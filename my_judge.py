#!/usr/bin/env python3
"""
Vera Bot Verification Agent
============================
Run: python verify_agent.py
Paste terminal output to Claude for scoring + corrections.
Uses Ollama locally (no API key needed).
"""

import json
import time
import requests
from datetime import datetime

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
BOT_URL     = "http://localhost:8000"   # change to production URL if needed
OLLAMA_URL  = "http://localhost:11434"
OLLAMA_MODEL = "llama3"                 # change to your ollama model

SEED_DIR = "./seed_data"

# ── COLORS ────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

passed = 0
failed = 0
results = []

def p(color, label, msg):
    print(f"{color}{BOLD}[{label}]{RESET} {msg}")

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        p(GREEN, "PASS", f"{name} {detail}")
    else:
        failed += 1
        p(RED,  "FAIL", f"{name} {detail}")
    results.append({"test": name, "pass": condition, "detail": detail})

# ── OLLAMA JUDGE ──────────────────────────────────────────────────────────────
def ollama_score(message, merchant_name, locality, offer, trigger_kind):
    """Score message quality using local Ollama."""
    prompt = f"""Score this merchant WhatsApp message on 5 dimensions (0-10 each).

MESSAGE: "{message}"

CONTEXT:
- Merchant: {merchant_name}
- Locality: {locality}
- Active Offer: {offer}
- Trigger: {trigger_kind}

SCORING RUBRIC:
1. Specificity (0-10): Does it use real numbers, names, locality? Generic = 0, Hyperlocal = 10
2. Engagement Compulsion (0-10): Would merchant reply immediately? Boring = 0, Must reply = 10
3. Category Fit (0-10): Is tone right for this business type?
4. Merchant Fit (0-10): Personalized to this specific merchant?
5. Decision Quality (0-10): Is this the right message for this trigger?

RULES:
- Deduct 3 points if message mentions wrong city/locality
- Deduct 2 points if message is > 320 characters
- Deduct 3 points if message is generic with no real facts
- Deduct 2 points if no clear CTA

Return ONLY this JSON (no markdown):
{{"specificity": 0, "engagement": 0, "category_fit": 0, "merchant_fit": 0, "decision_quality": 0, "total": 0, "verdict": "one line feedback"}}"""

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        raw = r.json().get("response", "{}")
        # Clean JSON
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        return {"error": str(e), "total": 0}
    return {"total": 0, "verdict": "Could not score"}

# ── LOAD SEED DATA ────────────────────────────────────────────────────────────
def load_seed():
    import os, glob
    categories = {}
    merchants  = []
    triggers   = []

    cat_dir = os.path.join(SEED_DIR, "categories")
    if os.path.exists(cat_dir):
        for f in glob.glob(f"{cat_dir}/*.json"):
            d = json.load(open(f))
            categories[d["slug"]] = d

    m_file = os.path.join(SEED_DIR, "merchants_seed.json")
    if os.path.exists(m_file):
        merchants = json.load(open(m_file))["merchants"]

    t_file = os.path.join(SEED_DIR, "triggers_seed.json")
    if os.path.exists(t_file):
        triggers = json.load(open(t_file))["triggers"]

    c_file = os.path.join(SEED_DIR, "customers_seed.json")
    customers = []
    if os.path.exists(c_file):
        customers = json.load(open(c_file))["customers"]

    return categories, merchants, triggers, customers

# ── PUSH CONTEXT ──────────────────────────────────────────────────────────────
def push_context(scope, context_id, payload, version=1):
    r = requests.post(f"{BOT_URL}/v1/context", json={
        "scope": scope,
        "context_id": context_id,
        "version": version,
        "payload": payload,
        "delivered_at": datetime.utcnow().isoformat() + "Z"
    }, timeout=10)
    return r.status_code == 200

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*65}{RESET}")
print(f"{BOLD}     VERA BOT VERIFICATION AGENT v1.0{RESET}")
print(f"{BOLD}{'='*65}{RESET}\n")

# ── 1. HEALTH CHECK ───────────────────────────────────────────────────────────
print(f"{CYAN}{BOLD}--- HEALTH CHECK ---{RESET}")
try:
    r = requests.get(f"{BOT_URL}/v1/healthz", timeout=5)
    data = r.json()
    check("healthz status=ok", data.get("status") == "ok", str(data))
    check("healthz has contexts_loaded", "contexts_loaded" in data)
except Exception as e:
    check("healthz reachable", False, str(e))

