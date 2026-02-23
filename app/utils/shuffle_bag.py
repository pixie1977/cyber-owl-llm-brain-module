from __future__ import annotations

import random
from typing import List, Iterator, TypeVar

T = TypeVar('T')

class ShuffleBag(Iterator[T]):
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
    def __init__(self, items: List[T], *, rng: random.Random | None = None):
        if not items:
            raise ValueError("Нужен непустой список items")
        self._items: List[T] = list(items)
        self._bag: List[T]  = []          # текущее содержимое «шляпы»
        self._rng           = rng or random.SystemRandom()
        self._reshuffle()                 # первый раз заполняем шляпу

    def _reshuffle(self) -> None:
        """Перемешиваем элементы и кладём в шляпу снова."""
        self._bag = self._items[:]        # копия исходного списка
        self._rng.shuffle(self._bag)

    # —–– стандартные методы Python-итератора –––––––––––––––––––––––
    def __iter__(self) -> "ShuffleBag[T]":
        return self

    def __next__(self) -> T:
        if not self._bag:                 # опустела — перемешиваем заново
            self._reshuffle()
        return self._bag.pop()            # забираем «верхний» элемент

    # —–– удобный метод «возьми один» –––––––––––––––––––––––––––––––
    def pick(self) -> T:
        """Эквивалентно next(bag), но читается понятнее."""
        return next(self)


# Пример использования ---------------------------------------------------------
if __name__ == "__main__":
    colors = ["red", "green", "blue", "yellow"]

    bag = ShuffleBag(colors)  # создаём шляпу

    # выбор 12 элементов; видно, что повторения возможны лишь после 4-го шага
    for i in range(12):
        print(f"{i + 1:2d}: {bag.pick()}")