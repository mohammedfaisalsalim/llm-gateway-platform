# Intelligent LLM API Gateway

A production-grade, asynchronous AI infrastructure gateway designed to sit in front of enterprise LLM feature calls. This platform dynamically classifies incoming prompt complexity using a machine learning model, orchestrates intelligent traffic routing to optimized local or cloud model providers, and maintains a thread-isolated transactional database audit trail.

Built with **FastAPI**, **Ollama**, **Scikit-learn**, and **SQLite**.

---

## Architecture Overview

The gateway intercepts standard chat completion requests and passes them through an isolated, multi-layered processing pipeline before dispatching them to downstream providers:

1. **Ingestion & Validation:** Fast API endpoints accept payload structures strictly validated via Pydantic schemas.
2. **Cognitive Complexity Classification:** A localized statistical machine learning model extracts structural prompt features (token density, command verbs, formatting constraints) to predict an operational difficulty tier (Tier 0, 1, or 2).
3. **Dynamic Routing Resolution:** The calculated tier is matched against a model configuration registry mapping specific quality thresholds and provider constraints.
4. **Thread-Isolated Execution:** Outbound inference requests and local transactional writes are offloaded to asynchronous worker threads, ensuring heavy model computation never blocks the main event loop.

---

## System Core Features

* **Multi-Provider Abstraction Layer:** Unified interface mapping seamlessly across local deployment instances (Ollama) and cloud ecosystem APIs (Google Gemini).
* **Asynchronous Hygiene Optimization:** 100% non-blocking database writes and model generations engineered via `asyncio.to_thread` workers to eliminate main thread blocking under concurrent production load.
* **Granular Metrics Auditing:** Structural time-series telemetry capturing request timestamps, token counts, latency metrics, and calculated financial costs logged instantly to an optimized SQLite backend.
* **Hot-Swappable Configuration Registry:** Decoupled YAML configuration mapping allows DevOps changes to provider parameters and numerical quality tiers without requiring code deployments.

---

## Directory Structure

```text
llm-gateway-platform/
├── .gitignore               # System runtime exclusion definitions
├── README.md                # System onboarding and technical documentation
└── gateway/
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
            └── chat.py      # Core chat completion routing endpoints


Local Development & Setup
Prerequisites
Python 3.11+

Ollama running locally with target model allocations:
ollama pull llama3.2:3b
ollama pull mistral:7b