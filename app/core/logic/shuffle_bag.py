from __future__ import annotations

import random
from typing import List

# ✅ Инициализация случайного генератора при импорте
random.seed()


class ShuffleBag:
    """
    Итератор-«шляпа»: каждый элемент списка выпадает ровно один раз за цикл.
    Как только шляпа опустела, она автоматически перетасовывается заново.

    Как это работает
    1. Создаём объект `ShuffleBag`, передав ему список элементов.
    2. Внутри класса копия списка перемешивается (`random.shuffle`).
    3. Метод `pick()` выдаёт элемент, удаляя его из «шляпы».
    4. Когда шляпа опустевает, она автоматически перетасовывается, и начинается новый цикл.

    Таким образом каждый элемент гарантированно будет встречаться ровно один раз за «раунд»,
    а порядок выдачи в каждом раунде остаётся случайным.
    """

    def __init__(self, items: List[str]) -> None:
        if not items:
            raise ValueError("ShuffleBag не может быть инициализирован пустым списком")
        self.reference_items = items.copy()
        self._items = self.reference_items.copy()
        self._reset()

    def _reset(self) -> None:
        self._items = self.reference_items.copy()
        random.shuffle(self._items)
        # Очищаем счетчик использованных элементов (если нужно отслеживать — можно оставить)
        self._used: List[str] = []

    def pick(self) -> str:
        if not self._items:
            self._reset()
        return self._items.pop()


# Пример использования ---------------------------------------------------------
if __name__ == "__main__":
    colors = ["red", "green", "blue", "yellow"]

    bag = ShuffleBag(colors)  # создаём шляпу

    # Выбор 12 элементов; после 4-х элементов шляпа перетасуется автоматически
    for i in range(12):
        print(f"{i + 1:2d}: {bag.pick()}")