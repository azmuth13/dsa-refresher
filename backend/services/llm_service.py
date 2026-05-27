import asyncio
import logging

from fastapi import HTTPException
import httpx

from config import get_settings

logger = logging.getLogger(__name__)


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
        logger.error("Unsupported LLM provider", extra={"provider": self.settings.LLM_PROVIDER})
        raise HTTPException(status_code=500, detail="Unsupported LLM provider")

    async def _generate_groq(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.GROQ_API_KEY:
            logger.error("Groq API key is not configured")
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

        logger.debug("Groq LLM request starting", extra={"provider": "groq", "model": self.settings.GROQ_MODEL})

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = None
                for attempt in range(3):
                    logger.debug(
                        "Groq API attempt",
                        extra={"provider": "groq", "model": self.settings.GROQ_MODEL, "attempt": attempt + 1},
                    )
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code not in {429, 500, 502, 503, 504}:
                        break
                    logger.warning(
                        "Groq API transient error, retrying",
                        extra={
                            "provider": "groq",
                            "model": self.settings.GROQ_MODEL,
                            "attempt": attempt + 1,
                            "status_code": response.status_code,
                        },
                    )
                    await asyncio.sleep(1.5 * (attempt + 1))

                if response is None:
                    logger.error(
                        "Groq request failed before receiving a response",
                        extra={"provider": "groq", "model": self.settings.GROQ_MODEL},
                    )
                    raise HTTPException(status_code=502, detail="Groq request failed before receiving a response")

                if response.status_code >= 400:
                    logger.error(
                        "Groq API returned error status after retries",
                        extra={
                            "provider": "groq",
                            "model": self.settings.GROQ_MODEL,
                            "status_code": response.status_code,
                            "response_body": response.text[:500],
                        },
                    )

                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Groq API HTTP error",
                extra={
                    "provider": "groq",
                    "model": self.settings.GROQ_MODEL,
                    "status_code": exc.response.status_code,
                    "response_body": exc.response.text[:500],
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Groq API error: {exc.response.text[:500]}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.error(
                "Groq request network failure",
                extra={"provider": "groq", "model": self.settings.GROQ_MODEL},
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
            logger.debug(
                "Groq LLM response received",
                extra={"provider": "groq", "model": self.settings.GROQ_MODEL, "response_len": len(content)},
            )
            return content
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(
                "Groq response missing expected content field",
                extra={"provider": "groq", "model": self.settings.GROQ_MODEL, "response_keys": list(data.keys())},
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail="Groq response did not contain text") from exc

    async def _generate_gemini(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.GEMINI_API_KEY:
            logger.error("Gemini API key is not configured")
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

        logger.debug("Gemini LLM request starting", extra={"provider": "gemini", "model": self.settings.GEMINI_MODEL})

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = None
                for attempt in range(3):
                    logger.debug(
                        "Gemini API attempt",
                        extra={"provider": "gemini", "model": self.settings.GEMINI_MODEL, "attempt": attempt + 1},
                    )
                    response = await client.post(url, json=payload)
                    if response.status_code not in {429, 500, 502, 503, 504}:
                        break
                    logger.warning(
                        "Gemini API transient error, retrying",
                        extra={
                            "provider": "gemini",
                            "model": self.settings.GEMINI_MODEL,
                            "attempt": attempt + 1,
                            "status_code": response.status_code,
                        },
                    )
                    await asyncio.sleep(1.5 * (attempt + 1))

                if response is None:
                    logger.error(
                        "Gemini request failed before receiving a response",
                        extra={"provider": "gemini", "model": self.settings.GEMINI_MODEL},
                    )
                    raise HTTPException(status_code=502, detail="Gemini request failed before receiving a response")

                if response.status_code >= 400:
                    logger.error(
                        "Gemini API returned error status after retries",
                        extra={
                            "provider": "gemini",
                            "model": self.settings.GEMINI_MODEL,
                            "status_code": response.status_code,
                            "response_body": response.text[:500],
                        },
                    )

                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Gemini API HTTP error",
                extra={
                    "provider": "gemini",
                    "model": self.settings.GEMINI_MODEL,
                    "status_code": exc.response.status_code,
                    "response_body": exc.response.text[:500],
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Gemini API error: {exc.response.text[:500]}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.error(
                "Gemini request network failure",
                extra={"provider": "gemini", "model": self.settings.GEMINI_MODEL},
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc}") from exc

        data = response.json()
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug(
                "Gemini LLM response received",
                extra={"provider": "gemini", "model": self.settings.GEMINI_MODEL, "response_len": len(content)},
            )
            return content
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(
                "Gemini response missing expected content field",
                extra={"provider": "gemini", "model": self.settings.GEMINI_MODEL, "response_keys": list(data.keys())},
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail="Gemini response did not contain text") from exc
