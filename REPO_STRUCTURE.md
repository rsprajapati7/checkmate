# CheckMate / Suraksha 2.0 — Backend Repository Structure

## Root Directory Layout

```
checkmate/
├── backend/                    # Main FastAPI application
├── frontend/                   # React frontend application (empty/placeholder)
├── models/                     # Model weights and registry
├── infra/                      # Docker, K8s, Terraform
├── tests/                      # Test suite (unit, integration, e2e)
├── packages/                   # Shared Python packages
│
├── pyproject.toml             # Python dependencies, tool config
├── Makefile                   # Development commands
├── docker-compose.yml         # Local dev: API + Postgres + Redis
├── .env.example               # Environment template
├── .gitignore
└── README.md
```

---

## `backend/` — FastAPI Application Structure

```
backend/
│
├── api/                       # HTTP API layer
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py          # POST /api/v1/documents/upload
│   │   ├── analyze.py         # POST /api/v1/documents/{id}/analyze
│   │   ├── status.py          # GET /api/v1/jobs/{job_id}
│   │   └── report.py          # GET /api/v1/reports/{job_id}
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── document.py        # DocumentUpload, DocumentMetadata
│   │   ├── analysis.py        # AnalysisRequest, AnalysisResponse
│   │   └── risk.py            # RiskScore, RiskTier, PipelineResult
│   │
│   ├── dependencies.py        # FastAPI Depends() functions
│   │                          # - auth, rate limiting, file validation
│   │
│   └── middleware.py          # CORS, logging, error handlers
│
├── ela_forgery/               # Error Level Analysis (ELA) & Image Forgery Detection Engine
│   ├── ela.py                 # Core ELA algorithm
│   ├── ghost.py               # GHOST algorithm for compression analysis
│   ├── docdetect.py           # Document alignment/bounding box checks
│   ├── visualize.py           # Heatmap and difference visualization
│   ├── analyze.py             # Main entry point for forgery evaluation
│   ├── dashboard.py           # Local ELA demo dashboard
│   ├── cli.py                 # Command line runner for local testing
│   └── README.md              # ELA engine specific documentation
│
├── pipelines/                 # The other 3 forensic analysis engines
│   ├── __init__.py
│   │
│   ├── metadata_forensics/    # Forensic State Machine
│   │   ├── __init__.py
│   │   ├── state_machine.py   # Chronological validation logic
│   │   ├── exif_parser.py     # PDF/EXIF metadata extraction
│   │   ├── anomaly_rules.py   # Logic checks (CreationDate > ModDate, etc)
│   │   └── scorer.py          # Anomalies → severity score
│   │
│   ├── seal_detection/        # YOLOv8 + Edge Analysis
│   │   ├── __init__.py
│   │   ├── yolo_detector.py   # YOLOv8 inference for seal localization
│   │   ├── edge_analysis.py   # Sharpness, compression metrics on cropped seal
│   │   ├── scorer.py          # Seal anomalies → score
│   │   └── config.py          # YOLOv8 model path, confidence threshold
│   │
│   └── nlp_cross_doc/         # LLM-based Entity Extraction + Consistency
│       ├── __init__.py
│       ├── entity_extractor.py  # NER: PAN, GST, Revenue, Dates, Names (via LLM)
│       ├── consistency_graph.py  # Build entity graph across documents
│       ├── accounting_rules.py   # Assets = Liabilities + Equity, etc
│       └── scorer.py            # Contradictions → anomaly score
│
├── fusion/                    # Risk Scoring & Aggregation
│   ├── __init__.py
│   ├── engine.py              # Weighted Bayesian fusion logic
│   │                          # w_ELA=0.35, w_meta=0.25, w_seal=0.25, w_nlp=0.15
│   ├── weights.py             # Weight configuration
│   └── risk_tier.py           # Score → GREEN/AMBER/RED classification
│
├── ai_investigator/           # Stage 3: LLM-based deeper analysis (Gemma 4 Cloud / Ollama)
│   ├── __init__.py
│   ├── llm_client.py          # Unified LLM client wrapper supporting:
│   │                          # - Google Cloud Vertex AI / AI Studio (Gemma 4 Cloud)
│   │                          # - Local Ollama (for offline development)
│   ├── prompt_builder.py      # Construct evidence-aware prompts
│   │                          # - Pass ELA heatmap, anomalies, metadata
│   ├── reasoning.py           # Interpret LLM output as evidence
│   └── config.py              # LLM configuration (provider, API keys, models, etc.)
│
├── cross_analysis/            # Stage 4: Deep Verification
│   ├── __init__.py
│   ├── registry_client.py     # Internal registry lookups (future: govt APIs)
│   ├── institution_verifier.py # Validate university, govt office existence
│   ├── seal_validator.py      # Compare against known seal database
│   └── historical_comparator.py # Check against previously processed docs
│
├── pattern_detection/         # Stage 5: Coordinated Fraud
│   ├── __init__.py
│   ├── fingerprint.py         # Hash seals, signatures for comparison
│   └── campaign_detector.py   # Detect reused tampering across docs
│
├── report_gen/                # Output Generation
│   ├── __init__.py
│   ├── pdf_builder.py         # WeasyPrint-based PDF report
│   ├── json_serializer.py     # JSON export for downstream systems
│   ├── templates/
│   │   └── report.html        # Jinja2 HTML template (compiled to PDF)
│   └── config.py              # Report styling, logos
│
├── core/                      # Infrastructure & Utilities
│   ├── __init__.py
│   ├── config.py              # Pydantic Settings (env-driven)
│   │                          # DATABASE_URL, REDIS_URL, MODEL_PATH, etc
│   ├── database.py            # SQLAlchemy + PostgreSQL connection
│   ├── models.py              # SQLAlchemy ORM models
│   │                          # - Document, Job, Report, RiskScore tables
│   ├── redis_client.py        # Result caching, job queue
│   ├── storage.py             # File handling (local or GCS)
│   ├── security.py            # API key auth, file sanitization, rate limiting
│   ├── logger.py              # Structured JSON logging
│   └── exceptions.py          # Custom exception classes
│
├── workers/                   # Async task processing
│   ├── __init__.py
│   └── pipeline_worker.py     # Orchestrate all 4 pipelines in parallel
│
├── main.py                    # FastAPI app initialization + startup/shutdown hooks
├── __init__.py
└── pyproject.toml             # Backend-specific deps (for IDE completion)
```