# ── 2. METADATA CHECK ─────────────────────────────────────────────────────────
print(f"\n{CYAN}{BOLD}--- METADATA CHECK ---{RESET}")
try:
    r = requests.get(f"{BOT_URL}/v1/metadata", timeout=5)
    data = r.json()
    check("metadata has team_name",    bool(data.get("team_name")))
    check("metadata team_name not placeholder", data.get("team_name") != "Your Name Here", 
          f"team_name={data.get('team_name')}")
    check("metadata has model",        bool(data.get("model")))
    check("metadata has approach",     bool(data.get("approach")))
    print(f"  Team: {data.get('team_name')} | Model: {data.get('model')}")
except Exception as e:
    check("metadata reachable", False, str(e))

# ── 3. LOAD + PUSH SEED DATA ──────────────────────────────────────────────────
print(f"\n{CYAN}{BOLD}--- CONTEXT PUSH ---{RESET}")
try:
    categories, merchants, triggers, customers = load_seed()
    print(f"  Loaded: {len(categories)} categories, {len(merchants)} merchants, "
          f"{len(triggers)} triggers, {len(customers)} customers")

    # Push categories
    for slug, cat in categories.items():
        ok = push_context("category", slug, cat)
        check(f"category/{slug}", ok)

    # Push merchants
    for m in merchants:
        ok = push_context("merchant", m["merchant_id"], m)
        check(f"merchant/{m['merchant_id'][:20]}", ok)

    # Push customers
    for c in customers[:5]:  # push first 5
        push_context("customer", c["customer_id"], c)

    # Push triggers
    for t in triggers:
        push_context("trigger", t["id"], t)

    print(f"  Seed data pushed successfully")
except Exception as e:
    check("seed data load", False, str(e))

# ── 4. TICK TEST — 6 KEY TRIGGERS ────────────────────────────────────────────
print(f"\n{CYAN}{BOLD}--- TICK QUALITY TEST ---{RESET}")

TEST_TRIGGERS = [
    ("trg_001_research_digest_dentists", "research_digest",
     "m_001_drmeera_dentist_delhi", "Dr. Meera's Dental Clinic", "Lajpat Nagar", "Dental Cleaning @ Rs.299"),
    ("trg_010_ipl_match_delhi", "ipl_match_today",
     "m_005_pizzajunction_restaurant_delhi", "SK Pizza Junction", "Sant Nagar", "Buy 1 Pizza Get 1 Free"),
    ("trg_019_chronic_refill_grandfather", "chronic_refill_due",
     "m_009_apollo_pharmacy_jaipur", "Apollo Health Plus Pharmacy", "Malviya Nagar", "Free Home Delivery"),
    ("trg_006_festival_diwali", "festival_upcoming",
     "m_003_studio11_salon_hyderabad", "Studio11 Family Salon", "Kapra", "Haircut at Rs.99"),
    ("trg_015_winback_rashmi", "customer_lapsed_hard",
     "m_007_powerhouse_gym_bangalore", "PowerHouse Fitness", "HSR Layout", "3 FREE Trial Classes"),
    ("trg_018_supply_atorvastatin_recall", "supply_alert",
     "m_009_apollo_pharmacy_jaipur", "Apollo Health Plus Pharmacy", "Malviya Nagar", "Senior Citizen 15% OFF"),
]

tick_scores = []

for trg_id, kind, mid, biz_name, locality, offer in TEST_TRIGGERS:
    print(f"\n  {YELLOW}Trigger: {trg_id}{RESET}")
    try:
        r = requests.post(f"{BOT_URL}/v1/tick",
            json={"available_triggers": [trg_id]},
            timeout=30)
        data = r.json()
        actions = data.get("actions", [])

        check(f"tick/{kind} returns actions", len(actions) > 0)
        if not actions:
            continue

        action = actions[0]
        body   = action.get("body", "")
        supp   = action.get("suppression_key", "")
        cta    = action.get("cta", "")

        print(f"  Body: {body}")
        print(f"  Suppression: {supp}")
        print(f"  CTA: {cta}")

        # Schema checks
        check(f"tick/{kind} body <=320 chars", len(body) <= 320, f"({len(body)} chars)")
        check(f"tick/{kind} has suppression_key", bool(supp))
        check(f"tick/{kind} has cta", bool(cta))
        check(f"tick/{kind} no URL in body", "http" not in body.lower())
        check(f"tick/{kind} no encoding error", "â" not in body and "Ã" not in body,
              "encoding ok" if ("â" not in body and "Ã" not in body) else "ENCODING BROKEN")

        # Ollama scoring
        print(f"  {YELLOW}Scoring with Ollama...{RESET}")
        score = ollama_score(body, biz_name, locality, offer, kind)
        if "error" not in score:
            total = score.get("total", 0)
            tick_scores.append(total)
            verdict = score.get("verdict", "")
            color = GREEN if total >= 7 else (YELLOW if total >= 5 else RED)
            print(f"  {color}Score: {total}/10 — {verdict}{RESET}")
            print(f"    Specificity={score.get('specificity',0)} | "
                  f"Engagement={score.get('engagement',0)} | "
                  f"CategoryFit={score.get('category_fit',0)} | "
                  f"MerchantFit={score.get('merchant_fit',0)} | "
                  f"DecisionQ={score.get('decision_quality',0)}")
        else:
            print(f"  {RED}Ollama scoring failed: {score.get('error')}{RESET}")

    except Exception as e:
        check(f"tick/{kind}", False, str(e))

