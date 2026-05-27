import json
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from services.llm_service import LLMService
from services.scraper_service import fetch_cppalgorithms_context
from services.topic_service import get_random_topic

logger = logging.getLogger(__name__)

router = APIRouter()


class RandomTopicResponse(BaseModel):
    topic_name: str
    category: str
    difficulty: str
    core_concept: str
    time_complexity: dict
    space_complexity: str
    key_insight: str
    common_pitfalls: list[str]
    template_code: str
    example_problem: dict
    practice_links: list[dict]
    related_topics: list[str]
    source_context_used: bool = Field(default=False)
    model_used: str


SYSTEM_PROMPT = """You are a concise DSA teaching assistant. Generate a 'daily refresher bite' for a competitive programmer.
Format your response as JSON with these exact fields:
{
  "topic_name": string,
  "category": string,
  "difficulty": string,
  "core_concept": string,
  "time_complexity": { "best": string, "average": string, "worst": string },
  "space_complexity": string,
  "key_insight": string,
  "common_pitfalls": [string],
  "template_code": string,
  "example_problem": { "title": string, "description": string, "approach": string },
  "practice_links": [{ "platform": string, "url": string, "title": string, "difficulty": string }],
  "related_topics": [string]
}
Be specific and concrete. Avoid generic advice. Return only valid JSON."""


def _extract_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def _generate_and_validate(
    llm: LLMService,
    system_prompt: str,
    user_prompt: str,
    source_context_used: bool,
) -> RandomTopicResponse:
    raw = await llm.generate(system_prompt, user_prompt)
    payload = _extract_json(raw)
    payload["source_context_used"] = source_context_used
    payload["model_used"] = llm.model_used
    return RandomTopicResponse.model_validate(payload)


@router.get("/random-topic", response_model=RandomTopicResponse)
async def random_topic():
    topic = get_random_topic()
    logger.info("Generating random topic bite", extra={"topic": topic.get("name"), "category": topic.get("category")})
    context = await fetch_cppalgorithms_context(topic["name"])
    source_context_used = bool(context)

    user_prompt = json.dumps(
        {
            "topic": topic,
            "cp_algorithms_context": context or "No source context available. Use your own DSA knowledge.",
            "instruction": "Generate one concise daily refresher. Keep template_code between 10 and 30 Python lines.",
        },
        indent=2,
    )

    llm = LLMService()
    try:
        result = await _generate_and_validate(llm, SYSTEM_PROMPT, user_prompt, source_context_used)
        logger.info(
            "Random topic bite generated successfully",
            extra={"topic": topic.get("name"), "model": llm.model_used, "context_used": source_context_used},
        )
        return result
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "Random topic bite first attempt invalid JSON, retrying",
            extra={"topic": topic.get("name"), "error": str(exc)},
        )
        strict_prompt = (
            SYSTEM_PROMPT
            + "\nYour previous response failed JSON validation. Return only one complete JSON object with all required fields and no markdown. Escape all newlines inside template_code as \\n and do not truncate strings."
        )
        try:
            result = await _generate_and_validate(llm, strict_prompt, user_prompt, source_context_used)
            logger.info(
                "Random topic bite generated on retry",
                extra={"topic": topic.get("name"), "model": llm.model_used},
            )
            return result
        except (json.JSONDecodeError, ValidationError) as exc2:
            logger.error(
                "Random topic bite generation failed after retry",
                extra={"topic": topic.get("name"), "error": str(exc2)},
                exc_info=True,
            )
            raise HTTPException(status_code=502, detail=f"LLM returned invalid refresher JSON: {exc2}") from exc2