---

## `models/` — Weights & Configuration

```
models/
│
├── yolov8/                    # Seal detection model
│   ├── seal_detector.pt       # Fine-tuned on Indian govt seal dataset
│   ├── metadata.json          # Input size, class names, etc
│   └── config.yaml
│
├── gemma/                     # [DELETED / OPTIONAL] Local Gemma weights
│                              # (Not needed if using Gemma 4 Cloud or local Ollama)
│
├── finbert/                   # [DELETED] (Cross-doc NER utilizes same LLM client, no local weights required)
│
└── registry.json              # Model manifest
    # {
    #   "models": {
    #     "yolov8": {"version": "2", "path": "models/yolov8/seal_detector.pt", "sha256": "..."},
    #     "llm": {"provider": "google|ollama", "model": "gemma-4-cloud|gemma2"}
    #   }
    # }
```

---

## `infra/` — Deployment & Infrastructure

```
infra/
│
├── docker/
│   ├── Dockerfile             # Multi-stage: base + deps + app
│   │                          # Python 3.11 slim, torch/transformers optimized
│   ├── Dockerfile.worker      # (Optional) separate container for heavy pipelines
│   ├── docker-compose.yml     # Local dev: API + Postgres + Redis
│   ├── .dockerignore
│   └── entrypoint.sh          # Initialize DB, migrations
│
├── k8s/                       # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml         # Non-secret config (model versions, log levels)
│   ├── secret.yaml            # (Git-ignored) API keys, DB credentials
│   ├── api-deployment.yaml    # FastAPI replicas, resource limits
│   ├── worker-deployment.yaml # (Optional) separate worker pods for scaling
│   ├── service.yaml           # ClusterIP for internal, LoadBalancer for external
│   ├── ingress.yaml           # /api/* routing, TLS termination
│   └── hpa.yaml               # Horizontal Pod Autoscaler (CPU-triggered)
│
├── terraform/
│   ├── main.tf                # GCP resources: GKE, Cloud SQL, Cloud Storage
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
│
├── nginx/
│   ├── nginx.conf             # Reverse proxy, rate limiting, gzip
│   └── ssl/                   # (Git-ignored) TLS certificates
│
├── .github/
│   └── workflows/
│       ├── ci.yml             # Lint, test, build on every PR
│       │                      # - ruff, mypy, pytest, docker build
│       └── deploy.yml         # Push to GKE on main merge
│
└── README.md                  # Local setup, K8s deployment guide
```

---

## `tests/` — Comprehensive Test Suite

