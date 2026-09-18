# AML Investigator

Agentic AML / transaction-monitoring investigation platform for a bank compliance desk.

The system allows an authorized compliance user to investigate transactions using transaction data, customer information, alerts, sanctions screening, deterministic risk signals, and regulatory evidence.

This project is intentionally scoped as a working prototype.

## Architecture

```text
Natural-language query
        ↓
Authorization / RBAC
        ↓
Screening Agent
        ↓
Structured investigation package
        ↓
Investigation Agent
        ↓
Regulatory evidence retrieval
        ↓
Explainable investigation result
        ↓
Audit + analyst feedback
```

The system uses two agents:

* **Screening Agent** — gathers authorized transaction, customer, alert and sanctions evidence and calculates deterministic risk signals.
* **Investigation Agent** — receives the screening package and retrieves relevant regulatory evidence before producing the investigation findings.

RBAC is enforced in the backend data-access layer before restricted data is passed to the agents.


## Roles

| Role                 | Access                                                             |
| -------------------- | ------------------------------------------------------------------ |
| CCO                  | Full investigation and customer access                             |
| AML Analyst          | Transactions, alerts, sanctions and masked customer data           |
| External Auditor     | Audit, rationale and evidence without raw customer/transaction PII |
| Relationship Manager | Assigned-portfolio transactions, alerts and masked customer data   |

Authorization is performed before restricted information is provided to the agents.


## Example Investigation

The main demonstration case is:

```text
Why was transaction TXN1042 flagged, and does it violate any applicable AML requirements?
```

The investigation combines:

```text
TXN1042 → $9,800 → UAE
TXN1043 → $9,700 → UAE
TXN1047 → $18,500 → Singapore
ALT-102 → HIGH severity alert
```

The system identifies deterministic risk signals, retrieves relevant regulatory evidence, and produces an explainable investigation result.

A probable sanctions match remains classified as **probable** and is not automatically treated as a confirmed match.

## Project Structure

```text
aml-investigator/
├── app/
│   ├── agents/                 # Screening and Investigation agents
│   ├── auth/                   # RBAC and user context
│   ├── retrieval/              # Regulatory retrieval and ChromaDB
│   ├── tools/                  # Controlled investigation tools
│   ├── models.py               # Database models
│   └── db.py                   # Database configuration
│
├── data/
│   ├── raw/                    # Source documents
│   ├── processed/              # Processed data
│   └── understanding/          # Regulatory understanding files
│
├── eval/                       # Evaluation cases and runner
├── frontend/                   # Streamlit application
├── scripts/                    # Database/data/index setup scripts
├── tests/                      # Automated tests
│
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

### 1. Create the environment

```powershell
python -m venv .avenv
.\.avenv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Create `.env` from `.env.example` and configure the LLM provider/API key.

Do not commit `.env` or API keys to the repository.

### 4. Initialize the database

```powershell
python -m scripts.init_db
python -m scripts.load_data
python -m scripts.verify_data
```

### 5. Build the regulatory index

```powershell
python -m scripts.index_regulations
```

## Run the Application

```powershell
streamlit run frontend\streamlit_app.py
```

The Streamlit interface provides:

* Investigation
* Alerts
* Audit Trail
* Evaluation
* System information

## Evaluation

Run the evaluation suite with:

```powershell
python -m eval.run_evaluation
```

Run the complete automated tests with:

```powershell
python -m pytest -q
```

Prompt-injection defense is not implemented in the current version and is treated as a deferred bonus feature.

## What Breaks at 100×

### 1. Database scalability

SQLite will become a bottleneck with significantly larger transaction volumes and concurrent users.

A production implementation would use a scalable relational database with appropriate indexing, connection pooling and partitioning.

### 2. Regulatory retrieval scalability

The current ChromaDB setup is designed for a small regulatory corpus.

At much larger scale, the system would need scalable search infrastructure, metadata filtering, document/version management and retrieval-quality monitoring.

### 3. LLM rate limits

LLM provider rate limits can become a bottleneck with many concurrent investigations.

A production system would require caching, throttling, asynchronous processing, fallback models/providers and stronger observability.
