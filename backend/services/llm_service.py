import asyncio

from fastapi import HTTPException
import httpx

from config import get_settings


class LLMService:
    def __init__(self):
        self.settings = get_settings()

    @property
    def model_used(self) -> str:
        if self.settings.LLM_PROVIDER == "groq":
            return f"groq:{self.settings.GROQ_MODEL}"
        if self.settings.LLM_PROVIDER == "gemini":
            return f"gemini:{self.settings.GEMINI_MODEL}"
        return self.settings.LLM_PROVIDER

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.settings.LLM_PROVIDER == "groq":
            return await self._generate_groq(system_prompt, user_prompt)
        if self.settings.LLM_PROVIDER == "gemini":
            return await self._generate_gemini(system_prompt, user_prompt)
        raise HTTPException(status_code=500, detail="Unsupported LLM provider")

    async def _generate_groq(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")

        payload = {
            "model": self.settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.35,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = None
                for attempt in range(3):
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code not in {429, 500, 502, 503, 504}:
                        break
                    await asyncio.sleep(1.5 * (attempt + 1))
                if response is None:
                    raise HTTPException(status_code=502, detail="Groq request failed before receiving a response")
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Groq API error: {exc.response.text[:500]}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="Groq response did not contain text") from exc

    async def _generate_gemini(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.GEMINI_MODEL}:generateContent?key={self.settings.GEMINI_API_KEY}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.35,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = None
                for attempt in range(3):
                    response = await client.post(url, json=payload)
                    if response.status_code not in {429, 500, 502, 503, 504}:
                        break
                    await asyncio.sleep(1.5 * (attempt + 1))
                if response is None:
                    raise HTTPException(status_code=502, detail="Gemini request failed before receiving a response")
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Gemini API error: {exc.response.text[:500]}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc}") from exc

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="Gemini response did not contain text") from exc
