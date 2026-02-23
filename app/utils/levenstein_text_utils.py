"""
Утилиты для оценки сходства строк с использованием расстояния Левенштейна.
"""
from app.core.logger import get_logger


log = get_logger(__file__[:-3])

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Вычисляет расстояние Левенштейна между двумя строками.

    Args:
        s1: Первая строка.
        s2: Вторая строка.

    Returns:
        Расстояние Левенштейна (количество вставок, удалений, замен).
    """
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Создаём матрицу
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1      # вставка
            deletions = curr_row[j] + 1           # удаление
            substitutions = prev_row[j] + (c1 != c2)  # замена
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    Возвращает нормализованную меру сходства между двумя строками (0.0 - 1.0).

    1.0 — строки идентичны, 0.0 — полностью разные.

    Args:
        s1: Первая строка.
        s2: Вторая строка.

    Returns:
        Коэффициент сходства в диапазоне [0.0, 1.0].
    """
    try:
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0  # обе строки пустые

        distance = levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)
    except Exception as e:
        log.warn(e)
        return 0.0


# Тесты
if __name__ == "__main__":
    test_cases = [
        ("привет", "привет"),
        ("привет", "превет"),
        ("привет", "здравствуй"),
        ("", ""),
        ("", "текст"),
        ("стек", "свет"),
    ]

    print("🧪 Тесты расстояния Левенштейна и сходства:\n")
    for a, b in test_cases:
        dist = levenshtein_distance(a, b)
        sim = similarity_ratio(a, b)
        print(f"'{a}' ↔ '{b}'")
        print(f"  Расстояние: {dist}, Сходство: {sim:.3f}\n")