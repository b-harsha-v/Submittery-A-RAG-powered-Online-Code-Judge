# 🚀 Submittery: A RAG-Powered AI Online Judge & Pair-Programming Platform

![Submittery Banner](https://img.shields.io/badge/Submittery-v5.0-6366f1?style=for-the-badge&logo=codeforces&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_15-pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-Flash_%26_Embeddings-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Sandbox_Isolation-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EC2_%26_CI%2FCD-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)

> **Submittery** is a next-generation competitive programming judge and collaborative coding platform. Unlike traditional static judges that only return raw verdicts, Submittery integrates an **asynchronous, continuous-learning Retrieval-Augmented Generation (RAG)** knowledge engine grounded in PostgreSQL (`pgvector`) and Google Gemini. It dynamically harvests community failure patterns, provides tiered Socratic hints without spoiling solutions, and conducts deep code-aware failure diagnostics in real time.

---

## 🌟 Core Features & Innovations

### 1. 🧠 Continuous-Learning RAG Failure Engine
- **Failure-Augmented Pitfall Harvesting**: When a submission fails (Wrong Answer, Time Limit Exceeded, Runtime Error), the background worker analyzes the execution trace and embeds the failure signature into vector memory (`pgvector`).
- **Dynamic Cluster Aggregation**: High-similarity failure patterns (>0.86 cosine similarity) are merged into recurring pitfall clusters with occurrence counts, continuously refining the judge's diagnostic precision.
- **Non-Spoiling Socratic Failure Diagnostics**: Instead of giving away the answer, Submittery inspects the student's live editor code, compares it with canonical invariants and historical pitfall memory, and provides targeted guiding questions.

### 2. 💡 3-Tier Grounded Socratic Hints
- **Tier 1 (High-Level Intuition)**: Conceptual problem framing and pattern recognition (e.g., "Think about two-pointer sliding windows").
- **Tier 2 (State Invariant & Math Relation)**: Core logical invariants without code syntax (e.g., "Maintain $\min(L[i], R[i]) - H[i]$").
- **Tier 3 (Edge Cases & Boundaries)**: Specific boundary pitfalls and tricky edge cases tailored to what the student has typed so far.

### 3. 🔍 Natural Language Semantic Problem Search
- Search across the entire problem bank using algorithmic concepts and real-world descriptions (e.g., *"Find problems involving monotonic stack and water elevation"* or *"Dynamic programming on grids with obstacles"*).

### 4. ⚡ Monaco Code-Aware AI Assistant
- Live synchronization between the **Monaco Code Editor** and the AI Assistant. Students can highlight or edit code and ask direct contextual questions (e.g., *"Why is my loop on line 14 timing out?"*).

### 5. 🛡️ High-Performance Micro-Container Sandbox
- Untrusted student code executes inside ephemeral, non-networked Docker micro-containers with strict resource constraints:
  - Memory hard-capped with swap disabled (`--memory=256m --memory-swap=256m`)
  - CPU usage restricted (`--cpus=0.5`)
  - Read-only root filesystem with isolated ephemeral workspace
  - Non-privileged system user (`nobody:nogroup`) execution
  - Sub-millisecond runtime and memory measurement

### 6. 🌐 Real-Time Collaboration & WebSockets
- Real-time submission queue streaming.
- Live multi-user leaderboards and live test execution logs.
- Google OAuth 2.0 & JWT authentication with fine-grained role-based access control (Admin / Student).

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer[Client / Frontend Layer]
        Browser[Modern Browser / Monaco Editor]
        Auth[Google OAuth / JWT Auth]
        WSClient[WebSocket Real-time Client]
    end

    subgraph ReverseProxy[Reverse Proxy & Edge]
        Nginx[Nginx Reverse Proxy :80/:443]
    end

    subgraph ApplicationLayer[FastAPI Application Services]
        Backend[FastAPI Backend :8000\nAuth / Problems / Submissions / AI API]
        CompilerService[Compiler Sandbox API :8002\nDocker-out-of-Docker Manager]
        Worker[Background Worker / Judge Engine\nRedis Queue Consumer & RAG Harvester]
    end

    subgraph DataAndAILayer[Data, Cache & Vector Intelligence]
        DB[(PostgreSQL 15 + pgvector :5432\nProblems / Submissions / Chunks / Pitfalls)]
        Redis[(Redis 7 :6379\nQueue & Pub/Sub Leaderboard)]
        Gemini[Google Gemini Flash\nText & Vector Embeddings API]
    end

    subgraph ExecutionSandbox[Isolated Micro-Sandbox]
        DHost[Host Docker Engine]
        Box1[Sandbox Container #1\nNo Net / Read-Only / CPU Capped]
        Box2[Sandbox Container #2\nNon-Root / Memory Capped]
    end

    Browser --> Nginx
    WSClient --> Nginx
    Nginx --> Backend
    Backend --> DB
    Backend --> Redis
    Backend --> Gemini
    
    Backend -->|Push Submission Job| Redis
    Worker -->|Pop Job| Redis
    Worker -->|POST /execute| CompilerService
    CompilerService -->|DooD Socket| DHost
    DHost --> Box1
    DHost --> Box2
    
    Worker -->|Harvest Failures & Save Verdict| DB
    Worker -->|Embed Failure Patterns| Gemini
    Worker -->|Broadcast Verdict| Redis
    Redis -->|WebSocket Event| Backend
    Backend -->|Real-time Verdict Stream| WSClient
```

---

## 🗄️ Database & Vector Schema

Submittery uses PostgreSQL 15 with the `pgvector` extension for storing structured data and high-dimensional semantic embeddings:

```mermaid
erDiagram
    USERS ||--o{ SUBMISSIONS : submits
    PROBLEMS ||--o{ TEST_CASES : contains
    PROBLEMS ||--o{ SUBMISSIONS : evaluated_on
    PROBLEMS ||--o{ PROBLEM_KNOWLEDGE_CHUNKS : has_canonical_chunks
    PROBLEMS ||--o{ SUBMISSION_PITFALLS : accumulates_pitfall_memory

    USERS {
        uuid id PK
        string email
        string username
        string role
    }

    PROBLEMS {
        uuid id PK
        string title
        string slug
        string difficulty
        text description
        float time_limit
        int memory_limit
    }

    PROBLEM_KNOWLEDGE_CHUNKS {
        uuid id PK
        uuid problem_id FK
        string chunk_type
        string title
        text content
        vector embedding
    }

    SUBMISSION_PITFALLS {
        uuid id PK
        uuid problem_id FK
        string verdict
        text failed_testcase_summary
        text code_pattern
        text pitfall_summary
        text socratic_guidance
        vector embedding
        int occurrence_count
    }

    SUBMISSIONS {
        uuid id PK
        uuid user_id FK
        uuid problem_id FK
        text code
        string status
        float runtime
        int memory
    }
```

---

## 📂 Project Structure

```
.
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # REST & WebSocket Route Controllers
│   │   ├── core/             # Security, JWT, Rate Limiters
│   │   ├── models/           # SQLAlchemy & pgvector Database Models
│   │   ├── services/         # AI Service & RAG Knowledge Engine
│   │   ├── static/           # Single-Page App (HTML, Vanilla JS, CSS)
│   │   └── main.py           # Application Entrypoint & Startup Seeds
├── compiler_service/         # Ephemeral Micro-Sandbox Manager
│   ├── sandbox/              # Sandbox Container Blueprint (Dockerfile & Runner)
│   └── main.py               # Sandbox Execution API
├── worker/                   # Background Async Judge & RAG Harvester
│   └── main.py               # Redis Queue Worker Loop
├── docker-compose.yml        # PostgreSQL (pgvector) & Redis Infrastructure
└── requirements.txt          # Unified Python Dependencies
```

---

## 🛠️ Setup & Running Guide

### 1. Prerequisites
- [Git](https://git-scm.com/)
- [Python 3.11+](https://www.python.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine (ensure Docker daemon is running)

### 2. Clone and Configure Environment
```bash
git clone https://github.com/b-harsha-v/Submittery-A-RAG-powered-Online-Code-Judge.git
cd Submittery-A-RAG-powered-Online-Code-Judge

# Copy example environment file
cp .env.example .env
```

Edit `.env` and supply your credentials:
```env
# Google Gemini API (Required for AI RAG Features)
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Google OAuth (Optional for Google Sign-In)
GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com

# Database & Redis Settings
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5435/submittery
REDIS_URL=redis://localhost:6385/0
COMPILER_SERVICE_URL=http://localhost:8002
```

### 3. Start Database & Cache Containers
```bash
docker compose up -d
```
*Spins up PostgreSQL 15 with `pgvector` on port `5435` and Redis on port `6385` with persistent data volumes.*

### 4. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 5. Launch the Services

Open 3 terminal windows (or run with process managers like `tmux` / `systemd` / `supervisord`):

**Terminal 1 — Compiler Sandbox Service:**
```bash
uvicorn compiler_service.main:app --host 0.0.0.0 --port 8002
```

**Terminal 2 — Background Worker & RAG Harvester:**
```bash
python -m worker.main
```

**Terminal 3 — FastAPI Backend & Web Server:**
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **`http://localhost:8000`** in your browser!

---

## ☁️ Running on AWS EC2

To host Submittery on an **AWS EC2 Ubuntu Instance** (e.g. `t3.small` / `t3.medium`):

1. **Install Docker & Python**:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose python3-pip python3-venv git
   sudo usermod -aG docker $USER
   ```
2. **Clone & Configure**:
   ```bash
   git clone https://github.com/b-harsha-v/Submittery-A-RAG-powered-Online-Code-Judge.git
   cd Submittery-A-RAG-powered-Online-Code-Judge
   cp .env.example .env
   # Add your GEMINI_API_KEY to .env
   ```
3. **Start Persistent PostgreSQL + Redis**:
   ```bash
   docker compose up -d
   ```
4. **Install Requirements & Run Services**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Start the 3 services in background / tmux / systemd
   uvicorn compiler_service.main:app --host 0.0.0.0 --port 8002 &
   python3 -m worker.main &
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
   ```
5. Open **Port 8000** (or Port 80 via Nginx reverse proxy) in your EC2 Security Group.

---

## 🧪 Testing & Verification

- **Submit Code**: Pick any problem (e.g. *Trapping Rain Water* or *Counting Bits*), write your solution in Monaco editor, and click **Submit**.
- **Test Socratic Hints**: Click the **AI Assistant** tab and request Tier 1, Tier 2, or Tier 3 hints to see non-spoiling guidance grounded in canonical vectors.
- **Test Failure Diagnostic**: Submit a faulty solution and click **RAG Failure Diagnostic** to inspect how the system references your exact code variables and historical community pitfalls.
- **Test Semantic Search**: Type natural language problem concepts in the problem catalog search bar.

---

## 📜 License & Acknowledgments

This project is licensed under the MIT License.
Built with ❤️ by **B Harsha Vardhan** using Google Gemini, FastAPI, and PostgreSQL `pgvector`.
