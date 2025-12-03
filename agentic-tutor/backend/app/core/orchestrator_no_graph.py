# # backend/app/core/orchestrator_no_graph.py

# from backend.app.agents.tutor_agent import TutorAgent
# from backend.app.agents.evaluator_agent import EvaluatorAgent
# from backend.app.agents.monitor_agent import MonitorAgent
# from backend.app.core.rag.rag_service import RAGService

# from backend.app.database.session import get_session
# from backend.app.database.models import Event

# import uuid
# import datetime


# def log_event(student_id, event_type, payload, thread_id):
#     with get_session() as session:
#         e = Event(
#             event_id=uuid.uuid4().hex,
#             student_id=student_id,
#             event_type=event_type,
#             payload={**payload, "thread_id": thread_id},
#             created_at=datetime.datetime.utcnow(),
#         )
#         session.add(e)
#         session.commit()


# class Orchestrator:
#     """
#     Clean, stable orchestrator — NO LangGraph.
#     Flow controlled ONLY by frontend buttons.
    
#     Step flow:
#         1) start_session → tutor_node
#         2) start_quiz → generate_questions_node
#         3) submit_answers → grade_answers → monitor → next_action
#     """

#     def __init__(self):
#         self.tutor = TutorAgent()
#         self.evaluator = EvaluatorAgent()
#         self.monitor = MonitorAgent()

#         # Load vectorstore once
#         RAGService.initialize()

#         # Runtime session storage
#         self.sessions = {}

#     # ---------------------------------------------------------------
#     # SESSION START — runs ONLY tutor lesson
#     # ---------------------------------------------------------------
#     async def start_session(self, student_id: str, topic: str):
#         thread_id = f"{student_id}_{uuid.uuid4().hex}"

#         # build RAG context
#         rag_context = RAGService.get_context(
#             f"explain {topic} with examples and misconceptions", 
#             use_tavily=True
#         )

#         # tutor agent
#         tutor_result = await self.tutor.run(
#             goal="teach_topic",
#             context={
#                 "goal_params": {
#                     "topic": topic,
#                     "student_id": student_id,
#                     "target_mastery": 0.8,
#                     "embedded_context": rag_context,
#                 }
#             }
#         )

#         lesson_plan = tutor_result.get("plan", [])

#         # save in memory
#         self.sessions[thread_id] = {
#             "student_id": student_id,
#             "topic": topic,
#             "lesson_plan": lesson_plan,
#             "questions": None,
#             "grading_result": None,
#             "monitor_decision": None,
#             "rag_context": rag_context,
#             "next_action": "evaluate",    # next step is quiz
#         }

#         log_event(student_id, "lesson_delivered",
#                   {"topic": topic, "steps": len(lesson_plan)}, thread_id)

#         return {
#             "thread_id": thread_id,
#             "lesson_plan": lesson_plan,
#             "next_action": "evaluate",
#         }

#     # ---------------------------------------------------------------
#     # START QUIZ — ONLY generates questions
#     # ---------------------------------------------------------------
#     async def start_quiz(self, thread_id: str):
#         state = self.sessions.get(thread_id)
#         if not state:
#             return {"error": "invalid thread_id"}

#         topic = state["topic"]

#         rag_context = RAGService.get_context(topic, use_tavily=True)

#         eval_result = await self.evaluator.run(
#             goal="generate_questions",
#             context={"goal_params": {
#                 "topic": topic,
#                 "q_types": ["conceptual", "procedural", "application", "open-ended"],
#                 "counts": {"conceptual": 2, "procedural": 2, "application": 1, "open-ended": 1},
#                 "embedded_context": rag_context
#             }}
#         )

#         questions = eval_result.get("questions", [])

#         # Save to session
#         state["questions"] = questions
#         state["next_action"] = "grade"

#         log_event(state["student_id"], "questions_generated",
#                   {"count": len(questions)}, thread_id)

#         return {
#             "thread_id": thread_id,
#             "questions": questions,
#             "next_action": "grade"
#         }

#     # ---------------------------------------------------------------
#     # SUBMIT ANSWERS — performs grading + monitor decision
#     # ---------------------------------------------------------------
#     async def submit_answers(self, thread_id: str, answers):
#         state = self.sessions.get(thread_id)
#         if not state:
#             return {"error": "invalid thread_id"}

#         # grade answers
#         grade_result = await self.evaluator.run(
#             goal="grade_answers",
#             context={"goal_params": {
#                 "eval_record": {"questions": state["questions"]},
#                 "student_answers": answers,
#             }}
#         )

#         state["grading_result"] = grade_result

#         # build eval summary for monitor
#         eval_summary = {
#             "overall_score": float(grade_result.get("overall_score", 0.0)),
#             "per_question": grade_result.get("grading", {}),
#             "misconceptions": grade_result.get("misconceptions", []),
#         }

#         # monitor agent
#         monitor_result = await self.monitor.run(
#             goal="decide",
#             context={"goal_params": {
#                 "student_id": state["student_id"],
#                 "eval_summary": eval_summary,
#                 "policy": {
#                     "mastery_threshold": 0.8,
#                     "consec_required": 2,
#                     "escalate_threshold": 0.4
#                 }
#             }}
#         )

#         state["monitor_decision"] = monitor_result

#         # extract next action
#         decision = monitor_result.get("remediation_plan", {})
#         allow_advance = monitor_result.get("allow_advance", False)

#         if decision:
#             next_action = {
#                 "remedial": "teach",
#                 "practice": "evaluate",
#                 "review": "teach",
#                 "accelerate": "advance"
#             }.get(decision.get("action", "advance"), "advance")
#         else:
#             next_action = "advance" if allow_advance else "teach"

#         state["next_action"] = next_action

#         log_event(state["student_id"], "monitor_decision",
#                   {"decision": monitor_result}, thread_id)

#         return {
#             "grading": grade_result,
#             "monitor_decision": monitor_result,
#             "next_action": next_action
#         }

#     # ---------------------------------------------------------------
#     # EXPOSE SESSION STATE
#     # ---------------------------------------------------------------
#     def get_state(self, thread_id: str):
#         return self.sessions.get(thread_id, {})