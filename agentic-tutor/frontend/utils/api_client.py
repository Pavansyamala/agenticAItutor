# frontend/utils/api_client.py
import requests
import streamlit as st

BASE_URL = "http://127.0.0.1:5005"  # Make sure this matches exactly

class APIClient:
    @staticmethod
    def start_session(student_id: str, topic: str):
        try:
            resp = requests.post(
                f"{BASE_URL}/api/session/start",
                json={"student_id": student_id, "topic": topic},
                timeout=200
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Is uvicorn running on port 5000?")
            return {"error": "connection_failed"}
        except Exception as e:
            st.error(f"Backend error: {e}")
            return {"error": str(e)}

    @staticmethod
    def submit_answers(thread_id: str, answers: list):
        try:
            print(">>> SENDING REQUEST TO BACKEND")
            print("URL:", f"{BASE_URL}/api/eval/submit?thread_id={thread_id}")
            print("BODY:", answers)

            resp = requests.post(
                f"{BASE_URL}/api/eval/submit",
                params={"thread_id": thread_id},
                json=answers,
                timeout=30
            )

            print(">>> RESPONSE STATUS:", resp.status_code)
            print(">>> RESPONSE TEXT:", resp.text)

            resp.raise_for_status()
            return resp.json()

        except Exception as e:
            print(">>> CLIENT EXCEPTION:", e)
            return {"error": "submit failed"}


    @staticmethod
    def get_session_state(thread_id: str):
        try:
            resp = requests.get(f"{BASE_URL}/api/session/{thread_id}")
            return resp.json()
        except:
            return {"error": "state fetch failed"}

    @staticmethod
    def get_profile(student_id: str):
        try:
            resp = requests.get(f"{BASE_URL}/api/student/{student_id}/profile")
            resp.raise_for_status()
            return resp.json()
        except:
            return {"error": "failed to fetch profile"}
