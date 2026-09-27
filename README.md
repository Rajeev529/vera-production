# Vera Bot — magicpin AI Challenge Submission

Vera is an AI growth assistant for local merchants, designed to help them improve listings, run campaigns, and engage customers through sharp, grounded, and high-compulsion WhatsApp nudges.

## 🚀 Live URL
`https://verai-production-66d2.up.railway.app`

## 🛠️ Technical Approach

### The Compose Engine
Vera uses a **deterministic 4-layer structured prompt composer**. Instead of relying on a vector database, the system leverages the structured JSON context provided by the judge to ensure every message is grounded in real facts.

**Composition Layers:**
1. **Merchant**: Business identity, owner name, locality, performance signals (CTR, calls), and active offers.
2. **Category**: Industry-specific tone (e.g., clinical for dentists, warm for salons) and peer benchmarks.
3. **Trigger**: The "Why Now" (e.g., performance dip, research spike, festival, or recall).
4. **Customer**: (Optional) Relationship state, last visit, and specific preferences.

### Design Principles for High Engagement
To maximize the **Engagement Compulsion** score, Vera follows these strict rules:
- **Specificity**: No generic "increase sales" claims. Uses real numbers (e.g., "190 people searched") and exact offer prices.
- **Single Idea**: One insight, one benefit, and one clear yes/no question per message.
- **Local Grounding**: Always references the merchant's own city and locality to establish trust.
- **Low Friction**: CTAs are designed to be "easy wins" (e.g., "Shall I send it?").

---

## 📡 API Specification

| Method | URL | Purpose |
|--------|-----|---------|
| `GET` | `/v1/healthz` | Liveness check |
| `GET` | `/v1/metadata` | Team info and model details |
| `POST` | `/v1/context` | Idempotent storage of merchant/category/trigger/customer data |
| `POST` | `/v1/tick` | Generate the best nudge based on available triggers |
| `POST` | `/v1/reply` | Handle merchant replies (Support for intent transitions & hostile handling) |

---

## 💻 Tech Stack
- **Framework**: Django + Django REST Framework
- **LLM**: Groq $\rightarrow$ `qwen/qwen3.8-27b` (Chosen for high reasoning capabilities and low latency)
- **Orchestration**: LangChain (PromptTemplates + JsonOutputParser)
- **Database**: SQLite (Persistent volume on Railway)
- **Deployment**: Railway (Gunicorn)

---

## 🧪 Local Development & Testing

### Setup
```bash
# 1. Clone and environment
python -m venv myvenv
myvenv\Scripts\activate
pip install -r requirements.txt

# 2. Database and Data
python manage.py migrate
python load_seed_data.py

# 3. Run
python manage.py runserver
```

### Testing with the Judge Simulator
The `judge_simulator.py` is used to validate endpoint behavior and score compositions across the 5 rubric dimensions: **Decision Quality, Specificity, Category Fit, Merchant Fit, and Engagement Compulsion.**

```bash
# Run the official local harness
python judge_simulator.py
```

### Unit Testing
A dedicated test suite is available to verify LLM response shapes and trigger selection logic:
```bash
python test_llm.py
```

---

## 📊 Scoring Rubric Alignment
Vera is optimized for the following dimensions:
- **Decision Quality**: `pick_best_trigger()` ranks triggers by urgency to ensure the most relevant signal drives the message.
- **Specificity**: Strict prompt constraints force the LLM to use provided numbers and local facts.
- **Category Fit**: Voice profiles are injected based on the category slug.
- **Merchant Fit**: Personalized using the owner's first name and business-specific performance deltas.
- **Engagement**: Focuses on "Loss Aversion" and "FOMO" hooks with a single, low-friction CTA.
