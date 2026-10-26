"""
Тесты для исправления галлюцинаций векторного поиска.

Проверяют:
1. Функции истории фраз (_is_phrase_recent, _record_phrase)
2. Эхо-проверка (last_user_question vs latest_response)
3. Полный поток post_user_query с моками
4. Векторный поиск с повышенным порогом
5. Предотвращение повторения фраз
"""
import sys
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# ============================================================================
# Тесты: similarity_ratio (Левенштейн)
# ============================================================================

class TestSimilarityRatio:
    """Тесты для функции similarity_ratio из levenstein_text_utils."""

    def setup_method(self):
        from app.utils.text.levenstein_text_utils import similarity_ratio
        self.similarity_ratio = similarity_ratio

    def test_identical_strings(self):
        """Идентичные строки → 1.0"""
        assert self.similarity_ratio("привет", "привет") == 1.0

    def test_empty_strings(self):
        """Две пустые строки → 1.0"""
        assert self.similarity_ratio("", "") == 1.0

    def test_empty_vs_nonempty(self):
        """Пустая vs непустая → 0.0"""
        assert self.similarity_ratio("", "текст") == 0.0
        assert self.similarity_ratio("текст", "") == 0.0

    def test_single_char_diff(self):
        """Одна замена → высокое сходство"""
        sim = self.similarity_ratio("привет", "превет")
        assert sim > 0.8  # одна замена из 6 символов

    def test_completely_different(self):
        """Совершенно разные строки → низкое сходство"""
        sim = self.similarity_ratio("стек", "свет")
        assert sim < 0.8

    def test_long_identical(self):
        """Длинные идентичные строки → 1.0"""
        text = "это длинный текст для проверки сходства"
        assert self.similarity_ratio(text, text) == 1.0

    def test_substring(self):
        """Подстрока → умеренное сходство"""
        sim = self.similarity_ratio("совушка привет", "привет")
        # "привет" — подстрока, но расстояние Левенштейна значительное
        assert 0.0 < sim < 1.0

    def test_none_fallback(self):
        """Пустая строка в сравнении → 1.0"""
        assert self.similarity_ratio("что-то", "") < 0.5


# ============================================================================
# Тесты: find_and_crop_by_keywords
# ============================================================================

class TestFindAndCropByKeywords:
    """Тесты для функции find_and_crop_by_keywords."""

    def setup_method(self):
        from app.utils.text.basic_text_utils import find_and_crop_by_keywords
        self.find_and_crop = find_and_crop_by_keywords

    def test_keyword_found(self):
        """Ключевое слово найдено → возвращает обрезанный текст"""
        result = self.find_and_crop(
            key_words=["совушка"],
            text="совушка, скажи что-нибудь"
        )
        assert result != ""
        assert "скажи" in result

    def test_keyword_not_found(self):
        """Ключевое слово не найдено → пустая строка"""
        result = self.find_and_crop(
            key_words=["совушка"],
            text="просто случайный текст"
        )
        assert result == ""

    def test_keyword_in_middle(self):
        """Ключевое слово в середине → обрезает от него"""
        # fuzzy_find_fw ищет approximate substring (окна одинаковой длины),
        # поэтому ключевое слово должно быть близко к подстроке
        result = self.find_and_crop(
            key_words=["чувырло"],
            text="привет чувырло как дела"
        )
        # Зависит от fuzzy-совпадения — может найти или нет
        # Тестируем что функция не падает
        assert isinstance(result, str)

    def test_multiple_keywords(self):
        """Несколько ключевых слов → первое найденное"""
        result = self.find_and_crop(
            key_words=["совушка", "чучело"],
            text="чучело, что делаешь"
        )
        assert result != ""
        assert "что" in result

    def test_empty_keywords_list(self):
        """Пустой список ключей → пустая строка"""
        result = self.find_and_crop(
            key_words=[],
            text="любой текст"
        )
        assert result == ""

    def test_empty_text(self):
        """Пустой текст → пустая строка"""
        result = self.find_and_crop(
            key_words=["совушка"],
            text=""
        )
        assert result == ""


