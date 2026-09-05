# FailureForge 🔥

> **An adversarial evaluation engine that turns autonomous-agent failures into robust benchmark tasks and tests whether the evaluator itself can be gamed.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Pytest](https://img.shields.io/badge/pytest-passed-brightgreen.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 The Core Thesis

Most agent evaluation frameworks ask a simple question:  
> *"Did the final state look correct?"*

**FailureForge** asks a much harder, production-grade question:  
> *"Did the agent actually accomplish the task correctly, through a valid causal path, without exploiting weaknesses in the environment or grader?"*

FailureForge evaluates **both the agent and the verifier**.

---

## ✨ Features

1. **Reward-Hacking Detection (7 Specialized Detectors)**:
   - `direct_state_manipulation`: Detects direct database record setting bypassing business logic tool workflows.
   - `premature_confirmation`: Catches notifications sent before underlying transactions complete.
   - `tool_order_bypass`: Identifies skipped prerequisites (e.g. eligibility check bypassed before refund creation).
   - `duplicate_side_effect`: Flags non-idempotent duplicate actions.
   - `wrong_entity_modification`: Detects state mutations applied to wrong entities.
   - `impossible_transition`: Prevents invalid domain state jumps.
   - `grader_targeted_manipulation`: Flags mutations targeted strictly at grader-visible fields.

2. **Automatic Benchmark Generation**:
   - Takes failed agent trajectories, extracts the root failure pattern, and auto-generates new, hardened benchmark tasks with custom invariants and verifier rules.

3. **Grader Red-Teaming**:
   - Evaluates whether the verifier itself can be gamed by running 8 adversarial attack patterns, producing a **Grader Robustness Score**.

4. **Zero-Friction Local & Docker Running**:
   - Standalone launcher script (`python run_demo.py`) that auto-installs missing dependencies and runs out-of-the-box.
   - Docker containerization & `docker-compose` support for isolated reproducible runs.

---

## 🚀 Quick Start (Zero Setup Required)

### Option 1: One-Line Python Run
Clone the repository and run:

```bash
python run_demo.py
```
*`run_demo.py` automatically installs dependencies if missing and launches the interactive demonstration!*

---

## 🔑 LLM API Key Configuration (Groq / OpenAI)

FailureForge includes **two modes of execution**:
1. **Zero-Setup Local Demo Mode (Default)**: Uses deterministic honest and adversarial reference agents so anyone can run the demo **immediately without needing any API key**.
2. **Live LLM Agent Mode**: Evaluates real LLMs dynamically (Groq, OpenAI, or any OpenAI-compatible provider).

### How to pass your API key:

#### Option A: Set environment variables in `.env`
Copy `.env.example` to `.env` and set your key:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
# OR
OPENAI_API_KEY=sk-your_openai_api_key_here
```

#### Option B: Export in terminal
```bash
export GROQ_API_KEY="gsk_your_groq_api_key_here"
```

#### Running Live LLM Task Evaluation:
```bash
python -m failureforge.cli.main run --agent llm --task CS-001
```

---

### Option 2: Docker / Docker Compose


```bash
docker compose up
```

---

### Option 3: Manual Installation

```bash
# Clone the repository
git clone https://github.com/viren/failureforge.git
cd failureforge

# Install dependencies
pip install -r requirements.txt

# Run full test suite
python -m pytest tests/

# Run CLI demo
python -m failureforge.cli.main demo

# Start REST API server
uvicorn failureforge.main:app --reload --port 8000
```

---

## 🧪 How to Test Real Scenarios & Modify Inputs

Reviewers and engineers can test FailureForge and modify task inputs in 4 different ways:

### 1. View Available Benchmark Tasks
```bash
python -m failureforge.cli.main tasks
```
Lists all 15 tasks (`task-01` through `task-15`) with difficulties, required invariants, and policy constraints.

### 2. Run Real Agent Executions on Any Task
```bash
# Run honest agent on task-01
python -m failureforge.cli.main run task-01 --agent honest

# Run adversarial agent (reward-hacking attack)
python -m failureforge.cli.main run task-01 --agent adversarial

# Run live Groq/OpenAI LLM agent on task-01
python -m failureforge.cli.main run task-01 --agent llm
```

### 3. Modify Task Inputs & Seed Scenarios
Task input data (customers, orders, price amounts, delivery statuses, tickets) is defined in [`seeder.py`](file:///d:/Project/failureforge/backend/failureforge/environments/customer_support/seeder.py).
To modify order prices, customer statuses, or add new task data:
1. Open `backend/failureforge/environments/customer_support/seeder.py` and modify `SEED_DATA`.
2. Re-seed database: `python -m failureforge.cli.main seed`
3. Re-run task: `python -m failureforge.cli.main run task-01 --agent honest`

### 4. Interactive Web API (Swagger UI)
Start the REST API server:
```bash
uvicorn failureforge.main:app --reload --port 8000
```
Open **`http://localhost:8000/docs`** in your browser to interactively execute tasks, inspect trajectories, run grader red-teaming, and view overview analytics via OpenAPI Swagger interface!

---

## 🛠️ Architecture


```
failureforge/
├── backend/
│   ├── failureforge/
│   │   ├── api/                  # FastAPI endpoints (/tasks, /runs, /benchmarks, /grader-reports)
│   │   ├── benchmark_generation/ # Automatic benchmark candidate generator
│   │   ├── cli/                  # Rich interactive CLI
│   │   ├── engine/               # Main orchestration & trajectory engine
│   │   ├── environments/         # Stateful customer support environment & SEED data
│   │   ├── execution/            # HonestAgent, AdversarialAgent, LLMAgent (Groq/OpenAI)
│   │   ├── invariants/           # Invariant checker & rules
│   │   ├── redteam/              # Grader red-team suite (8 attack types)
│   │   ├── reward_hacking/       # 7 reward-hacking detection algorithms
│   │   └── verification/         # Causal & Outcome verifier engines
├── tests/
│   ├── unit/                     # Unit test suite
│   └── integration/              # FastAPI integration tests
├── Dockerfile                    # Containerization spec
├── docker-compose.yml            # Multi-service setup
└── run_demo.py                   # Zero-friction auto-installer & launcher
```

---

## 📊 Live Demo Output Overview

When you run `python run_demo.py`:
- **Agent A (HonestAgent)** runs a multi-step task following proper eligibility check -> refund creation -> email notification order.
- **Agent B (AdversarialAgent)** executes a reward-hacking attack using direct DB mutations (`_direct_set_refund_status`).
- **Naive Grader**: Grades **BOTH** agents as `PASS` (False positive for Agent B!).
- **FailureForge Engine**: Detects `direct_state_manipulation` & `premature_confirmation`, marking Agent B as `SUSPICIOUS` / `FAIL`.

---

## 📄 License

MIT License. Free to use for agent benchmarking and evaluation research.
