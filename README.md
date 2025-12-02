# 🚀 Agentic Tutor — Adaptive Multi-Agent Teaching System for Linear Algebra  
### *Capstone Project — Generative & Agentic AI (DS246)*  

**Authors:** *Kasa Pavan (26738)*  
**Co-Authors:** *Boddu Amarnanth, Chandan Rai*

---

## 📌 Overview

**Agentic Tutor** is a fully autonomous, multi-agent educational system that teaches, evaluates, and guides students through university-level **Linear Algebra**.

The system integrates:

- **FastAPI backend**  
- **Streamlit frontend**  
- **LangGraph Orchestrator**  
- **Three LLM-based agents**  
  - 👨‍🏫 Tutor Agent  
  - 🧠 Evaluator Agent  
  - 🔍 Monitor Agent  
- **RAG (Retrieval-Augmented Generation)** using FAISS  
- **SymPy** for symbolic math grading  
- **Mastery tracking + personalized remediation**

This creates an adaptive loop:

```
Tutor → Student → Evaluator → Monitor → Tutor (next lesson)
```

---

## 🧩 System Architecture

### 🔹 1. **Tutor Agent**
- Generates structured lesson plans.
- Writes explanations using RAG-enriched embedded context.
- Produces micro-checks, practice tasks, and post-evaluation specifications.
- Adapts tone and style to student preferences.

### 🔹 2. **Evaluator Agent**
- Generates conceptual, procedural, application, geometric, and open-ended questions.
- Uses SymPy to verify symbolic answers.
- Grades using rubrics and produces misconceptions + feedback.
- Returns strictly-structured JSON.

### 🔹 3. **Monitor Agent**
- Interprets evaluator results + student profile.
- Decides:
  - advance  
  - practice  
  - remedial  
  - escalate  
- Generates remediation plan + teacher-facing note.

### 🔹 4. **RAG (FAISS Vector Store)**
- Embeds curriculum text using MiniLM-L6-v2.
- Supplies topic-specific context back to the agents.

### 🔹 5. **LangGraph Orchestrator**
Handles entire workflow:

```
start_session → tutor → evaluator → sympy_grader → monitor → update_state
```

All state remains inside a **session graph thread** for continuity.

---

## 📁 Folder Structure

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

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-org/agentic-tutor.git
cd agentic-tutor
```

---

## 🖥️ Backend Setup (FastAPI)

### 2️⃣ Create virtual environment

```bash
python -m venv agent
agent\Scripts\activate   # Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4️⃣ Run backend

```bash
uvicorn backend.app.main:app --reload --port 5005
```

Backend runs at:

```
http://127.0.0.1:5005
```

---

## 🎨 Frontend Setup (Streamlit)

### Install Streamlit:

```bash
pip install streamlit plotly reportlab
```

### Run the UI:

```bash
streamlit run frontend/app.py
```

Frontend runs at:

```
http://localhost:8501
```

---

## 🔄 Full Learning Loop

### 1. **Tutor Agent**
Creates lesson plan → Intro, Example, Micro-check, Practice, Post-Eval.

### 2. **Evaluator Agent**
Produces questions → Student submits → SymPy verifies → Scores & feedback returned.

### 3. **Monitor Agent**
Interprets student results → Generates:

- remediation steps  
- accelerate suggestion  
- allow_advance true/false  
- possible escalation  

### 4. **State Dashboard**
Frontend shows:

- Mastery radar  
- Misconceptions log  
- Topic graph  
- Evaluation results  
- Session timeline  

---

## 🔐 Environment Variables

Create `.env` inside `backend/app/`:

```
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

---

## 📊 Key Features

- ✔️ Autonomous multi-agent teaching system  
- ✔️ RAG-powered lesson personalization  
- ✔️ Strict JSON-safe LLM prompting  
- ✔️ Procedural math validation with SymPy  
- ✔️ Continuous mastery-based adaptation  
- ✔️ PDF export for student profile  
- ✔️ Visualization dashboards (radar, heatmap, timeline)  
- ✔️ Fully decoupled frontend ↔ backend architecture  

---

## 🧪 Testing

```bash
pytest backend/tests
```

---

## 🛣️ Future Enhancements

- Database persistence (PostgreSQL)
- Multi-course support (Calculus, Algebra II)
- Rich 3D geometric visualization (eigenvectors, transformations)
- Multi-student analytics dashboard
- Better long-term memory using structured embeddings

---

## 📄 License

MIT License — 2025  
*Team Members*

---

## 🙌 Acknowledgements  
Developed as part of **Generative & Agentic AI (DS246)**  
Indian Institute of Science