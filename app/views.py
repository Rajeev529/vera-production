import uuid
import time
import logging

from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ContextStore
from .composer import compose_message, pick_best_trigger

logger = logging.getLogger(__name__)
START_TIME = time.time()


# ─────────────────────────────────────────────
# 1. POST /v1/context
# ─────────────────────────────────────────────
@api_view(["POST"])
def context(request):
    data       = request.data
    scope      = data.get("scope", "")
    context_id = data.get("context_id", "")
    version    = data.get("version", 1)
    payload    = data.get("payload", {})

    if not context_id or not scope:
        return Response({"error": "scope and context_id required"}, status=400)

    existing = ContextStore.objects.filter(context_id=context_id).first()

    # Idempotent: same or older version → no-op
    if existing and existing.version >= version:
        return Response({
            "accepted": True,
            "ack_id": f"ack_{uuid.uuid4().hex[:8]}",
            "stored_at": existing.stored_at.isoformat(),
        })

    obj, _ = ContextStore.objects.update_or_create(
        context_id=context_id,
        defaults={"scope": scope, "version": version, "payload": payload},
    )

    # ── IMMEDIATE TRIGGER PROCESSING ─────────────────────
    # If this is a trigger being pushed, try to generate an action immediately
    actions = []
    if scope == "trigger":
        try:
            # Find the merchant this trigger belongs to
            m_id = payload.get("merchant_id")
            if m_id:
                merchant = ContextStore.objects.filter(scope="merchant", context_id=m_id).first()
                if merchant:
                    m_payload = merchant.payload
                    cat_slug = m_payload.get("category_slug", "")
                    cat_obj = ContextStore.objects.filter(scope="category", context_id=cat_slug).first()
                    cat_payload = cat_obj.payload if cat_obj else {"display_name": cat_slug, "voice": {}, "peer_stats": {}, "digest": []}

                    # Check for customer context if applicable
                    cust_id = payload.get("customer_id")
                    cust_payload = None
                    if cust_id:
                        cust_obj = ContextStore.objects.filter(scope="customer", context_id=cust_id).first()
                        if cust_obj:
                            cust_payload = cust_obj.payload

                    # Use the pushed trigger as the 'best' trigger
                    msg = compose_message(m_payload, cat_payload, obj, cust_payload)
                    actions.append({
                        "merchant_id":     merchant.context_id,
                        "trigger_id":      obj.context_id,
                        "body":            msg["body"][:320],
                        "cta":             msg.get("cta", "open_ended"),
                        "suppression_key": msg.get("suppression_key", f"{obj.context_id}:default"),
                    })
        except Exception as e:
            logger.error(f"Immediate compose failed for {context_id}: {e}")

    if actions:
        return Response({
            "accepted": True,
            "ack_id": f"ack_{uuid.uuid4().hex[:8]}",
            "stored_at": obj.stored_at.isoformat(),
            "actions": actions,
        })

    return Response({
        "accepted": True,
        "ack_id": f"ack_{uuid.uuid4().hex[:8]}",
        "stored_at": obj.stored_at.isoformat(),
    })


# ─────────────────────────────────────────────
# 2. POST /v1/tick
# ─────────────────────────────────────────────
@api_view(["POST"])
def tick(request):
    available_triggers = request.data.get("available_triggers", [])
    actions = []

    print(f"\n--- TICK DEBUG START ---")
    print(f"Available triggers from request: {available_triggers}")

    # Find all triggers currently in the system that are also in the available list
    active_triggers = ContextStore.objects.filter(
        scope="trigger",
        context_id__in=available_triggers
    )

    print(f"Active triggers found in DB: {[t.context_id for t in active_triggers]}")

    all_triggers = list(ContextStore.objects.filter(scope="trigger"))
    seen_merchants = set()
    used_triggers  = set()

    # Iterate through the specific triggers we are asked to process
    for trigger in active_triggers:
        if len(actions) >= 20:
            break

        t_payload = trigger.payload
        m_id = t_payload.get("merchant_id")
        print(f"Processing trigger {trigger.context_id} for merchant {m_id}...")

        if not m_id:
            print(f"  -> SKIP: No merchant_id in trigger payload")
            continue

        if m_id in seen_merchants:
            print(f"  -> SKIP: Merchant {m_id} already processed")
            continue

        # Find the merchant associated with this trigger
        merchant = ContextStore.objects.filter(scope="merchant", context_id=m_id).first()
        if not merchant:
            print(f"  -> SKIP: Merchant {m_id} not found in ContextStore")
            continue

        seen_merchants.add(m_id)
        m_payload = merchant.payload
        cat_slug  = m_payload.get("category_slug", "")

        cat_obj     = ContextStore.objects.filter(scope="category", context_id=cat_slug).first()
        cat_payload = cat_obj.payload if cat_obj else {
            "display_name": cat_slug, "voice": {}, "peer_stats": {}, "digest": []
        }

        # Use the trigger we are currently iterating over
        best_trigger = trigger
        used_triggers.add(best_trigger.context_id)

        cust_payload = None
        cust_id = best_trigger.payload.get("customer_id")
        if cust_id:
            cust_obj = ContextStore.objects.filter(scope="customer", context_id=cust_id).first()
            if cust_obj:
                cust_payload = cust_obj.payload

        try:
            msg = compose_message(m_payload, cat_payload, best_trigger, cust_payload)
            print(f"  -> SUCCESS: Composed message for {m_id}")
            actions.append({
                "merchant_id":     merchant.context_id,
                "trigger_id":      best_trigger.context_id,
                "body":            msg["body"][:320],
                "cta":             msg.get("cta", "open_ended"),
                "suppression_key": msg.get("suppression_key", f"{best_trigger.context_id}:default"),
            })
        except Exception as e:
            print(f"  -> ERROR: Compose failed for {merchant.context_id}: {e}")
            logger.error(f"Compose failed for {merchant.context_id}: {e}")
            continue

    print(f"Final actions count: {len(actions)}")
    print(f"--- TICK DEBUG END ---\n")
    return Response({"actions": actions})


