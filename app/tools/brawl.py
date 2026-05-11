import random

from langchain_core.tools import tool

from app.tools.brawl_data.brawl_templates import brawl_templates_shuffle
from app.tools.brawl_data.brawl_words import agressive_words_shuffle


class BrawlerSova:
    def __init__(self, shuffle_bag_words):
        self.shuffle_bag_words = shuffle_bag_words  # Твой класс со списком слов из PDF

    def generate_insult(self):
        # Шаблоны «интеллектуальной агрессии»

        template = brawl_templates_shuffle.pick()
        # Вытаскиваем слова из твоего ShuffleBag
        return template.format(
            word1=self.shuffle_bag_words.pick(),
            word2=self.shuffle_bag_words.pick(),
            word3=self.shuffle_bag_words.pick()
        )

brawler = BrawlerSova(agressive_words_shuffle)

def get_mat_count(expression_score: dict) -> int:
    try:
        mat_count = int(expression_score.get("counts").get("mat"))
        return mat_count
    except Exception as exeption:
        return 0

# Создаем инструмент для агента
@tool(return_direct=True)
def trigger_vicious_response(reason: str) -> str:
    """Генерирует жесткий и саркастичный отпор хаму."""
    return brawler.generate_insult()
