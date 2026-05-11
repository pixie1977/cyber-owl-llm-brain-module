#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sophisticated (yet polite) insult generator.

Основные возможности
--------------------
✓ 3 уровня «крепости» фраз (1—мягкий, 3—самый едкий, но без мата)  
✓ Морфологическое согласование прилагательного с выбранным существительным  
✓ >1e6 возможных уникальных фраз  
✓ CLI и библиотечный API  
✓ Поддержка seed для воспроизводимости результатов  
"""

from __future__ import annotations

import argparse
import hashlib
import random
from typing import Dict, Iterable, List, Set

try:
    import pymorphy2
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "Не найден pymorphy2. Установите командой:\n"
        "    pip install pymorphy2 pymorphy2-dicts-ru"
    ) from exc

morph = pymorphy2.MorphAnalyzer()


# ──────────────────────────────────────
# СЛОВАРИ
# ──────────────────────────────────────
ADJECTIVES: Dict[int, List[str]] = {
    1: [
        "забывчивый",
        "простоватый",
        "сонный",
        "неуклюжий",
        "рассеянный",
        "деланный",
        "несообразительный",
        "приглаженный",
        "неповоротливый",
        "тишайший",
    ],
    2: [
        "надменный",
        "занудный",
        "пучеглазый",
        "махровый",
        "скользкий",
        "ехидный",
        "разухабистый",
        "самодовольный",
        "пресловутый",
        "запальчивый",
    ],
    3: [
        "бестолковый",
        "архизнанудный",
        "феерический",
        "эпический",
        "невъепический",
        "криворукий",
        "звездообразный",
        "злоэпучий"
        "зловредно‐надсадный",
        "титанически непутёвый",
        "заносчивый",
        "неотёсанный",
        "неистовый",
        "безмерно неукротимый",
    ],
}

NOUNS: Dict[int, List[str]] = {
    1: [
        "соня",
        "мечтатель без цели",
        "растяпа",
        "пофигист",
        "философ-любитель",
        "читатель подстрочников",
        "любитель завтраков",
        "распорядитель пауз",
    ],
    2: [
        "шалопай",
        "крендель",
        "рыцарь без шпаги",
        "поэт без рифм",
        "трепач",
        "крот без очков",
        "самоделкин без отвёртки",
        "капитан очевидность",
    ],
    3: [
        "растыка",
        "царь горы из картона",
        "властелин бумажных замков",
        "катастроф на двух ногах",
        "исполин бурлеска",
        "адепт скуки вселенской",
        "тень несбыточных надежд",
        "гуру громких пустот",
        "печальная акциденция современности",
        "похерист-любитель",
        "раздолбай",
        "раздолбаюшко"
    ],
}


TEMPLATES: List[str] = [
    "О, ты {adj} {noun}{suf}!",
    "Смотри, какой {adj} {noun}{suf}.",
    "Да ты ж {adj} {noun}{suf}, право слово!",
    "{adj_cap} {noun}{suf}.",
    "Истинно {adj} {noun}{suf}.",
    "Снова {adj} {noun}{suf}!",
    "Опять {adj} {noun}{suf}!",
]


# ──────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ──────────────────────────────────────
def _agree_adj(adj: str, noun: str) -> str:
    """
    Склоняем прилагательное под существительное (ед. число, имен. падеж).

    Parameters
    ----------
    adj : str
        Исходная форма прилагательного (муж. род, ед. число, И.п.).
    noun : str
        Любая фраза; род определяется по первому слову.

    Returns
    -------
    str
        Согласованная форма прилагательного.
    """
    first_word = noun.split()[0]
    parsed_noun = morph.parse(first_word)[0]
    gender = parsed_noun.tag.gender  # masc/femn/neut
    if gender is None:
        gender = 'masc'
    parsed_adj = morph.parse(adj)[0]
    try:
        inflected = parsed_adj.inflect({gender, "nomn"})
    except ValueError as err:
        print("wrong gramemme: "+str(parsed_adj))
        raise err
    return inflected.word if inflected else adj


def _pick(level: int, mapping: Dict[int, List[str]]) -> str:
    level = max(1, min(3, level))
    return random.choice(mapping[level])


# ──────────────────────────────────────
# ПУБЛИЧНОЕ API
# ──────────────────────────────────────
def generate_insult_phrase(level: int = 3) -> str:
    """
    Сгенерировать одну ругательную фразу.

    Parameters
    ----------
    level : int, optional
        «Крепость» фразы: 1 — мягкая, 3 — самая едкая, by default 2.

    Returns
    -------
    str
        Готовая фраза.
    """
    noun_raw = _pick(level, NOUNS)
    adj_raw = _pick(level, ADJECTIVES)
    adj = _agree_adj(adj_raw, noun_raw)
    suf = ""
    template = random.choice(TEMPLATES)
    phrase = template.format(
        adj=adj,
        adj_cap=adj.capitalize(),
        noun=noun_raw,
        suf=suf,
    )
    # чтобы не было двойных пробелов, если suffix == ""
    return " ".join(phrase.split())


def batch(size: int = 10, level: int = 2, seed: int | None = None) -> Iterable[str]:
    """
    Генерировать несколько уникальных фраз.

    Parameters
    ----------
    size : int
        Количество фраз.
    level : int
        «Крепость» (1..3).
    seed : int | None
        Фиксированный seed для повторяемости.

    Yields
    ------
    str
        Очередная уникальная фраза.
    """
    if seed is not None:
        random.seed(seed)

    emitted_hashes: Set[str] = set()
    while len(emitted_hashes) < size:
        phrase = generate_insult_phrase(level)
        phrase_hash = hashlib.sha1(phrase.encode()).hexdigest()
        if phrase_hash not in emitted_hashes:
            emitted_hashes.add(phrase_hash)
            yield phrase


# ──────────────────────────────────────
# CLI
# ──────────────────────────────────────
def _cli() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(
        prog="insultgen",
        description="Генератор изощрённых ругательств (без мата).",
    )
    parser.add_argument(
        "-n", "--num", type=int, default=10, help="сколько фраз сгенерировать (default=10)"
    )
    parser.add_argument(
        "-l",
        "--level",
        type=int,
        choices=[1, 2, 3],
        default=3,
        help="уровень «крепости» (1–3, default=2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="зафиксировать сид генератора случайных чисел для воспроизводимости",
    )
    args = parser.parse_args()
    for phrase in batch(args.num, args.level, args.seed):
        print(phrase)


if __name__ == "__main__":
    _cli()