```
tests/
│
├── conftest.py                # Pytest fixtures (DB, mock clients, test docs)
│
├── unit/
│   ├── test_ela.py            # ELA algorithm correctness
│   ├── test_metadata_fsm.py   # State machine logic
│   ├── test_seal_detection.py # YOLOv8 mocking
│   ├── test_nlp_consistency.py # Entity extraction + rules
│   ├── test_fusion_engine.py  # Score aggregation
│   └── test_llm_reasoning.py   # Prompt + response parsing (Gemma 4 / Ollama)
│
├── integration/
│   ├── test_full_pipeline.py  # Upload → all pipelines → report (real models)
│   ├── test_api_endpoints.py  # FastAPI client tests
│   └── test_database.py       # ORM operations
│
├── fixtures/
│   ├── genuine/               # Real documents (redacted)
│   │   ├── aadhaar.pdf
│   │   ├── pan.pdf
│   │   └── certificate.pdf
│   │
│   └── forged/                # Synthetically tampered
│       ├── ela_tampered.pdf   # Pixel-level copy-paste
│       ├── metadata_invalid.pdf
│       ├── seal_cloned.pdf
│       └── nlp_contradictory.pdf
│
├── e2e/
│   ├── conftest.py            # Async fixtures for real API
│   └── test_upload_workflow.py # End-to-end upload → RED/AMBER/GREEN response
│
├── benchmarks/
│   ├── test_throughput.py     # Target: <30s per document
│   ├── test_accuracy.py       # Precision/recall vs fixture set
│   └── test_latency.py        # P99 latency under load
│
└── README.md
```

---

## `packages/` — Shared Python Modules

```
packages/
│
├── shared_types/              # Pydantic models used by both API + workers
│   ├── __init__.py
│   ├── document.py            # Document, DocumentMetadata
│   ├── risk.py                # RiskScore, PipelineResult, RiskTier
│   ├── job.py                 # JobStatus, JobResult
│   └── report.py              # ReportData, ReportMetadata
│
└── risk_schema/               # JSON Schema for risk scoring contract
    ├── __init__.py
    └── schema.json            # Validation schema for all risk outputs
```

---

## Root Configuration Files

```
checkmate/
│
├── pyproject.toml             # Complete Python tooling config
│   # [tool.poetry]
│   # name = "checkmate"
│   # [tool.pytest]
│   # [tool.mypy]
│   # [tool.ruff]
│
├── Makefile                   # Common commands
│   # make dev           → docker-compose up
│   # make test          → pytest with coverage
│   # make lint          → ruff + mypy
│   # make docker-build  → build API image
│   # make k8s-apply     → kubectl apply -f infra/k8s/
│
├── docker-compose.yml         # Local dev
│   # services:
│   #   api: (FastAPI)
│   #   db: (PostgreSQL 15)
│   #   cache: (Redis 7)
│
├── .env.example               # Environment variables template
│   # DATABASE_URL=postgresql://...
│   # REDIS_URL=redis://localhost:6379
│   # LLM_PROVIDER=ollama          # "google" or "ollama"
│   # LLM_MODEL=gemma2             # e.g., "gemma-4-cloud" for production, "gemma2" for local Ollama
│   # GEMMA_API_KEY=your-api-key   # Required if provider is "google"
│   # OLLAMA_API_BASE=http://localhost:11434  # Required if provider is "ollama"
│   # YOLO_MODEL_PATH=models/yolov8/seal_detector.pt
│   # UPLOAD_MAX_SIZE=50MB
│   # LOG_LEVEL=INFO
│   # API_KEY_SECRET=...
│
├── .gitignore
├── README.md                  # Architecture overview + setup guide
└── LICENSE
```

---

## Key Files to Understand the Architecture

### 1. **`backend/main.py`** — App Initialization
```python
# FastAPI setup, middleware, startup/shutdown hooks
# - Load models at startup
# - Initialize DB connections
# - Health checks
```

### 2. **`backend/pipelines/__init__.py`** — Orchestration
```python
# Parallel execution of 4 pipelines
async def run_all_pipelines(document_bytes: bytes) -> PipelineResults:
    # Asyncio.gather all 4 tasks
    # Each returns: anomaly_score, evidence dict, heatmap (if ELA)
```

### 3. **`backend/fusion/engine.py`** — Scoring Logic
```python
# Weighted Bayesian aggregation
# final_score = (w_ela * ela_score) + (w_meta * meta_score) + ...
# risk_tier = GREEN if score < 0.3 else AMBER if score < 0.6 else RED
```

