# frontend/utils/api_client.py
import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:5010"  # Make sure backend runs on this port

class APIClient:
    @staticmethod
    def start_session(student_id: str, topic: str):
        try:
            resp = requests.post(f"{BASE_URL}/api/session/start", json={"student_id": student_id, "topic": topic}, timeout=300)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            st.error(f"Start session failed: {e}")
            return {}

    @staticmethod
    def submit_answers(thread_id: str, answers: list):
        import time
        try:
            resp = requests.post(
                f"{BASE_URL}/api/eval/submit",
                params={"thread_id": thread_id},
                json=answers,
                timeout=180
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            st.error(f"Submit failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_session_state(thread_id: str):
        try:
            resp = requests.get(f"{BASE_URL}/api/session/{thread_id}", timeout=30)
            resp.raise_for_status()
            return resp.json()
        except:
            return {}

    @staticmethod
    def get_profile(student_id: str):
        try:
            resp = requests.get(f"{BASE_URL}/api/student/{student_id}/profile", timeout=30)
            resp.raise_for_status()
            return resp.json()
        except:
            return {}