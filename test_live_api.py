import requests
import json
from datetime import datetime

# ================= CONFIGURATION =================
BASE_URL = "https://vera-production-production.up.railway.app"
# =================================================

def print_result(test_name, success, details):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"    Details: {details}")

def test_health():
    print("Testing /v1/healthz...")
    try:
        r = requests.get(f"{BASE_URL}/v1/healthz", timeout=10)
        print_result("Health Check", r.status_code == 200, f"Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False

def test_metadata():
    print("\nTesting /v1/metadata...")
    try:
        r = requests.get(f"{BASE_URL}/v1/metadata", timeout=10)
        print_result("Metadata Check", r.status_code == 200, f"Response: {r.text}")
        return r.status_code == 200
    except Exception as e:
        print_result("Metadata Check", False, str(e))
        return False

def test_context_push():
    print("\nTesting /v1/context (Pushing Data)...")
    payload = {
        "scope": "merchant",
        "context_id": "test_merchant_123",
        "version": 1,
        "payload": {
            "identity": {"name": "Test Store", "owner_first_name": "Raj", "city": "Delhi", "locality": "Rohini"},
            "category_slug": "dentists",
            "performance": {"ctr": "2%", "views": 100, "calls": 5}
        },
        "delivered_at": datetime.utcnow().isoformat() + "Z"
    }
    try:
        r = requests.post(f"{BASE_URL}/v1/context", json=payload, timeout=10)
        print_result("Context Push", r.status_code == 200, f"Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print_result("Context Push", False, str(e))
        return False

def test_tick():
    print("\nTesting /v1/tick (Generating Nudge)...")
    # Use a trigger ID that exists in your seed data
    payload = {
        "now": datetime.utcnow().isoformat() + "Z",
        "available_triggers": ["trg_001_research_digest_dentists"]
    }
    try:
        r = requests.post(f"{BASE_URL}/v1/tick", json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            actions = data.get("actions", [])
            print_result("Tick Generation", len(actions) > 0, f"Generated {len(actions)} action(s)")
            if actions:
                print(f"    Example Body: {actions[0].get('body')}")
            return True
        else:
            print_result("Tick Generation", False, f"Status: {r.status_code}")
            return False
    except Exception as e:
        print_result("Tick Generation", False, str(e))
        return False

def test_reply():
    print("\nTesting /v1/reply (Handling Response)...")
    payload = {
        "conversation_id": "test_conv_123",
        "merchant_id": "test_merchant_123",
        "from_role": "merchant",
        "message": "Yes, I want to try this!",
        "received_at": datetime.utcnow().isoformat() + "Z",
        "turn_number": 2
    }
    try:
        r = requests.post(f"{BASE_URL}/v1/reply", json=payload, timeout=10)
        print_result("Reply Handling", r.status_code == 200, f"Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print_result("Reply Handling", False, str(e))
        return False

if __name__ == "__main__":
    print(f"🚀 Starting API Test for: {BASE_URL}\n" + "="*50)
    results = []
    results.append(test_health())
    results.append(test_metadata())
    results.append(test_context_push())
    results.append(test_tick())
    results.append(test_reply())

    print("\n" + "="*50)
    final_score = sum(results)
    print(f"FINAL RESULT: {final_score}/{len(results)} tests passed.")
    if final_score == len(results):
        print("🎉 ALL ENDPOINTS ARE WORKING PERFECTLY!")
    else:
        print("⚠️ Some endpoints failed. Check the logs above.")