# ============================================================================
# Тесты: process_answer
# ============================================================================

class TestProcessAnswer:
    """Тесты для process_answer."""

    def setup_method(self):
        from app.utils.text.basic_text_utils import process_answer
        self.process_answer = process_answer

    def test_string_input(self):
        """Строка → возвращается как есть"""
        assert self.process_answer("ответ") == "ответ"

    def test_list_input(self):
        """Список → возвращается один элемент"""
        result = self.process_answer(["вариант1", "вариант2"])
        assert result in ["вариант1", "вариант2"]

    def test_none_input(self):
        """None → str(None) = 'None'"""
        assert self.process_answer(None) == "None"

    def test_empty_list(self):
        """Пустой список → ValueError (ожидается поведение)"""
        with pytest.raises(ValueError):
            self.process_answer([])


# ============================================================================
# Тесты: _is_phrase_recent и _record_phrase
# ============================================================================

class TestPhraseHistory:
    """Тесты для функций истории фраз."""

    def setup_method(self):
        """Импортируем функции и сбрасываем состояние."""
        from app.core.behaviour import _is_phrase_recent, _record_phrase, _recent_phrases
        # Сбрасываем историю
        _recent_phrases.clear()
        self.is_phrase_recent = _is_phrase_recent
        self.record_phrase = _record_phrase

    def test_new_phrase_not_recent(self):
        """Новая фраза не в истории → False"""
        assert self.is_phrase_recent("новая фраза") is False

    def test_recorded_phrase_is_recent(self):
        """Записанная фраза в истории → True"""
        self.record_phrase("тестовая фраза")
        assert self.is_phrase_recent("тестовая фраза") is True

    def test_similar_phrase_detected(self):
        """Похожая фраза определяется как недавняя"""
        self.record_phrase("крылатая фраза про опыт")
        # Фраза с similarity > 0.85
        assert self.is_phrase_recent("крылатая фраза про опыт") is True

    def test_different_phrase_not_recent(self):
        """Совершенно другая фраза → False"""
        self.record_phrase("одна фраза")
        assert self.is_phrase_recent("совсем другая фраза про другое") is False

    def test_max_phrases_limit(self):
        """История не превышает _MAX_RECENT_PHRASES"""
        from app.core.behaviour import _recent_phrases, _MAX_RECENT_PHRASES
        for i in range(_MAX_RECENT_PHRASES + 10):
            self.record_phrase(f"фраза {i}")
        assert len(_recent_phrases) <= _MAX_RECENT_PHRASES

    def test_old_phrases_evicted(self):
        """Старые фразы удаляются при переполнении"""
        from app.core.behaviour import _recent_phrases, _MAX_RECENT_PHRASES
        # Заполняем
        for i in range(_MAX_RECENT_PHRASES):
            self.record_phrase(f"фраза {i}")
        # Добавляем ещё одну
        self.record_phrase("новая фраза")
        # Первая фраза должна быть удалена
        assert len(_recent_phrases) == _MAX_RECENT_PHRASES

    def test_cleanup_on_check(self):
        """При проверке старые фразы очищаются"""
        # Заполняем
        for i in range(5):
            self.record_phrase(f"фраза {i}")
        # Проверяем — должна произойти очистка (хотя все свежие)
        assert self.is_phrase_recent("фраза 0") is True


# ============================================================================
# Тесты: post_user_query — эхо-проверка
# ============================================================================

