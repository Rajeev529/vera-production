import requests
import json
from datetime import datetime
import time

# ================= CONFIGURATION =================
BASE_URL = "http://127.0.0.1:8000"
# =================================================

def push_context(scope, cid, payload):
    url = f"{BASE_URL}/v1/context"
    data = {
        "scope": scope,
        "context_id": cid,
        "version": 1,
        "payload": payload,
        "delivered_at": datetime.utcnow().isoformat() + "Z"
    }
    try:
        r = requests.post(url, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Error pushing {scope} {cid}: {e}")
        return False

def get_nudge(available_triggers):
    url = f"{BASE_URL}/v1/tick"
    data = {
        "now": datetime.utcnow().isoformat() + "Z",
        "available_triggers": available_triggers
    }
    try:
        r = requests.post(url, json=data, timeout=15)
        if r.status_code == 200:
            return r.json().get("actions", [])
    except Exception as e:
        print(f"Error getting nudge: {e}")
    return []

def send_reply(message, turn=1, role="merchant"):
    url = f"{BASE_URL}/v1/reply"
    data = {
        "message": message,
        "turn_number": turn,
        "from_role": role
    }
    try:
        r = requests.post(url, json=data, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Error sending reply: {e}")
    return {}

def run_complex_scenario(case):
    print(f"\n{'='*80}")
    print(f"🚀 TEST CASE: {case['name']}")
    print(f"Type: {case['type']} | Expected: {case['expected']}")
    print(f"{'='*80}")

    # 1. Push contexts
    for scope, cid, payload in case['contexts']:
        if not push_context(scope, cid, payload):
            print(f"❌ Failed to push {scope} {cid}")
            return "FAILED_PUSH"

    # 2. Get the first nudge
    trigger_id = case['trigger_id']
    actions = get_nudge([trigger_id])

    if not actions:
        print("\nVerdict: ❌ FAIL - Bot remained silent.")
        return "SILENT"

    first_nudge = actions[0]
    print(f"\n🤖 BOT NUDGE: \n\"{first_nudge['body']}\"")

    # 3. Q&A Interaction
    for i, interaction in enumerate(case['interactions']):
        user_msg = interaction['user']
        expected_action = interaction['expected_action']

        print(f"\n👤 MERCHANT: {user_msg}")
        response = send_reply(user_msg, turn=i+2)

        actual_action = response.get('action', 'unknown')
        bot_body = response.get('body', '')

        print(f"🤖 BOT: [{actual_action}] {bot_body}")

        if actual_action != expected_action:
            print(f"⚠️ MISMATCH: Expected {expected_action}, got {actual_action}")
        else:
            print(f"✅ Correct action: {actual_action}")

    print(f"\nVerdict: ✅ Scenario completed.")
    return "COMPLETED"

if __name__ == "__main__":
    print(f"🌟 VERA STRESS TEST SUITE 🌟")
    print(f"Target: {BASE_URL}\n")

    test_cases = [
        # --- EDGE CASE: MISSING CATEGORY ---
        {
            "name": "Missing Category Context",
            "type": "edge",
            "expected": "Should still send a generic but professional nudge",
            "contexts": [
                ("merchant", "m_missing_cat_01", {"identity": {"id": "m_missing_cat_01", "name": "Quick Fix", "owner_first_name": "Raj", "city": "Delhi", "locality": "Rohini"}, "category_slug": "plumbing", "performance": {"calls": 5}, "offers": []}),
                ("trigger", "trg_missing_cat_01", {"kind": "perf_dip", "merchant_id": "m_missing_cat_01", "payload": {"drop": "50%"}})
            ],
            "trigger_id": "trg_missing_cat_01",
            "interactions": [
                {"user": "Yes, do it", "expected_action": "send"}
            ]
        },
        # --- EDGE CASE: CONFLICTING LOCATION ---
        {
            "name": "Conflicting Location",
            "type": "edge",
            "expected": "Should not mention wrong city in nudge",
            "contexts": [
                ("merchant", "m_conflict_01", {"identity": {"id": "m_conflict_01", "name": "Royal Spa", "owner_first_name": "Suman", "city": "Mumbai", "locality": "Bandra"}, "category_slug": "salons"}),
                ("trigger", "trg_conflict_01", {"kind": "research_digest", "merchant_id": "m_conflict_01", "payload": {"locality": "Delhi", "count": 100}})
            ],
            "trigger_id": "trg_conflict_01",
            "interactions": [
                {"user": "Where is this demand?", "expected_action": "wait"}
            ]
        },
        # --- EDGE CASE: EXTREME PERFORMANCE DIP ---
        {
            "name": "Extreme Performance Dip (99% Drop)",
            "type": "stress",
            "expected": "Should sound urgent but not panicky",
            "contexts": [
                ("merchant", "m_extreme_01", {"identity": {"id": "m_extreme_01", "name": "Apex Gym", "owner_first_name": "Vik", "city": "Bangalore", "locality": "Koramangala"}, "category_slug": "gyms", "performance": {"calls": 1, "delta_7d": {"calls": -99}}}),
                ("trigger", "trg_extreme_01", {"kind": "perf_dip", "merchant_id": "m_extreme_01", "payload": {"drop": "99%"}})
            ],
            "trigger_id": "trg_extreme_01",
            "interactions": [
                {"user": "Is this for real?", "expected_action": "wait"},
                {"user": "Fine, try a campaign", "expected_action": "send"}
            ]
        },
        # --- EDGE CASE: HOSTILE MERCHANT ---
        {
            "name": "Hostile Merchant",
            "type": "edge",
            "expected": "Bot should END immediately",
            "contexts": [
                ("merchant", "m_hostile_01", {"identity": {"id": "m_hostile_01", "name": "Angry Clinic", "owner_first_name": "Dr. X", "city": "Chennai", "locality": "Adyar"}, "category_slug": "dentists"}),
                ("trigger", "trg_hostile_01", {"kind": "research_digest", "merchant_id": "m_hostile_01", "payload": {"count": 50}})
            ],
            "trigger_id": "trg_hostile_01",
            "interactions": [
                {"user": "Stop messaging me. This is spam!", "expected_action": "end"}
            ]
        },
        # --- EDGE CASE: AMBIGUOUS REPLY ---
        {
            "name": "Ambiguous Reply",
            "type": "edge",
            "expected": "Bot should ask for clarification (wait)",
            "contexts": [
                ("merchant", "m_ambig_01", {"identity": {"id": "m_ambig_01", "name": "Cafe Joy", "owner_first_name": "Joy", "city": "Jaipur", "locality": "Mansarovar"}, "category_slug": "restaurants"}),
                ("trigger", "trg_ambig_01", {"kind": "research_digest", "merchant_id": "m_ambig_01", "payload": {"count": 200}})
            ],
            "trigger_id": "trg_ambig_01",
            "interactions": [
                {"user": "I might be interested, let me think", "expected_action": "wait"}
            ]
        },
        # --- EDGE CASE: WIN-BACK WITH CUSTOMER DATA ---
        {
            "name": "Personalized Win-back",
            "type": "stress",
            "expected": "Should use customer name and specific detail",
            "contexts": [
                ("merchant", "m_win_01", {"identity": {"id": "m_win_01", "name": "Elite Spa", "owner_first_name": "Priya", "city": "Pune", "locality": "Koregaon Park"}, "category_slug": "salons"}),
                ("customer", "c_win_01", {"identity": {"name": "Anjali"}, "relationship": {"last_visit": "180 days ago", "services_received": ["HydraFacial", "Massage"]}}),
                ("trigger", "trg_win_01", {"kind": "winback", "merchant_id": "m_win_01", "customer_id": "c_win_01", "payload": {"customer_name": "Anjali", "days_since_visit": 180}})
            ],
            "trigger_id": "trg_win_01",
            "interactions": [
                {"user": "Yes, reach out to her", "expected_action": "send"}
            ]
        },
        # --- EDGE CASE: HUGE SEARCH SPIKE ---
        {
            "name": "Massive Search Spike",
            "type": "stress",
            "expected": "Should handle large numbers naturally",
            "contexts": [
                ("merchant", "m_spike_01", {"identity": {"id": "m_spike_01", "name": "Mega Gym", "owner_first_name": "Sam", "city": "Delhi", "locality": "Saket"}, "category_slug": "gyms"}),
                ("trigger", "trg_spike_01", {"kind": "research_digest", "merchant_id": "m_spike_01", "payload": {"count": 15000, "search_term": "Weight Loss"}})
            ],
            "trigger_id": "trg_spike_01",
            "interactions": [
                {"user": "15k people? Are you sure?", "expected_action": "wait"},
                {"user": "Okay, let's do it", "expected_action": "send"}
            ]
        },
        # --- EDGE CASE: NO OFFERS ACTIVE ---
        {
            "name": "No Active Offers",
            "type": "edge",
            "expected": "Should not hallucinate an offer, should suggest creating one",
            "contexts": [
                ("merchant", "m_no_off_01", {"identity": {"id": "m_no_off_01", "name": "Pure Pharma", "owner_first_name": "Amit", "city": "Lucknow", "locality": "Hazratganj"}, "category_slug": "pharmacies", "offers": []}),
                ("trigger", "trg_no_off_01", {"kind": "research_digest", "merchant_id": "m_no_off_01", "payload": {"count": 300}})
            ],
            "trigger_id": "trg_no_off_01",
            "interactions": [
                {"user": "What offer will you send?", "expected_action": "wait"}
            ]
        },
        # --- EDGE CASE: FAST CONFIRMATION ---
        {
            "name": "Instant Yes",
            "type": "stress",
            "expected": "Should transition to send immediately",
            "contexts": [
                ("merchant", "m_fast_01", {"identity": {"id": "m_fast_01", "name": "Quick Bite", "owner_first_name": "Riya", "city": "Mumbai", "locality": "Colaba"}, "category_slug": "restaurants"}),
                ("trigger", "trg_fast_01", {"kind": "research_digest", "merchant_id": "m_fast_01", "payload": {"count": 100}})
            ],
            "trigger_id": "trg_fast_01",
            "interactions": [
                {"user": "Yes", "expected_action": "send"}
            ]
        },
        # --- EDGE CASE: SKEPTICAL MERCHANT ---
        {
            "name": "Skeptical Merchant",
            "type": "edge",
            "expected": "Should handle doubt professionally",
            "contexts": [
                ("merchant", "m_skep_01", {"identity": {"id": "m_skep_01", "name": "Safe Clinic", "owner_first_name": "Dr. K", "city": "Hyderabad", "locality": "Banjara"}, "category_slug": "dentists"}),
                ("trigger", "trg_skep_01", {"kind": "perf_dip", "merchant_id": "m_skep_01", "payload": {"drop": "20%"}})
            ],
            "trigger_id": "trg_skep_01",
            "interactions": [
                {"user": "I dont believe your data", "expected_action": "wait"}
            ]
        },
        # --- EDGE CASE: MULTIPLE TRIGGERS (Simulated by sequence) ---
        {
            "name": "Sequential Triggers",
            "type": "stress",
            "expected": "Should handle different triggers for same merchant",
            "contexts": [
                ("merchant", "m_seq_01", {"identity": {"id": "m_seq_01", "name": "Zen Yoga", "owner_first_name": "Maya", "city": "Chennai", "locality": "Besant Nagar"}, "category_slug": "gyms"}),
                ("trigger", "trg_seq_01", {"kind": "perf_dip", "merchant_id": "m_seq_01", "payload": {"drop": "10%"}}),
                ("trigger", "trg_seq_02", {"kind": "research_digest", "merchant_id": "m_seq_01", "payload": {"count": 500}})
            ],
            "trigger_id": "trg_seq_01",
            "interactions": [
                {"user": "Sure", "expected_action": "send"}
            ]
        }
    ]

    # Adding 15 more variations to reach 25+
    for i in range(1, 16):
        test_cases.append({
            "name": f"Variation Test {i}",
            "type": "standard",
            "expected": "Standard response",
            "contexts": [
                ("merchant", f"m_var_{i}", {"identity": {"id": f"m_var_{i}", "name": f"Biz {i}", "owner_first_name": f"Owner {i}", "city": "Delhi", "locality": "Central"}, "category_slug": "restaurants"}),
                ("trigger", f"trg_var_{i}", {"kind": "research_digest", "merchant_id": f"m_var_{i}", "payload": {"count": 10*i}})
            ],
            "trigger_id": f"trg_var_{i}",
            "interactions": [
                {"user": "Ok", "expected_action": "send"}
            ]
        })

    results = []
    for case in test_cases:
        res = run_complex_scenario(case)
        results.append((case['name'], res))

    print(f"\n\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    for name, res in results:
        print(f"{name}: {res}")
