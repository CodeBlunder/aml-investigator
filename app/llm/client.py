
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class LLMClient:
    """
    Small wrapper around the configured LLM provider.

    The rest of the application should interact with this
    class instead of calling the provider SDK directly.
    """

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        self.model = os.getenv("LLM_MODEL", "").strip()

        if self.provider != "groq":
            raise RuntimeError(
                "LLM_PROVIDER must be set to 'groq'."
            )

        if not self.model:
            raise RuntimeError(
                "LLM_MODEL must be configured."
            )

        api_key = os.getenv("GROQ_API_KEY", "").strip()

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(api_key=api_key)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Generate a response from the configured LLM.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError(
                "The LLM returned an empty response."
            )

        return content.strip()
