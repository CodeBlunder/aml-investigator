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

## Main Features

* Natural-language AML investigation queries
* Two-agent workflow with structured handoff
* Role-based access control
* Customer PII masking
* Relationship Manager portfolio restrictions
* Deterministic AML risk signals
* Sanctions/watchlist screening
* Regulatory evidence retrieval
* ChromaDB semantic regulatory index
* Analyst feedback mechanism
* Audit logging
* Automated evaluation suite

## Roles

| Role                 | Access                                                             |
| -------------------- | ------------------------------------------------------------------ |
| CCO                  | Full investigation and customer access                             |
| AML Analyst          | Transactions, alerts, sanctions and masked customer data           |
| External Auditor     | Audit, rationale and evidence without raw customer/transaction PII |
| Relationship Manager | Assigned-portfolio transactions, alerts and masked customer data   |

Authorization is performed before restricted information is provided to the agents.

## Data

Transaction, customer, alert, sanctions and feedback data is synthetic.

Regulatory evidence is based on the public **RBI Master Direction - Know Your Customer (KYC) Direction, 2016**.

```text
data/
├── raw/                         # Source regulatory document
├── understanding/              # Structured regulatory requirements
└── chroma/                      # Regulatory vector index
```

No real customer PII is used.

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

The evaluation suite covers areas including:

* Transaction investigation
* Related transactions
* Deterministic risk assessment
* Alerts
* Sanctions screening
* Regulatory evidence
* RBAC restrictions
* Insufficient or missing data

Update the final pass counts in this README after the final test run.

## Security Design

The application does not allow the agents to execute arbitrary SQL.

Instead, agents use controlled backend tools such as:

```text
get_transaction()
search_transactions()
get_customer()
get_alert()
find_alerts()
search_sanctions()
search_regulations()
```

This provides a constrained interface between the agents and the underlying data.

RBAC and row-level restrictions are enforced before data is returned.

## Feedback

Analyst feedback can be recorded against investigation outcomes.

The current feedback signals include:

```text
TRUE_HIT
FALSE_POSITIVE
ESCALATED
```

Feedback is intended to provide a mechanism for improving future investigation behavior.

## Regulatory Evidence

The regulatory pipeline is:

```text
RBI PDF
   ↓
PDF extraction
   ↓
Structured requirements
   ↓
ChromaDB indexing
   ↓
Semantic retrieval
   ↓
Investigation Agent
```

The regulatory understanding files and indexing script are included so the regulatory index can be regenerated.

## Current Limitations

This is a prototype and is not intended for production banking use.

The current implementation has simplified:

* AML risk rules
* Regulatory retrieval
* Database infrastructure
* LLM infrastructure
* Feedback learning

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

## Summary

AML Investigator demonstrates an end-to-end agentic AML investigation workflow while keeping critical controls outside the LLM.

The design separates:

```text
Authorization
    +
Deterministic risk detection
    +
Evidence retrieval
    +
Agent reasoning
    +
Auditability
```

This allows the LLM to assist with investigation and explanation without making it the authority for access control or deterministic AML risk decisions.
