import os
import json
import logging
from dotenv import load_dotenv

# Import the logic from the app
from app.composer import compose_message, pick_best_trigger

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def test_llm_response():
    """
    Tests if the LLM is responding correctly by simulating a standard
    merchant, category, and trigger scenario.
    """
    logger.info("Testing LLM response via compose_message...")

    # 1. Mock Data
    merchant_payload = {
        "merchant_id": "m_001",
        "identity": {
            "name": "Dr. Meera Dental",
            "owner_first_name": "Meera",
            "city": "Delhi",
            "locality": "Lajpat Nagar"
        },
        "performance": {
            "ctr": "2.5%",
            "views": 1000,
            "calls": 25,
            "delta_7d": "-10%"
        },
        "offers": [
            {"title": "Dental Check Up @ ₹299", "status": "active"}
        ],
        "signals": ["high_demand_local"],
        "subscription": {"status": "active", "days_remaining": 30},
        "customer_aggregate": {"total": 500}
    }

    category_payload = {
        "display_name": "Dentists",
        "voice": {"tone": "professional yet urgent"},
        "peer_stats": {"avg_ctr": "2.0%", "avg_calls_30d": 20},
        "digest": [{"title": "High search for cleaning", "actionable": "push checkup offers"}]
    }

    # Using a class-like object for trigger as expected by composer.py
    class TriggerObj:
        def __init__(self, context_id, payload):
            self.context_id = context_id
            self.payload = payload

    trigger_obj = TriggerObj(
        context_id="trg_001_research_digest_dentists",
        payload={
            "kind": "research_digest",
            "urgency": 5,
            "merchant_id": "m_001",
            "suppression_key": "research:m_001:2026-W18",
            "details": "190 people searched for dental checkup in Lajpat Nagar today"
        }
    )

    customer_payload = {
        "identity": {"name": "John Doe"},
        "state": "lapsed",
        "relationship": {"last_visit": "2025-01-01", "services_received": ["cleaning"]}
    }

    try:
        # Execute composition
        result = compose_message(merchant_payload, category_payload, trigger_obj, customer_payload)

        logger.info(f"LLM Result: {json.dumps(result, indent=2)}")

        # Validations
        assert "body" in result, "Response missing 'body'"
        assert len(result["body"]) <= 320, f"Body too long: {len(result['body'])} chars"
        assert "Rs." in result["body"] or "₹" not in result["body"], "Found rupee symbol instead of 'Rs.'"
        assert result["suppression_key"] == "research:m_001:2026-W18", "Suppression key mismatch"

        logger.info("✅ LLM Response Test Passed!")
        return True

    except Exception as e:
        logger.error(f"❌ LLM Response Test Failed: {e}")
        return False

def test_trigger_selection():
    """
    Tests if the trigger selection logic correctly picks the most urgent matched trigger.
    """
    logger.info("Testing Trigger Selection logic...")

    class TriggerObj:
        def __init__(self, context_id, payload):
            self.context_id = context_id
            self.payload = payload

    all_triggers = [
        TriggerObj("trg_low", {"merchant_id": "m_001", "urgency": 1}),
        TriggerObj("trg_high", {"merchant_id": "m_001", "urgency": 10}),
    ]

    merchant_payload = {"merchant_id": "m_001"}
    available_triggers = ["trg_low", "trg_high"]

    best = pick_best_trigger(merchant_payload, available_triggers, all_triggers)

    if best and best.context_id == "trg_high":
        logger.info("✅ Trigger Selection Test Passed!")
        return True
    else:
        logger.error(f"❌ Trigger Selection Test Failed: Expected trg_high, got {best.context_id if best else 'None'}")
        return False

if __name__ == "__main__":
    print("\n--- Running Unit Tests for Vera AI ---\n")
    llm_ok = test_llm_response()
    trig_ok = test_trigger_selection()

    print("\n--- Final Summary ---")
    print(f"LLM Response: {'PASSED' if llm_ok else 'FAILED'}")
    print(f"Trigger Selection: {'PASSED' if trig_ok else 'FAILED'}")

    if not (llm_ok and trig_ok):
        exit(1)
