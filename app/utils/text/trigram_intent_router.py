import re
from typing import Dict, List, Set, Tuple


class TrigramIntentRouter:
    """
    Быстрый триграммный роутер на чистом Python.
    Устойчив к ошибкам распознавания Vosk и перестановке слов.
    """

    def __init__(self, intents: Dict[str, List[str]], threshold: float = 0.40):
        self.threshold = threshold
        self._re_clean = re.compile(r"[^а-яёa-z0-9\s]")
        # Предвычисляем триграммы для всех эталонных фраз при старте:
        # формат: [(intent_name, word_count, set_of_trigrams), ...]
        self._index: List[Tuple[str, int, Set[str]]] = []

        for intent, phrases in intents.items():
            for phrase in phrases:
                norm = self._normalize(phrase)
                words = norm.split()
                if words:
                    self._index.append((intent, len(words), self._to_trigrams(norm)))

    def _normalize(self, text: str) -> str:
        text = text.lower().replace("ё", "е")
        text = self._re_clean.sub(" ", text)
        return " ".join(text.split())

    @staticmethod
    def _to_trigrams(text: str) -> Set[str]:
        padded = f" {text} "
        if len(padded) < 3:
            return {padded}
        return {padded[i : i + 3] for i in range(len(padded) - 2)}

    @staticmethod
    def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        if intersection == 0:
            return 0.0
        return intersection / (len(set_a) + len(set_b) - intersection)

    def predict(self, text: str, default: str = "crazy") -> Tuple[str, float]:
        """Возвращает (название_режима, уверенность_от_0_до_1)."""
        norm = self._normalize(text)
        words = norm.split()
        if not words:
            return default, 0.0

        best_intent = default
        best_score = 0.0
        total_words = len(words)

        for intent, target_len, target_trigrams in self._index:
            # Если фраза пользователя короче эталона — сравниваем целиком
            if total_words <= target_len:
                score = self._jaccard(self._to_trigrams(norm), target_trigrams)
                if score > best_score:
                    best_score = score
                    best_intent = intent
            else:
                # Иначе прогоняем скользящим окном по словам пользователя
                for i in range(total_words - target_len + 1):
                    window_phrase = " ".join(words[i : i + target_len])
                    score = self._jaccard(
                        self._to_trigrams(window_phrase), target_trigrams
                    )
                    if score > best_score:
                        best_score = score
                        best_intent = intent

        if best_score >= self.threshold:
            return best_intent, round(best_score, 3)
        return default, round(best_score, 3)