# ── 5. REPLY TESTS ────────────────────────────────────────────────────────────
print(f"\n{CYAN}{BOLD}--- REPLY HANDLING ---{RESET}")

reply_tests = [
    # (message, turn_number, from_role, expected_action, label)
    ("ok go ahead",    1, "merchant",  "send", "merchant positive"),
    ("stop this spam", 1, "merchant",  "end",  "merchant hostile"),
    ("blah blah blah", 1, "merchant",  "wait", "merchant unclear turn1"),
    ("blah blah blah", 2, "merchant",  "end",  "auto-reply detection turn2"),
    ("yes book me Wed 5 Nov 6pm", 1, "customer", "send", "customer booking"),
    ("no thanks",      1, "customer",  "end",  "customer decline"),
]

for msg, turn, role, expected, label in reply_tests:
    try:
        r = requests.post(f"{BOT_URL}/v1/reply", json={
            "message":     msg,
            "turn_number": turn,
            "from_role":   role,
            "received_at": datetime.utcnow().isoformat() + "Z"
        }, timeout=10)
        data   = r.json()
        action = data.get("action", "")
        body   = data.get("body", "")
        ok     = action == expected
        check(f"reply/{label}", ok,
              f"expected={expected} got={action} | body={body[:60]}")
    except Exception as e:
        check(f"reply/{label}", False, str(e))

# ── 6. IDEMPOTENCY CHECK ──────────────────────────────────────────────────────
print(f"\n{CYAN}{BOLD}--- IDEMPOTENCY CHECK ---{RESET}")
try:
    # Push same context twice with same version
    payload = {"test": "idempotency", "merchant_id": "test_idem"}
    r1 = requests.post(f"{BOT_URL}/v1/context", json={
        "scope": "merchant", "context_id": "test_idem_001",
        "version": 1, "payload": payload
    }, timeout=5)
    r2 = requests.post(f"{BOT_URL}/v1/context", json={
        "scope": "merchant", "context_id": "test_idem_001",
        "version": 1, "payload": payload
    }, timeout=5)
    check("idempotent same version", r1.status_code == 200 and r2.status_code == 200)

    # Higher version should replace
    r3 = requests.post(f"{BOT_URL}/v1/context", json={
        "scope": "merchant", "context_id": "test_idem_001",
        "version": 2, "payload": {**payload, "updated": True}
    }, timeout=5)
    check("higher version replaces", r3.status_code == 200)
except Exception as e:
    check("idempotency", False, str(e))

# ── 7. TIMEOUT CHECK ──────────────────────────────────────────────────────────
print(f"\n{CYAN}{BOLD}--- PERFORMANCE CHECK ---{RESET}")
try:
    start = time.time()
    r = requests.post(f"{BOT_URL}/v1/tick",
        json={"available_triggers": ["trg_001_research_digest_dentists"]},
        timeout=30)
    elapsed = time.time() - start
    check("tick response < 30s", elapsed < 30, f"({elapsed:.2f}s)")
    check("tick response < 10s", elapsed < 10, f"({elapsed:.2f}s) — ideal")
except Exception as e:
    check("tick timeout", False, str(e))

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*65}{RESET}")
print(f"{BOLD}     FINAL SUMMARY{RESET}")
print(f"{BOLD}{'='*65}{RESET}")
print(f"  Tests Passed : {GREEN}{BOLD}{passed}{RESET}")
print(f"  Tests Failed : {RED}{BOLD}{failed}{RESET}")
total_tests = passed + failed
pct = int((passed / total_tests) * 100) if total_tests else 0
color = GREEN if pct >= 80 else (YELLOW if pct >= 60 else RED)
print(f"  Pass Rate    : {color}{BOLD}{pct}%{RESET}")

if tick_scores:
    avg = sum(tick_scores) / len(tick_scores)
    color = GREEN if avg >= 7 else (YELLOW if avg >= 5 else RED)
    print(f"  Avg Msg Score: {color}{BOLD}{avg:.1f}/10{RESET} (Ollama judge)")

print(f"\n{BOLD}FAILED TESTS:{RESET}")
for r in results:
    if not r["pass"]:
        print(f"  {RED}✗ {r['test']}{RESET} — {r['detail']}")

print(f"\n{BOLD}{'='*65}{RESET}")
print(f"Paste this output to Claude for scoring + corrections!")
print(f"{BOLD}{'='*65}{RESET}\n")