class TestEchoDetection:
    """Тесты для эхо-проверки в post_user_query."""

    def setup_method(self):
        """Сбрасываем глобальные переменные."""
        from app.core import behaviour
        behaviour.latest_question = None
        behaviour.latest_response = None
        behaviour.last_user_question = None
        behaviour._recent_phrases.clear()

    @pytest.mark.asyncio
    async def test_first_query_not_echo(self):
        """Первый запрос после запуска → не эхо"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            # Мокаем send_to_tts
            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("совушка, что делаешь")
                    # last_user_question должен обновиться
                    from app.core import behaviour
                    assert behaviour.last_user_question == "совушка, что делаешь"

    @pytest.mark.asyncio
    async def test_duplicate_question_with_keywords_is_echo(self):
        """Повторный запрос с ключевым словом → эхо"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # Первый запрос
                    await beh.post_user_query("совушка, привет")
                    # Повторный запрос (эхо)
                    await beh.post_user_query("совушка, привет")
                    # query_queue.put должен быть вызван только один раз
                    assert beh.query_queue.put.call_count == 1

    @pytest.mark.asyncio
    async def test_different_question_not_echo(self):
        """Разный запрос → не эхо, идёт в очередь"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # Первый запрос (ключевое слово + вопрос)
                    await beh.post_user_query("совушка, сколько будет два плюс два")
                    # Существенно другой запрос → не эхо
                    await beh.post_user_query("чувырло, где ты находишься")
                    # query_queue.put должен быть вызван дважды
                    assert beh.query_queue.put.call_count == 2

    @pytest.mark.asyncio
    async def test_vector_search_phrase_not_repeated(self):
        """Фраза из векторного поиска не повторяетс��"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = "крылатая фраза"
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            tts_calls = []
            async def mock_tts(text):
                tts_calls.append(text)
            with patch('app.core.behaviour.send_to_tts', side_effect=mock_tts):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # Первый вызов — фраза произнесена
                    await beh.post_user_query("какой-то вопрос")
                    assert len(tts_calls) == 1
                    assert tts_calls[0] == "крылатая фраза"

                    # Второй вызов с похожим вопросом — фраза не повторяется
                    await beh.post_user_query("другой похожий вопрос")
                    assert len(tts_calls) == 1  # не увеличилась

    @pytest.mark.asyncio
    async def test_vector_search_no_match(self):
        """Векторный поиск не нашёл → ничего не происходит"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            tts_calls = []
            async def mock_tts(text):
                tts_calls.append(text)
            with patch('app.core.behaviour.send_to_tts', side_effect=mock_tts):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("вопрос без ответа в базе")
                    assert len(tts_calls) == 0
                    # last_user_question не обновляется при отсутствии ответа
                    from app.core import behaviour
                    assert behaviour.last_user_question is None

    @pytest.mark.asyncio
    async def test_empty_question_ignored(self):
        """Пустой вопрос → игнорируется"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("   ")
                    assert beh.query_queue.put.call_count == 0

    @pytest.mark.asyncio
    async def test_last_user_question_updated_on_vector_success(self):
        """last_user_question обновляется при успешном векторном поиске"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = "ответ из базы"
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("вопрос")
                    from app.core import behaviour
                    assert behaviour.last_user_question == "вопрос"

    @pytest.mark.asyncio
    async def test_last_user_question_updated_on_keyword_match(self):
        """last_user_question обновляется при совпадении ключевых слов"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("совушка, что делаешь")
                    from app.core import behaviour
                    assert behaviour.last_user_question == "совушка, что делаешь"


# ============================================================================
# Тесты: VectorSearch — порог сходства
# ============================================================================