### 4. **`backend/ai_investigator/llm_client.py`** — Unified LLM Integration
```python
# Supports dual-mode execution:
# 1. Ollama: Local inference for offline development (default: gemma2)
# 2. Gemma 4 Cloud: Official Google GenAI API / Vertex AI (default: gemma-4-cloud)

class LLMInvestigator:
    async def analyze_suspicious_doc(
        self,
        doc_bytes: bytes,
        pipeline_results: PipelineResults,
        ela_heatmap: np.ndarray  # or base64-encoded image
    ) -> LLMAnalysisResult:
        # 1. Select provider from config (Ollama vs. Google GenAI)
        # 2. Build prompt with evidence
        # 3. Call endpoint (local Ollama or Gemma 4 Cloud)
        # 4. Parse structured JSON output
```

### 5. **`tests/fixtures/`** — Critical for Hackathon
Build 10–15 synthetically forged documents covering:
- **ELA trigger**: Pixel-level copy-paste of text/signature
- **Metadata trigger**: Invalid creation dates, software mismatches
- **Seal trigger**: Digitally cloned seal vs original
- **NLP trigger**: Revenue figures that don't match across documents

---

## Environment Setup (`.env.example`)

```bash
# Database
DATABASE_URL=postgresql://checkmate:password@localhost:5432/checkmate
REDIS_URL=redis://localhost:6379/0

# LLM Settings
LLM_PROVIDER=ollama  # "google" (Gemma 4 Cloud) or "ollama" (local development)
LLM_MODEL=gemma2     # "gemma-4-cloud" for google, "gemma2" or "gemma:2b" for ollama
GEMMA_API_KEY=your_google_api_key_here
OLLAMA_API_BASE=http://localhost:11434
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.3

YOLO_MODEL_PATH=models/yolov8/seal_detector.pt
YOLO_CONFIDENCE_THRESHOLD=0.5

# File Upload
UPLOAD_MAX_SIZE=50  # MB
UPLOAD_TEMP_DIR=/tmp/checkmate-uploads
OUTPUT_DIR=/tmp/checkmate-output

# API
API_KEY_SECRET=your-secret-key-here
API_RATE_LIMIT=100/minute
LOG_LEVEL=INFO
ENVIRONMENT=development  # or "production"

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

---

## Makefile Quick Reference

```makefile
.PHONY: dev test lint docker-build docker-push deploy clean

dev:
	docker-compose up

test:
	pytest tests/ -v --cov=backend --cov-report=html

lint:
	ruff check backend/
	mypy backend/

docker-build:
	docker build -t checkmate:latest -f infra/docker/Dockerfile .

docker-push:
	docker tag checkmate:latest gcr.io/YOUR_PROJECT/checkmate:latest
	docker push gcr.io/YOUR_PROJECT/checkmate:latest

deploy:
	kubectl apply -f infra/k8s/

clean:
	rm -rf .pytest_cache __pycache__ htmlcov/ .mypy_cache
```

---

## Deployment Paths

### **Local Development**
```bash
make dev
# Runs: API (8000), Postgres (5432), Redis (6379)
```

### **Docker**
```bash
docker build -f infra/docker/Dockerfile -t checkmate:latest .
docker run -p 8000:8000 --env-file .env checkmate:latest
```

### **Kubernetes (GKE)**
```bash
# Configure cluster
gcloud container clusters create checkmate --zone us-central1-a

# Deploy
kubectl create namespace checkmate
kubectl apply -f infra/k8s/

# Check status
kubectl get pods -n checkmate
kubectl logs -n checkmate -l app=api
```

### **Terraform (Full GCP Stack)**
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

---

## Why This Structure?

| Decision | Reasoning |
|----------|-----------|
| **Monorepo** | Single CI, shared types, atomic PRs across backend + tests + infra |
| **API + pipelines separation** | API is thin; pipelines are fat. Easier to scale workers independently |
| **Fusion engine as module** | Scoring weights can be tuned without touching pipelines |
| **LLM in `ai_investigator/`** | Stage 3 of architecture; supports Gemma 4 Cloud & Ollama hot-swapping |
| **`packages/shared_types/`** | Pydantic models stay DRY; API, workers, tests all import from one source |
| **Test fixtures in repo** | Synthetic forged docs are your product validation; version them |
| **Terraform + K8s together** | Infra-as-code for reproducibility; run anywhere (GCP, AWS, on-prem) |

---

## Next Steps

1. **Clone and initialize**:
   ```bash
   git clone <repo>
   cd checkmate
   cp .env.example .env
   make dev
   ```

2. **Verify structure**:
   ```bash
   tree -L 3 backend/ -I "__pycache__"
   ```

3. **Run tests**:
   ```bash
   make test
   ```

4. **Build Docker image**:
   ```bash
   make docker-build
   ```

5. **Deploy to Kubernetes**:
   ```bash
   make deploy
   ```

