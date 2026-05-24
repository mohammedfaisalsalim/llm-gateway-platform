# Intelligent LLM API Gateway

A production-grade, asynchronous AI infrastructure gateway designed to sit in front of enterprise LLM feature calls. This platform dynamically classifies incoming prompt complexity using a machine learning model, orchestrates intelligent traffic routing to optimized local or cloud model providers based on numerical quality tiers, and maintains a thread-isolated transactional database audit trail.

Built with **FastAPI**, **Ollama**, **Scikit-learn**, **SQLite**, and **python-dotenv**.

---

## Architecture Overview

The gateway intercepts standard chat completion requests and passes them through an isolated, multi-layered processing pipeline before dispatching them to downstream providers:

1. **Ingestion & Validation:** FastAPI endpoints accept payload structures strictly validated via Pydantic schemas. Local environment variables are dynamically managed using `python-dotenv`.
2. **Cognitive Complexity Classification:** A localized statistical machine learning model extracts structural prompt features (token density, command verbs, formatting constraints) to predict an operational difficulty tier (Tier 0, 1, or 2).
3. **Dynamic Routing Resolution:** The calculated tier is matched against a model configuration registry mapping specific numerical quality tiers (1, 2, or 3) and provider constraints.
4. **Thread-Isolated Execution:** Outbound inference requests and local transactional writes are offloaded to asynchronous worker threads, ensuring heavy model computation never blocks the main event loop.

---

## System Core Features

* **Multi-Provider Abstraction Layer:** Unified interface mapping seamlessly across local deployment instances (Ollama) and cloud ecosystem APIs (Google Gemini 2.0 Flash).
* **Asynchronous Hygiene Optimization:** 100% non-blocking database writes and model generations engineered via `asyncio.to_thread` workers to eliminate main thread blocking under concurrent production load.
* **Granular Metrics Auditing:** Structural time-series telemetry capturing request timestamps, token counts, latency metrics, and calculated financial costs logged instantly to an optimized SQLite backend.
* **Hot-Swappable Configuration Registry:** Decoupled YAML configuration mapping allows DevOps changes to provider parameters and numerical quality tiers without requiring code deployments or causing string mismatch errors.
* **Deterministic Configuration Pathing:** Built using robust `pathlib` dynamic tracking to guarantee environment-agnostic file resolution, completely eliminating pathing errors across local environments and container deployments.

---

## Directory Structure

```text
llm-gateway-platform/
├── .gitignore               # System runtime exclusion definitions
├── README.md                # System onboarding and technical documentation
└── gateway/
    ├── .env                 # Local environment secrets (Git-ignored)
    ├── requirements.txt     # Locked application dependencies
    └── app/
        ├── __init__.py      # Module identification marker
        ├── main.py          # Application entry point & lifespan state manager
        ├── classifier.py    # Scikit-learn prompt taxonomy singleton
        ├── database.py      # Async-wrapped metrics logging abstraction
        ├── models.py        # Shared Pydantic data schemas
        ├── models_config.yaml # Structural provider routing configurations
        ├── providers.py     # Unified API execution worker
        └── routes/
            └── chat.py      # Core chat completion routing endpoints implementing path-safe config loading
Local Development & Setup
Prerequisites
Python 3.11+

Ollama running locally with target model allocations:

Bash
ollama pull llama3.2:3b
ollama pull mistral:7b
Installation
Clone the repository to your local workspace:

Bash
git clone [https://github.com/mohammedfaisalsalim/llm-gateway-platform.git](https://github.com/mohammedfaisalsalim/llm-gateway-platform.git)
cd llm-gateway-platform/gateway
Configure a local virtual environment and activate it:

Bash
python -m venv .venv
# On Windows (Command Prompt)
.venv\Scripts\activate
# On Windows (PowerShell)
.venv\Scripts\Activate.ps1
Install system dependencies:

Bash
pip install -r requirements.txt
Set up your environment variables:
Create a file named .env inside the gateway/ directory and add your secret credentials:

Plaintext
GEMINI_API_KEY=your_actual_gemini_api_key_here
Running the Gateway
Launch the server instance using Uvicorn:

Bash
uvicorn app.main:app --reload --port 8000
The interactive API documentation will be available locally at http://localhost:8000/docs.

Production API Verification
1. Simple Volume Testing (Tier 0 Complexity -> Quality Tier 1: Llama 3.2)
Bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "Hello gateway"}]}'
2. High Complexity Testing (Tier 2 Complexity -> Quality Tier 3: Mistral)
Bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "Analyze the log stream structure, evaluate if
