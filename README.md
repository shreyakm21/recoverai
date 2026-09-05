# recoverai
Intelligent failed-payment recovery system with policy-controlled recovery and Razorpay Test Mode integration


# RecoverAI

> Intelligent, policy-controlled recovery for failed digital payments.

RecoverAI is a failed-payment recovery system that analyzes why a payment failed, recommends an appropriate recovery strategy, validates that strategy against safety policies, executes recovery actions, and maintains a complete audit trail.

Built for the **Razorpay AI Buildathon**.

---

## The Problem

A failed payment does not always mean a lost customer.

Failures can happen because of:

- temporary bank timeouts
- payment gateway errors
- insufficient funds
- authentication failures
- customers abandoning checkout

Simply retrying every failed payment is ineffective and can also create a poor customer experience.

Different failures need different recovery strategies.

RecoverAI turns:

```text
Payment Failed
```

into:

```text
Understand Failure
       ↓
Recommend Recovery
       ↓
Validate Safety Policy
       ↓
Execute Recovery
       ↓
Track Outcome
       ↓
Audit Everything
```

---

## What RecoverAI Does

For every failed payment, RecoverAI evaluates the failure and selects an appropriate recovery action.

| Failure | Recovery Strategy |
|---|---|
| `BANK_TIMEOUT` | `RETRY` |
| `GATEWAY_ERROR` | `RETRY` |
| `INSUFFICIENT_FUNDS` | `SEND_REMINDER` |
| `CUSTOMER_ABANDONED` | `SEND_PAYMENT_LINK` |
| `AUTH_FAILURE` | `REAUTHENTICATE` |

The recommendation is **not executed blindly**.

Every action must first pass through the **Policy Engine**.

---

## Core Design Principle

> **The advisor recommends. The policy engine decides. Every action is auditable.**

RecoverAI deliberately separates reasoning from execution.

This allows intelligent recovery decisions while ensuring that financial actions remain bounded by deterministic safety rules.

---

# System Architecture

```text
                     ┌──────────────────────┐
                     │   Failed Payments    │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │   FastAPI Backend    │
                     └──────────┬───────────┘
                                │
               ┌────────────────┴────────────────┐
               │                                 │
               ▼                                 ▼
      ┌─────────────────┐               ┌─────────────────┐
      │ Recovery Advisor│               │  Policy Engine  │
      │                 │               │                 │
      │ Diagnose failure│               │ Validate action │
      │ Recommend action│               │ Enforce limits  │
      │ Assess risk     │               │ Block unsafe    │
      └────────┬────────┘               └────────┬────────┘
               │                                 │
               └────────────────┬────────────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │  Recovery Executor   │
                     └──────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
           ┌────────────────┐      ┌──────────────────┐
           │ Recovery       │      │ Razorpay         │
           │ Simulation     │      │ Test Mode        │
           └───────┬────────┘      └────────┬─────────┘
                   │                        │
                   └───────────┬────────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │   Recovery Audit   │
                     │       Trail        │
                     └─────────┬──────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │ Streamlit Dashboard│
                     └────────────────────┘
```

---

# Recovery Advisor

The Recovery Advisor analyzes:

- failure type
- transaction amount
- payment method
- previous retry count

and produces:

- diagnosis
- recommended action
- reasoning
- risk level

Example:

```json
{
  "diagnosis": "Temporary payment gateway failure",
  "recommended_action": "RETRY",
  "reasoning": "A temporary gateway error may succeed on another attempt, provided retry limits are respected.",
  "risk_level": "LOW"
}
```

### Current AI implementation

The current Buildathon prototype uses a **deterministic recovery advisor** rather than a live LLM API.

This gives the prototype:

- reproducible decisions
- predictable demonstrations
- zero external LLM dependency
- safe fallback behavior

The advisor is isolated behind a service layer so that an LLM can later be introduced for richer contextual reasoning without giving the model direct authority to execute financial actions.

---

# Policy Engine

The Policy Engine is RecoverAI's safety layer.

For example:

### Temporary failure

```text
GATEWAY_ERROR
      ↓
Advisor: RETRY
      ↓
Policy: ALLOWED
      ↓
Recovery may execute
```

### Authentication failure

```text
AUTH_FAILURE
      ↓
Advisor: REAUTHENTICATE
      ↓
Policy: BLOCKED
      ↓
No automatic financial action
```

The policy layer prevents the recommendation system from blindly performing unsafe actions.

---

# Recovery Actions

RecoverAI supports multiple recovery strategies:

### RETRY

Used for failures likely to be temporary, such as:

