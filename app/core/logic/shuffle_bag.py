from __future__ import annotations

import random
from typing import List, Iterator, TypeVar

from networkx.classes import is_empty

T = TypeVar('T')

class ShuffleBag():
    """
    Итератор-«шляпа»: каждый элемент списка выпадает ровно один раз за цикл.
    Как только шляпа опустела, она автоматически перетасовывается заново.

    Как это работает
    1. Создаём объект `ShuffleBag`, передав ему список элементов.
    2. Внутри класса копия списка перемешивается (`_rng.shuffle`).
    3. Метод `pick()` (или `next(bag)`) выдаёт элемент, удаляя его из «шляпы».
    4. Когда шляпа опустевает, она автоматически перетасовывается, и начинается новый цикл.

    Таким образом каждый элемент гарантированно будет встречаться ровно один раз за «раунд», а порядок выдачи в каждом раунде остаётся случайным.
    """

    def __init__(self, items: List[str]):
        if not items:
            raise ValueError("ShuffleBag не может быть инициализирован пустым списком")
        self._items = items.copy()
        self._reset()

    def _reset(self) -> None:
        random.shuffle(self._items)
        self._used: List[str] = []

    def pick(self) -> str:
        if not self._items or len(self._items) == 0:
            self._reset()
        item = self._items.pop()
        self._used.append(item)
        return item


# Пример использования ---------------------------------------------------------
if __name__ == "__main__":
    colors = ["red", "green", "blue", "yellow"]

    bag = ShuffleBag(colors)  # создаём шляпу

    # выбор 12 элементов; видно, что повторения возможны лишь после 4-го шага
    for i in range(12):
        print(f"{i + 1:2d}: {bag.pick()}")