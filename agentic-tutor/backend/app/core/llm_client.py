# backend/app/core/llm_client.py
import os
from typing import Any
from openai import OpenAI, AsyncOpenAI
from openai import APIError, RateLimitError, AuthenticationError
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """
    Wrapper around Groq (or any OpenAI-compatible provider).
    Forces STRICT JSON output using the official `response_format={"type": "json_object"}`.
    """

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY (or OPENAI_API_KEY) environment variable is required.")

        # Sync client
        self.sync_client: OpenAI = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        # Async client
        self.async_client: AsyncOpenAI = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a system + user message pair to Groq and return STRICT JSON.

        Uses response_format={"type": "json_object"} which forces valid JSON and avoids:
        - escaped JSON strings
        - partial JSON
        - non-parseable output
        """

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],

                # 🔥 CRITICAL: FORCE VALID JSON
                response_format={"type": "json_object"},

                # Should NOT be high for JSON data generation
                temperature=0.0,
                max_tokens=2048,
            )

            # Always safe because JSON mode ensures valid JSON object
            return response.choices[0].message.content.strip()

        except AuthenticationError:
            return "[LLM Error] Invalid API key – check GROQ_API_KEY."

        except RateLimitError:
            return "[LLM Error] Rate limit exceeded. Try again later."

        except APIError as e:
            return f"[LLM Error] API error: {e}"

        except Exception as e:
            return f"[LLM Error] Unexpected error: {str(e)}"