- `BANK_TIMEOUT`
- `GATEWAY_ERROR`

Retries are bounded to prevent uncontrolled repeated attempts.

### SEND_REMINDER

Used when immediate retries are unlikely to help.

Example:

```text
INSUFFICIENT_FUNDS
```

### SEND_PAYMENT_LINK

Used when the customer showed purchase intent but abandoned checkout.

Example:

```text
CUSTOMER_ABANDONED
```

### REAUTHENTICATE

Used for authentication-related failures.

Automatic execution is blocked because customer authentication may be required.

---

# Recovery Audit Trail

Every recovery attempt is recorded.

Example:

```json
{
  "recommended_action": "SEND_PAYMENT_LINK",
  "action_allowed": true,
  "decision_reason": "Customer abandoned checkout and may complete payment later.",
  "recovery_result": "FAILED",
  "recovered_amount": 0,
  "processed_at": "2026-09-03T07:43:39"
}
```

RecoverAI distinguishes between:

```text
retry_count
```

and:

```text
recovery attempt count
```

For example, sending a payment link is a recovery attempt but **not a payment retry**.

This provides a more accurate recovery history.

---

# Razorpay Test Mode Integration

RecoverAI integrates with **Razorpay Test Mode** to demonstrate an actual checkout-based recovery flow without using real money.

The integration follows:

```text
Failed RecoverAI Payment
          ↓
Create Razorpay Order
          ↓
Razorpay Standard Checkout
          ↓
Complete Test Payment
          ↓
Backend Signature Verification
          ↓
Validate Razorpay Payment
          ↓
Mark Payment RECOVERED
          ↓
Create Audit Record
```

The backend validates payment information before updating RecoverAI's internal state.

A successful verified recovery produces an audit entry such as:

```text
Recommended Action : RAZORPAY_CHECKOUT
Action Allowed     : true
Recovery Result    : RECOVERED
```

---

## Razorpay Verification

RecoverAI performs server-side verification rather than trusting the browser's success callback alone.

The backend validates information including:

- Razorpay payment signature
- Razorpay order
- payment details
- expected payment amount
- payment/order association
- payment status

Only after successful verification is the RecoverAI transaction marked as recovered.

---

# Recovery Dashboard

RecoverAI includes an interactive **Streamlit dashboard**.

The dashboard provides:

### Business KPIs

- Initial Revenue at Risk
- Revenue Recovered
- Recovery Rate
- Remaining Failed Payments
- Remaining Revenue at Risk
- Blocked Payments

### Recovery Analytics

- recovery progress
- failure distribution
- failed-payment table

### Recovery Agent

Users can select an individual failed payment and inspect:

- failure reason
- transaction amount
- retry count
- advisor diagnosis
- recommended recovery action
- risk level
- policy decision

### Recovery Execution

Allowed recovery actions can be triggered directly from the dashboard.

### Audit Timeline

Every previous recovery attempt for the selected payment is visible in the dashboard.

---

# Prototype Evaluation

RecoverAI was evaluated using a synthetic payment dataset.

## Dataset

```text
Total transactions       : 200
Successful transactions  : 146
Failed transactions      : 54
Initial revenue at risk  : ₹89,546
```

The generated dataset contains different payment methods and failure scenarios.

---

## Initial Batch Simulation

The initial reproducible recovery simulation produced:

```text
Failed transactions processed : 54
Recovered payments             : 27
Revenue recovered              : ₹44,973
Recovery rate                  : 50.22%
Blocked actions                : 6
Unresolved payments            : 27
```

The live application state changes as additional recovery actions and Razorpay Test Mode recoveries are performed.

Therefore, dashboard values may differ from the initial batch simulation.

> These results are produced using synthetic transactions and simulated recovery probabilities. They are prototype results and are not Razorpay production statistics.

---

# Example Recovery Flow

Consider:

```text
Payment ID   : pay_00003
Amount       : ₹199
Failure      : GATEWAY_ERROR
```

RecoverAI initially determines:

```text
Diagnosis           : Temporary payment gateway failure
Recommended Action  : RETRY
Risk                : LOW
Policy              : ALLOWED
```

An earlier simulated recovery attempt failed.

The payment was then recovered through Razorpay Test Mode.

Audit history:

```text
Attempt 1
RETRY
→ FAILED

Attempt 2
RAZORPAY_CHECKOUT
→ RECOVERED
```

Final state:

```text
status           : success
recovery_status  : recovered
recovered_amount : ₹199
```

This demonstrates recovery from the original failure through verified checkout and audit tracking.

---

# Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite

### Recovery

- Custom Recovery Advisor
- Deterministic Policy Engine
- Recovery simulation engine

### Payment Integration

- Razorpay Python SDK
- Razorpay Orders
- Razorpay Standard Checkout
- Razorpay Test Mode
- Signature verification

### Dashboard

- Streamlit
- Pandas
- Requests

---

# API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend health |
| `GET` | `/payments/failed` | List currently failed payments |
| `GET` | `/recovery/summary` | Recovery KPIs |
| `GET` | `/recovery/advice/{payment_id}` | Recovery recommendation |
| `POST` | `/recovery/process/{payment_id}` | Process individual recovery |
| `POST` | `/recovery/process-batch` | Process failed payments in batch |
| `GET` | `/recovery/audit/{payment_id}` | View recovery history |
| `POST` | `/razorpay/order/{payment_id}` | Create Razorpay test order |
| `POST` | `/razorpay/verify` | Verify checkout payment |
| `POST` | `/razorpay/webhook` | Razorpay webhook endpoint |

FastAPI automatically exposes interactive API documentation through Swagger UI.

---

# Running RecoverAI Locally

## 1. Clone the repository

```bash
git clone https://github.com/shreyakm21/recoverai.git
cd recoverai
```

## 2. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Razorpay Test Mode

Create:

```text
.env
```

and add your own Razorpay Test Mode credentials:

```env
RAZORPAY_KEY_ID=your_test_key
RAZORPAY_KEY_SECRET=your_test_secret
```

The `.env` file is excluded from Git.

Never commit payment credentials.

## 5. Generate transactions

```bash
python -m simulator.generate_transactions
```

## 6. Seed the database

```bash
python -m simulator.seed_database
```

## 7. Start the API

```bash
uvicorn app.main:app --reload
```

FastAPI:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 8. Start the dashboard

In another terminal:

```bash
streamlit run dashboard/app.py
```

The dashboard will normally be available at:

```text
http://localhost:8501
```

---

# Project Structure

```text
recoverai/
│
├── app/
│   ├── api/
│   │   └── recovery.py
│   │
│   ├── database/
│   │   └── db.py
│   │
│   ├── models/
│   │   ├── payment.py
│   │   └── recovery_audit.py
│   │
│   ├── services/
│   │   ├── ai_recovery_advisor.py
│   │   ├── razorpay_service.py
│   │   └── recovery_engine.py
│   │
│   └── main.py
│
├── dashboard/
│   ├── app.py
│   └── test_checkout.html
│
├── data/
│   ├── transactions.csv
│   └── recovery_audit.csv
│
├── simulator/
│   ├── generate_transactions.py
│   ├── recovery_simulator.py
│   ├── seed_database.py
│   └── test_recovery_engine.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

# Security & Safety

RecoverAI includes several safeguards:

- payment secrets stored outside source control
- server-side Razorpay signature verification
- bounded payment retries
- authentication failures blocked from unsafe automatic recovery
- advisor separated from policy enforcement
- recovery attempts stored in an audit trail
- duplicate recovery of already successful payments rejected
- unknown failures routed toward safer handling

---

# Current Limitations

RecoverAI is a Buildathon prototype.

The current version has the following limitations:

- transaction data is synthetic
- recovery success/failure outcomes are simulated
- reminder delivery is simulated
- payment-link intervention is simulated
- the Recovery Advisor currently uses deterministic reasoning rather than a live LLM
- SQLite is used for local persistence
- the dashboard and API run locally
- production webhook delivery would require a permanently deployed public backend

These choices keep the prototype reproducible while demonstrating the complete recovery architecture.

---

# Future Scope

RecoverAI can be extended with:

- LLM-powered contextual recovery reasoning
- payment-success prediction
- customer behavior modeling
- merchant-specific recovery policies
- scheduled smart retries
- email/SMS/WhatsApp reminders
- production payment-link generation
- webhook-driven recovery workflows
- PostgreSQL
- background task queues
- idempotent payment processing
- merchant-level analytics
- recovery strategy A/B testing
- cloud deployment

---

# Why RecoverAI?

RecoverAI is not simply a payment retry system.

It demonstrates how an intelligent recovery agent can combine:

```text
Reasoning
+
Deterministic Safety
+
Payment Infrastructure
+
Business Analytics
+
Auditability
```

to recover revenue without blindly retrying failed transactions.

---

## Built for Razorpay AI Buildathon

**Project:** RecoverAI  
**Focus:** Intelligent Failed Payment Recovery  
**Payment Integration:** Razorpay Test Mode
