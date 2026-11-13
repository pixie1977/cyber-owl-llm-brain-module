from app.core.logger import get_logger
from app.utils.text.trigram_intent_router import TrigramIntentRouter

INTENT_EXAMPLES = {
    "consultant": [
        "консультант",
        "справка",
        "поищи в базе",
        "найди в базе",
        "что такое",
        "кто такой",
        "расскажи про",
        "объясни что значит",
        "поясни за",
    ],
    "tools": [
        "который час",
        "сколько времени",
        "посчитай",
        "сколько будет",
        "вычисли",
        "синус",
        "косинус",
        "логарифм",
        "корень",
        "спасбросок",
        "брось кубик",
        "кинь кубик",
        "кинь кости",
        "сделай спасбросок",
        "расскажи шутку",
        "анекдот",
        "скажи тост",
        "поздравь",
    ],
}

log = get_logger(__name__)

intent_router = TrigramIntentRouter(INTENT_EXAMPLES, threshold=0.40)


def classify_intent(text: str) -> str:
    mode, score = intent_router.predict(text, default="crazy")
    log.debug("Роутер: режим=%s (score=%.3f)", mode, score)
    return mode