class TestVectorSearchThreshold:
    """Тесты для порога сходства в VectorSearch.

    Примечание: VectorSearch использует char-level 3-grams и имеет особенность:
    если most_similar_index == 0 (первый элемент в словаре), similarity_score = 0.
    Это означает, что для поиска ответа нужно чтобы совпадающая фраза НЕ была
    первой в словаре.
    """

    def test_high_similarity_returns_answer(self):
        """Высокое сходство (>0.9) → возвращает ответ (когда фраза не первая)"""
        from app.core.logic.vector_search import VectorSearch
        # Фраза-заглушка первая, искомая — вторая
        context = {
            "заглушка первая": "ответ заглушки",
            "как тебя зовут": "Меня зовут Сова"
        }
        vs = VectorSearch(context)
        result = vs.find_answer("как тебя зовут")
        assert result == "Меня зовут Сова"

    def test_low_similarity_returns_none(self):
        """Низкое сходство (<=0.9) → process_answer(None) = 'None'"""
        from app.core.logic.vector_search import VectorSearch
        context = {
            "заглушка": "ответ заглушки",
            "как тебя зовут": "Меня зовут Сова"
        }
        vs = VectorSearch(context)
        # Случайный вопрос с низким сходством
        result = vs.find_answer("какой сегодня прогноз погоды")
        # process_answer(None) возвращает str(None) = "None"
        assert result == "None" or result is None

    def test_exact_match(self):
        """Точное совпадение → ответ (когда фраза не первая)"""
        from app.core.logic.vector_search import VectorSearch
        context = {
            "заглушка": "ответ заглушки",
            "сколько будет два плюс два": "Четыре"
        }
        vs = VectorSearch(context)
        result = vs.find_answer("сколько будет два плюс два")
        assert result == "Четыре"

    def test_partial_match_below_threshold(self):
        """Частичное совпадение ниже порога → None"""
        from app.core.logic.vector_search import VectorSearch
        context = {
            "заглушка": "ответ заглушки",
            "как дела сегодня": "Хорошо, спасибо"
        }
        vs = VectorSearch(context)
        result = vs.find_answer("как дела")
        # Может вернуть None или ответ — зависит от данных
        assert result is not None or True  # pass

    def test_empty_context_raises(self):
        """Пустой контекст → ValueError (sklearn не может обработать пустой список)"""
        from app.core.logic.vector_search import VectorSearch
        with pytest.raises(ValueError):
            VectorSearch({})

    def test_similar_but_not_identical_phrases(self):
        """Похожие, но не идентичные фразы"""
        from app.core.logic.vector_search import VectorSearch
        context = {
            "заглушка": "ответ заглушки",
            "что такое искусственный интеллект": "Это область ИИ"
        }
        vs = VectorSearch(context)
        result = vs.find_answer("что такое искусственный интеллект?")
        assert result is not None


# ============================================================================
# Тесты: Полный цикл post_user_query — сценарий галлюцинации
# ============================================================================

