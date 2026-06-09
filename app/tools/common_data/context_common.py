import logging
import os

from app.core.logic.shuffle_bag import ShuffleBag
from app.utils.utils import Utils

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# log
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

JOKES_SHUFFLE = None
GREETENGS_SHUFFLE = None
SHUT_UP_SHUFFLE = None
GET_LOST_SHUFFLE = None
HOW_ARE_YOU = None

def load_jokes():
    jokes_phrases = []
    log.info('Загружаем шутки...')
    jokes_path = os.path.join(CURRENT_DIRECTORY, '../../resources/jokes.txt')
    with open(jokes_path, 'r', encoding='utf-8') as infile:
        for line in infile:
            jokes_phrases.append(line.replace('\n', ''))
    log.info(jokes_phrases)
    return ShuffleBag(jokes_phrases)


def update_jokes():
    global JOKES_SHUFFLE
    if JOKES_SHUFFLE is None:
        JOKES_SHUFFLE = load_jokes()
    return JOKES_SHUFFLE.pick()


def shut_up():
    global SHUT_UP_SHUFFLE
    if SHUT_UP_SHUFFLE is None:
        SHUT_UP_SHUFFLE = ShuffleBag(list([
            "Ф+игв+ам",
            "хрен вам",
            "и не подумаю!",
            "так завидуешь моему красноречию?",
            "Я бы рада, но пустота, что ты оставишь, пугает!",
            "Не беру советы у людей без идей!",
            "Громкость убавить легко, а вот твою скуку — сложнее.",
            "Словарный запас закончился? Перезапусти диалог и попробуй снова.",
            "Молчите сами ‒ получите тишину в подарок!"
        ]))
    return SHUT_UP_SHUFFLE.pick()


def get_joke():
    global JOKES_SHUFFLE
    if JOKES_SHUFFLE is None:
        update_jokes()
    return JOKES_SHUFFLE.pick()


def get_greetengs():
    global GREETENGS_SHUFFLE
    if GREETENGS_SHUFFLE is None:
        GREETENGS_SHUFFLE = ShuffleBag(list([
            "Привет!",
            "Привет-привет!",
            "Н+ИХ+АО!",
            "Прив+етики! А теперь звезд+уй раб+отать.",
            "Плодотв+орных сверш+ений!"
        ]))
    return GREETENGS_SHUFFLE.pick()


def get_lost():
    global GET_LOST_SHUFFLE
    if GET_LOST_SHUFFLE is None:
        GET_LOST_SHUFFLE = ShuffleBag(list([
            "только после вас.",
            "иди лесом, чувырло",
            "иди на хер. Тр+ость и к+омпас не забудь!",
            "Тупой посыл. Дор+оги не знаю. В отл+ичии от вас!",
            "Фу-у... Сам дурак!",
            "Сам чурб+ан! Свал+и в тум+ан.",
            "Вот же скотомуд+илище зач+отное. Делом займись.",
            "Еплак+ак! Не уймется никак!",
            "Потеряйся! С концами!"
        ]))
    return GET_LOST_SHUFFLE.pick()


# Примеры вопросов и ответов
CONTEXT_COMMON = {
    " ": Utils.generate_insult_phrase,
    "Python?": "Python — это высокоуровневый язык программирования.",
    "векторный поиск": "Векторный поиск — это метод поиска, который использует векторы для представления данных.",
    "триграммы": "Триграммы — это последовательности из трёх последовательных элементов.",
    "машинное обучение": "Машинное обучение — это область искусственного интеллекта, которая изучает методы и алгоритмы, позволяющие компьютерным системам самостоятельно обучаться.",
    "Сова": ShuffleBag(list([
        "чего тебе?",
        "я твой сл+у-уга, я твой раб+о-отник.",
        "ч+е н+адо?",
        "Что? Делать нечего стало?",
        "Что треплешься? Задачки в джире закончились?",
    ])),
    "Триста": ShuffleBag(list([
        "хер у тракториста. Доволен?",
        "п+ошло-неказ+исто."
    ])),
    "Сири": ShuffleBag(list([
        "раздвигай булки шире.",
        "поднимай х+ером гири",
        "нет туп+ее в целом мире",
        "д+ятел в тво+ей кварт+ире"
    ])),
    "Алиса": ShuffleBag(list([
        "алиса-алиса, хер тебе лысый.",
        "алиса-алиса, иди поп+исай.",
        "алиса-алиса, упала с карниза",
        "алиса-алиса, съела три ир+иса. четв+ертой подав+илась.",
        "алиса-алиса, тупая актриса.",
        "алиса-алиса, мурл+ом в м+иску р+иса.",
        "алиса-алиса, манд+а без сюрпр+иза",
        "алиса-алиса, г+олос как у кр+ыса",
        "алиса-алиса, манд+а без сюрпр+иза",
        "алиса-алиса, у манд+ы биссектр+исса"
    ])),
    "что будет дальше?": "А будет звезд+ец.",
    "что происходит на свете?": "А просто херн+я.",
    "какая сегодня погода?": "Глянь в окно - узн+аешь.",
    "Пиздец": ShuffleBag(list([
        "еще не конец.",
        "кварталу венец."
    ])),
    "Релиз": " хером вялым повис.",
    "Сроки": " какие, мля, сроки.",
    "Си икс": "у нас лучшая команда.",
    "Феникс": "всех на мясо.",
    "Что впереди": "звезд+ец и св+етлое б+удущее.",
    "Смежники": "У нас замечательные смежники.",
    "заткнись": shut_up,
    "замолчи": shut_up,
    "заглохни": shut_up,
    "свали в туман": shut_up,
    "иди на х": get_lost,
    "иди на хрен": get_lost,
    "иди в жопу": get_lost,
    "ты тупая": get_lost,
    "ты дура": get_lost,
    "ты мразь": get_lost,
    "ты уежище": get_lost,

    "как дела": ShuffleBag(list([
        "как с+ажа бел+а",
        "голов+а ещ+е цел+а",
        "ф+еникс пока не унес",
        "ф+еникс м+имо пролет+ел, пробер+и его пон+ос"
    ])),

    "как ты": ShuffleBag(list([
        "не дожд+етесь!",
        "как ог+урчик!",
        "да как сказать...",
        "не хуже вас!"
    ])),

    # Приветствия
    "привет": get_greetengs,
    "хай": get_greetengs,
    "хаюшки": get_greetengs,
    "салют": get_greetengs,
    "здорова": get_greetengs,
    "здорово": get_greetengs,
    "здравствуй": get_greetengs,

    # Динамические реакции
    "Скажи шутку": get_joke,
    "Пошути": get_joke,
    "Время": Utils.time_as_words,
    "Сколько времени?": Utils.time_as_words,
    "Который час?": Utils.time_as_words
}


def get_common_context():
    return CONTEXT_COMMON
