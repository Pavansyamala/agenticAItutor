# backend/app/agents/evaluator_agent.py
import json
import re
from uuid import uuid4
from typing import Dict, Any, List, Optional
from pathlib import Path

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.llm_client import LLMClient
from backend.app.core.tools.tavily_search import tavily_search
from backend.app.core.tools.sympy_tool import SymPyVerifier  # ← Your SymPy tool
from backend.app.agents.agent_prompts.evaluator_prompt import evaluator_prompt
from dotenv import load_dotenv

load_dotenv()


def _safe_merge_context(rag_context: str, tavily_snippets: List[Dict[str, Any]]) -> str:
    parts = []
    if rag_context:
        parts.append(rag_context.strip())

    for s in tavily_snippets:
        snip = s.get("snippet", "")
        snip = re.sub(r"https?://\S+", "", snip)
        snip = re.sub(r"\s+", " ", snip).strip()
        if snip:
            parts.append(snip)
    return "\n\n".join(parts)


class EvaluatorAgent(BaseAgent):
    def __init__(self, name: str = "evaluator", model: str = "llama-3.1-8b-instant"):
        super().__init__(name)
        self.llm = LLMClient(model=model)
        self.sympy = SymPyVerifier()  # ← Instance for symbolic checks

        self.template = evaluator_prompt

    async def _call_llm_for_generation(self, user_payload: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = json.dumps(user_payload, ensure_ascii=False)
        raw = await self.llm.chat(system_prompt=self.template, user_prompt=user_prompt)
        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    return {"error": "llm_parse_error", "raw": raw}
            return {"error": "llm_parse_error", "raw": raw}

    async def generate_questions(self, topic: str, q_types: List[str], counts: Dict[str, int], rag_context: str = "") -> Dict[str, Any]:
        need_web = any(qt in ("application", "open-ended") for qt in q_types)
        tavily_snips = []

        if need_web and not rag_context:
            try:
                tavily_snips = await tavily_search(f"{topic} application examples linear algebra", top_k=3)
            except Exception:
                pass

        merged_context = _safe_merge_context(rag_context, tavily_snips)

        payload = {
            "task": "generate_questions",
            "topic": topic,
            "q_types": q_types,
            "counts": counts,
            "embedded_context": merged_context,
            "require_symbolic_solutions": True  # ← Critical for SymPy
        }
        return await self._call_llm_for_generation(payload)

    async def grade_answers(self, eval_record: Dict[str, Any], student_answers: List[Dict[str, Any]]) -> Dict[str, Any]:

        questions = eval_record.get("questions", [])
        student_map = {a["qid"]: a["answer"] for a in student_answers}

        grading_result = {
            "grading": {},
            "overall_score": 0.0,
            "misconceptions": [],
            "symbolic_checks": {}
        }

        total_obtained = 0.0
        total_possible = 0.0

        for q in questions:
            qid = q["qid"]
            qtype = q.get("type", "conceptual")
            expected = q.get("expected_solution", "")
            rubric = q.get("rubric", {"full_marks": 10})
            student_answer = student_map.get(qid, "").strip()

            marks = 0.0
            feedback = ""
            sympy_used = False
            sympy_correct = False

            # ===============================
            # 1. SYMBOLIC GRADING (If relevant)
            # ===============================
            sympy_should_run = (
                qtype in ("procedural", "application") 
                and expected 
                and "?" not in expected
                and "??" not in expected
            )

            if sympy_should_run:
                try:
                    sympy_used = True

                    # Detect if it's a matrix or scalar expression
                    is_matrix = ("[[" in expected) or ("matrix" in expected.lower())

                    if is_matrix:
                        result = self.sympy.verify_matrix(student_answer, expected)
                    else:
                        result = self.sympy.verify_equality(student_answer, expected)

                    sympy_correct = result.get("correct", False)
                    parse_success = result.get("parse_success", True)
                    sympy_feedback = result.get("feedback", "")
                    feedback += f" [SymPy] {sympy_feedback}"

                    # Only award marks if SymPy parsing succeeded
                    if parse_success:
                        if sympy_correct:
                            marks = rubric.get("full_marks", 10)
                        else:
                            # Partial credit for correct format but wrong solution
                            marks = 0 
                    else:
                        marks = 0  # force LLM fallback

                except Exception as e:
                    # SymPy crashed OR input is not parsible
                    sympy_used = True
                    sympy_correct = False
                    marks = 0  # force LLM grading
                    feedback += f" [SymPy Error: fallback to LLM]"

            # ===============================
            # 2. LLM FALLBACK GRADING
            #    Triggered only when marks == 0
            # ===============================
            if marks == 0:
                payload = {
                    "task": "grade_single_question",
                    "question": q,
                    "student_answer": student_answer
                }
                llm_grade = await self._call_llm_for_generation(payload)

                marks = llm_grade.get("score", 0)
                llm_feedback = llm_grade.get("feedback", "No feedback provided.")

                if not sympy_used:
                    llm_feedback = "[LLM Graded] " + llm_feedback

                feedback = llm_feedback

            # ===============================
            # 3. Store scores & bookkeeping
            # ===============================
            max_marks = rubric.get("full_marks", 10)
            total_obtained += marks
            total_possible += max_marks

            grading_result["grading"][qid] = {
                "obtained": round(marks, 2),
                "possible": max_marks,
                "feedback": feedback.strip(),
                "sympy_used": sympy_used,
                "sympy_correct": sympy_correct
            }

            grading_result["symbolic_checks"][qid] = {
                "used": sympy_used,
                "correct": sympy_correct,
                "expected": expected,
                "student": student_answer
            }

            # Misconceptions
            if marks < 0.6 * max_marks:
                concept = q.get("concept", qtype)
                grading_result["misconceptions"].append(f"Weakness in {concept}")

        # Final Score
        grading_result["overall_score"] = round(
            total_obtained / total_possible, 3
        ) if total_possible > 0 else 0.0

        return grading_result


    async def run(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        gp = context.get("goal_params") or {}
        if goal == "generate_questions":
            return await self.generate_questions(
                topic=gp.get("topic", "linear algebra"),
                q_types=gp.get("q_types", ["conceptual", "procedural"]),
                counts=gp.get("counts", {"conceptual": 2, "procedural": 2}),
                rag_context=gp.get("embedded_context", gp.get("rag_context", ""))
            )
        elif goal == "grade_answers":
            return await self.grade_answers(
                eval_record=gp.get("eval_record", {}),
                student_answers=gp.get("student_answers", [])
            )
        else:
            raise ValueError(f"EvaluatorAgent cannot handle goal {goal}")