# ─────────────────────────────────────────────
# 3. POST /v1/reply
# ─────────────────────────────────────────────
@api_view(["POST"])
def reply(request):
    message     = request.data.get("message", "").lower()
    turn_number = request.data.get("turn_number", 1)
    from_role   = request.data.get("from_role", "merchant")

    positive = ["yes", "ok", "sure", "send", "go", "please", "book",
                "confirm", "wed", "thu", "slot", "lets", "do it", "try",
                "reach out", "sounds good", "go ahead"]
    negative = ["no", "nope", "stop", "cancel", "spam", "useless",
                "dont want", "not interested", "remove me"]

    # Question/doubt signals — always return wait
    question_signals = ["?", "where", "is this", "are you sure", "really",
                        "believe", "think", "maybe", "might", "what offer",
                        "which", "how", "why", "when", "sure about",
                        "for real", "seriously", "correct", "accurate"]
    is_question = any(w in message for w in question_signals)
    is_positive = any(w in message for w in positive)
    is_negative = any(w in message for w in negative)

    # 1. Hostile/negative — always end
    if is_negative:
        return Response({
            "action":    "end",
            "body":      "",
            "rationale": "Merchant declined or hostile",
        })

    # 2. Positive and no question — always send
    # We check this BEFORE auto-reply to prevent "Yes" or "Ok" from being ended
    if is_positive and not is_question:
        if from_role == "customer":
            return Response({
                "action":    "send",
                "body":      "Great! Your appointment is confirmed. You will receive a reminder before your visit.",
                "rationale": "Customer confirmed booking",
            })
        else:
            return Response({
                "action":    "send",
                "body":      "Perfect! Sending the campaign now. I will share a performance update in 24 hours.",
                "rationale": "Merchant accepted",
            })

    # 3. Auto-reply detection — ONLY if NOT positive, NOT negative, and NOT a question
    auto_reply_patterns = ["ok", "okay", "k", "hmm", "hm", "hi", "hello",
                           "hey", "thanks", "thank you", "noted", "seen"]
    is_auto_reply = (
        message.strip() in auto_reply_patterns
        or len(message.strip().split()) <= 1
    )

    if turn_number >= 2 and is_auto_reply and not is_question:
        return Response({
            "action":    "end",
            "body":      "",
            "rationale": "Auto-reply detected — no engagement",
        })

    # 4. Customer role - remaining cases (mostly questions or unclear)
    if from_role == "customer":
        return Response({
            "action":    "wait",
            "body":      "Could you confirm if you would like to book the slot?",
            "rationale": "Customer unclear or has question",
        })

    # 5. Merchant — question or doubt or thinking → always wait
    return Response({
        "action":    "wait",
        "body":      "That is a fair question — should I share more details, or shall we go ahead?",
        "rationale": "Merchant has a question — clarifying before action",
    })


# ─────────────────────────────────────────────
# 4. GET /v1/healthz
# ─────────────────────────────────────────────
@api_view(["GET"])
def healthz(request):
    counts = {
        scope: ContextStore.objects.filter(scope=scope).count()
        for scope in ["category", "merchant", "customer", "trigger"]
    }
    return Response({
        "status":          "ok",
        "uptime_seconds":  int(time.time() - START_TIME),
        "contexts_loaded": counts,
    })


# ─────────────────────────────────────────────
# 5. GET /v1/metadata
# ─────────────────────────────────────────────
@api_view(["GET"])
def metadata(request):
    return Response({
        "team_name":    "Rajeev",
        "team_members": ["Rajeev"],
        "model":        "groq/llama-3.3-70b-versatile",
        "approach":     "4-layer structured prompt composer — merchant + category + trigger + customer injected directly into LLM prompt. No vector DB needed; data already structured JSON.",
        "version":      "1.0.0",
    })