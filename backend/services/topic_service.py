import json
import random
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

TOPICS_PATH = Path(__file__).resolve().parent.parent / "data" / "topics.json"

DIFFICULTY_WEIGHTS = {
    "beginner": 5,
    "intermediate": 3,
    "advanced": 1,
}


@lru_cache
def load_topics() -> list[dict]:
    with TOPICS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_random_topic() -> dict:
    topics = load_topics()
    weights = [DIFFICULTY_WEIGHTS.get(topic.get("difficulty", "intermediate"), 2) for topic in topics]
    return random.choices(topics, weights=weights, k=1)[0]


def get_topic_by_id(topic_id: str) -> dict:
    for topic in load_topics():
        if topic["id"] == topic_id:
            return topic
    raise HTTPException(status_code=404, detail=f"Topic not found: {topic_id}")