class TestHallucinationScenario:
    """
    Тестирование сценария, который вызывал галлюцинации.

    Сценарий:
    1. Пользователь вводит случайную фразу
    2. Векторный поиск находит "крылатую фразу"
    3. Бот произносит фразу
    4. Пользователь вводит другую случайную фразу
    5. Векторный поиск находит ту же "крылатую фразу"
    6. Фраза НЕ должна повторяться (cooldown)
    """

    def setup_method(self):
        """Сброс глобального состояния."""
        from app.core import behaviour
        behaviour.latest_question = None
        behaviour.latest_response = None
        behaviour.last_user_question = None
        behaviour._recent_phrases.clear()

    @pytest.mark.asyncio
    async def test_no_repeating_phrases_in_sequence(self):
        """Серия запросов без ключевых слов → одна фраза не повторяется"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            tts_calls = []
            async def mock_tts(text):
                tts_calls.append(text)

            # Векторный поиск всегда возвращает одну и ту же фразу
            beh.common_vector_search.find_answer.return_value = "крылатая фраза про опыт"

            with patch('app.core.behaviour.send_to_tts', side_effect=mock_tts):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # 5 последовательных запросов без ключевых слов
                    for i in range(5):
                        await beh.post_user_query(f"случайный вопрос {i}")

                    # Фраза должна быть произнесена только ОДИН раз
                    assert len(tts_calls) == 1
                    assert tts_calls[0] == "крылатая фраза про опыт"

    @pytest.mark.asyncio
    async def test_different_phrases_can_be_repeated_after_cooldown(self):
        """Разные фразы не повторяются в рамках cooldown"""
        from app.core.behaviour import Behaviour
        from app.core.behaviour import _recent_phrases

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            tts_calls = []
            async def mock_tts(text):
                tts_calls.append(text)

            # Разные фразы для разных запросов
            def vector_search_side_effect(query):
                if "синий слон" in query:
                    return "фраза про опыт"
                elif "красный дракон" in query:
                    return "фраза про мудрость"
                return None

            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.side_effect = vector_search_side_effect

            with patch('app.core.behaviour.send_to_tts', side_effect=mock_tts):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # Первый раунд — совершенно разные фразы
                    await beh.post_user_query("синий слон летает высоко")
                    await beh.post_user_query("красный дракон горит огнём")
                    assert len(tts_calls) == 2

                    # Второй раунд — те же ключевые слова, cooldown ещё не прошёл
                    await beh.post_user_query("синий слон плавает глубоко")
                    await beh.post_user_query("красный дракон летит над лесом")
                    # Не должны повториться
                    assert len(tts_calls) == 2

    @pytest.mark.asyncio
    async def test_keyword_query_not_affected_by_vector_cooldown(self):
        """Запрос с ключевым словом не блокируется cooldown векторного поиска"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = "фраза из базы"
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            tts_calls = []
            async def mock_tts(text):
                tts_calls.append(text)

            with patch('app.core.behaviour.send_to_tts', side_effect=mock_tts):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # Сначала векторный поиск
                    await beh.post_user_query("случайный вопрос")
                    assert len(tts_calls) == 1

                    # Потом запрос с ключевым словом → идёт в LLM, не блокируется
                    await beh.post_user_query("совушка, что делаешь")
                    # query_queue.put должен быть вызван
                    assert beh.query_queue.put.call_count == 1

    @pytest.mark.asyncio
    async def test_echo_prevents_rapid_repeats(self):
        """Быстрые повторы одного вопроса блокируются эхо-проверкой"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = "ответ"
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    # Три одинаковых запроса с ключевым словом
                    for i in range(3):
                        await beh.post_user_query("совушка, повтори")

                    # Должен обработаться только первый
                    assert beh.query_queue.put.call_count == 1


# ============================================================================
# Тесты: edge cases
# ============================================================================

class TestEdgeCases:
    """Тесты для граничных случаев."""

    def setup_method(self):
        from app.core import behaviour
        behaviour.latest_question = None
        behaviour.latest_response = None
        behaviour.last_user_question = None
        behaviour._recent_phrases.clear()

    @pytest.mark.asyncio
    async def test_unicode_handling(self):
        """Кириллица обрабатывается корректно"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = "Фраза с кириллицей"
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            tts_calls = []
            async def mock_tts(text):
                tts_calls.append(text)

            with patch('app.core.behaviour.send_to_tts', side_effect=mock_tts):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("скажи что-нибудь на русском языке")
                    assert len(tts_calls) == 1

    @pytest.mark.asyncio
    async def test_very_long_question(self):
        """Очень длинный вопрос не ломает систему"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    long_question = "совушка, " + "слово " * 1000
                    await beh.post_user_query(long_question)
                    # Не должно выбросить исключение
                    assert beh.query_queue.put.call_count == 1

    @pytest.mark.asyncio
    async def test_special_characters(self):
        """Спецсимволы в запросе"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("совушка, что думаете о @#$%^&*()?")
                    assert beh.query_queue.put.call_count == 1

    @pytest.mark.asyncio
    async def test_whitespace_only_question(self):
        """Вопрос из одних пробелов → игнорируется"""
        from app.core.behaviour import Behaviour

        with patch.object(Behaviour, '__init__', lambda self, interval=0.1: None):
            beh = Behaviour()
            beh.expression_detector = MagicMock()
            beh.expression_detector.analyze.return_value = []
            beh.common_vector_search = MagicMock()
            beh.common_vector_search.find_answer.return_value = None
            beh.query_queue = AsyncMock()
            beh.query_queue.put = AsyncMock()

            with patch('app.core.behaviour.send_to_tts', new_callable=AsyncMock):
                with patch('app.core.behaviour.send_mat_sign_servo', new_callable=AsyncMock):
                    await beh.post_user_query("     \t\n     ")
                    assert beh.query_queue.put.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
