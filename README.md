---

# 🚀 **Agentic Tutor — Adaptive Multi-Agent Teaching System for Linear Algebra**

### *Capstone Project — Generative & Agentic AI (DS246)*

**Authors:** *Kasa Pavan & 26738*

**Co-Authors:** * Boddu Amarnanth & Chandan Rai*

---

## 📌 Overview

**Agentic Tutor** is a fully autonomous, multi-agent teaching system for university-level **Linear Algebra**, built using:

* **FastAPI** backend
* **Streamlit** frontend
* **LangGraph Orchestrator** for agent workflows
* **LLM Agents** (Tutor, Evaluator, Monitor)
* **RAG (Retrieval-Augmented Generation)** with FAISS
* **SymPy** for symbolic grading
* **Student modelling** with mastery tracking
* **Dynamic lesson planning**
* **Automated remediation and progression decisions**

The system simulates a complete tutoring workflow:

**Tutor → Student → Evaluator → Monitor → Tutor (loop)**
with each step guided by an **LLM agent prompt**, RAG context, and student performance data.

---

## 🧩 System Architecture

### 🔹 **1. Tutor Agent**

* Generates a structured lesson plan (intro → example → micro-check → practice → post-eval).
* Integrates **embedded curriculum context** from the RAG pipeline.
* Produces clean LaTeX-renderable content for the frontend.
* Adapts lesson style based on student preferences (visual, procedural, etc.).

### 🔹 **2. Evaluator Agent**

* Generates **high-quality evaluation questions** (conceptual, procedural, application, geometric, open-ended).
* Strict JSON output for machine parsing.
* Uses embedded_context + Tavily search implicitly.
* Grades student answers using:

  * **RAG context**
  * **SymPy symbolic correctness**
  * **Marking rubrics**

### 🔹 **3. Monitor Agent**

* Analyzes evaluator output + student profile.
* Makes decisions:

  * `allow_advance`
  * `remediation_plan`
  * `escalate`
* Uses mastery thresholds and risk profiles to adapt next steps.

### 🔹 **4. RAG Pipeline**

* Vector embeddings via **HuggingFace all-MiniLM-L6-v2**
* Curriculum stored as FAISS index
* Backend performs semantic retrieval per topic

### 🔹 **5. LangGraph Orchestrator**

Handles full autonomous workflow:

```
Start Session → Tutor Plan → Evaluator Questions → Grade → Monitor → Next Step
```

---

## 📁 Project Structure

```
agentic-tutor/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── tutor_agent.py
│   │   │   ├── evaluator_agent.py
│   │   │   ├── monitor_agent.py
│   │   │   └── agent_prompts/
│   │   │       ├── tutor_prompt.txt
│   │   │       ├── evaluator_prompt.txt
│   │   │       └── monitor_prompt.txt
│   │   ├── core/
│   │   │   ├── orchestrator.py
│   │   │   ├── event_bus.py
│   │   │   ├── rag/
│   │   │   │   ├── rag_service.py
│   │   │   │   └── vector_store.py
│   │   │   └── tools/
│   │   │       ├── rag.py
│   │   │       ├── sympy_tool.py
│   │   │       └── math_solver.py
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── app.py
│   ├── components/
│   ├── utils/
│   │   └── api_client.py
│   └── assets/
│
└── docs/
    ├── architecture.md
    ├── agent_designs.md
    ├── api_design.md
    ├── db_schema.md
    └── roadmap.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-org/agentic-tutor.git
cd agentic-tutor
```

---

## 🖥️ Backend Setup (FastAPI)

### 2️⃣ Create Python Environment

```bash
python -m venv agent
source agent/bin/activate    # Linux / macOS
agent\Scripts\activate       # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4️⃣ Run Backend Server

```bash
uvicorn backend.app.main:app --reload --port 5005
```

API will be available at:

```
http://127.0.0.1:5005
```

---

## 🎨 Frontend Setup (Streamlit)

### 1️⃣ Install frontend dependencies

(Same environment is used)

```bash
pip install streamlit plotly reportlab
```

### 2️⃣ Run Streamlit App

```bash
streamlit run frontend/app.py
```

Frontend opens at:

```
http://localhost:8501
```

---

## 🔄 Complete System Flow

### **1. Start Session**

The user selects:

* Student ID
* Topic

Frontend → `POST /api/session/start`
Orchestrator boots → RAG retrieves → Tutor agent generates lesson.

---

### **2. Student Answers Evaluation Questions**

Student submits answers → SymPy verifies → Evaluator grades → Monitor decides next action.

---

### **3. Dashboard Visualization**

Includes:

* Mastery radar chart
* Misconception log
* Topic graph
* Session timeline

All updated LIVE using API state.

---

## 📊 Key Features

### ✅ Multi-Agent Autonomous Teaching

Tutor, Evaluator, Monitor collaborate via LangGraph.

### ✅ Real-time Lesson Adaptation

Based on mastery, misconceptions, confidence, and history.

### ✅ Mathematical Rendering

LaTeX rendering inside Streamlit.

### ✅ Symbolic Grading via SymPy

Ensures mathematically correct evaluation.

### ✅ RAG Curriculum Integration

Semantic retrieval **per topic** → cleaner explanations & applied questions.

### ✅ Full Student Model

Mastery maps updated across:

* Conceptual
* Procedural
* Application
* Open-ended reasoning

### ✅ PDF Export of Student Profile

Auto-generated with ReportLab.

---

## 🧪 Testing

Unit tests located in:

```
backend/tests/
```

Run with:

```bash
pytest
```

---

## 🔐 Environment Variables

Add in `.env` (backend root):

```
GROQ_API_KEY=your_key
TAVILY_API_KEY=your_key
```

---

## 🚀 Future Enhancements

* Full database persistence (PostgreSQL)
* Multi-course expansion
* Interactive geometric visualizer for eigenvectors
* GPT-4o or local LLM drop-in support
* Student performance forecasting models

---

## 🤝 Contributing

Pull requests are welcome!
Before submitting:

* Run tests
* Format with `black`
* Follow JSON schema constraints

---

## 📄 License

MIT License © 2025 – Your Team

---

## 🏁 Final Notes

This project demonstrates:

* Agentic AI system design
* Multi-agent orchestration
* RAG-powered pedagogy
* Automated grading
* Adaptive tutoring loops

It is designed for academic demonstration and future scalability.