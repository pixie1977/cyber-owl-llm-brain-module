


raw_data = """
СЮДА ПОМЕСТИТЬ ПРОСТЫНЮ ТЕКСТА, ИЗ КОТОРОГО БУДЕТЕ ГЕНЕРИровать фразы
"""

import random
import re
from collections import defaultdict


def build_markov_chain_2(text):
    # Улучшенная очистка: оставляем буквы, цифры и знаки препинания
    words = re.findall(r'[а-яёА-ЯЁa-zA-Z0-9!?,.-]+', text.lower())

    if len(words) < 3:
        return {}

    # Словарь: (слово1, слово2) -> [список возможных слово3]
    chain = defaultdict(list)
    for i in range(len(words) - 2):
        key = (words[i], words[i + 1])
        chain[key].append(words[i + 2])
    return chain


def generate_sentence_2(chain, max_length=20):
    if not chain:
        return "Недостаточно данных для генерации."

    # Выбираем случайную пару слов для начала
    current_key = random.choice(list(chain.keys()))
    sentence = [current_key[0].capitalize(), current_key[1]]

    for _ in range(max_length - 2):
        next_words = chain.get(current_key)
        if not next_words:
            break

        next_word = random.choice(next_words)
        sentence.append(next_word)

        # Сдвигаем "окно" на одно слово вперед
        current_key = (current_key[1], next_word)

        if next_word.endswith(('.', '!', '?')):
            break

    return " ".join(sentence)


# Пример использования
model = build_markov_chain_2(raw_data)

for _ in range(5):
    print(generate_sentence_2(model, 15))

