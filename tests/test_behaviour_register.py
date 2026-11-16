"""
Тесты для функционала запоминания лиц и стоп-команд в Behaviour.
"""
import asyncio
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.behaviour import (
    Behaviour,
    REGISTER_COMMANDS,
    STOP_COMMANDS,
    NAME_PATTERNS,
)
from app.core.data.data import FaceDetection


# ==================== Тесты STOP_COMMANDS ====================

class TestStopCommands:
    """Проверка детекции стоп-команд."""

    def setup_method(self):
        self.behaviour = Behaviour()

    def test_stop_command_stop(self):
        assert self.behaviour._is_stop_command("стоп") is True

    def test_stop_command_molchi(self):
        assert self.behaviour._is_stop_command("молчи") is True

    def test_stop_command_hvatit(self):
        assert self.behaviour._is_stop_command("хватит") is True

    def test_stop_command_stop_english(self):
        assert self.behaviour._is_stop_command("stop") is True

    def test_stop_command_quiet(self):
        assert self.behaviour._is_stop_command("quiet") is True

    def test_stop_command_in_sentence(self):
        assert self.behaviour._is_stop_command("эй, стоп, не говори") is True

    def test_stop_command_not_in_normal_question(self):
        assert self.behaviour._is_stop_command("как тебя зовут") is False

    def test_stop_command_not_in_joke(self):
        assert self.behaviour._is_stop_command("расскажи анекдот") is False

    def test_stop_command_silence(self):
        assert self.behaviour._is_stop_command("silence") is True

    def test_stop_command_in_long_sentence(self):
        assert self.behaviour._is_stop_command("слушай, стоп, я сейчас занят") is True

    def test_stop_command_mixed_case(self):
        assert self.behaviour._is_stop_command("СТОП") is True

    def test_stop_command_not_in_museum(self):
        """Слово 'музей' не должно содержать стоп-команду."""
        assert self.behaviour._is_stop_command("музей") is False

    def test_stop_command_not_in_storm(self):
        """Слово 'шторка' не должно содержать стоп-команду."""
        assert self.behaviour._is_stop_command("шторка") is False

    def test_stop_command_with_stop_word(self):
        """Слово 'стопка' содержит 'стоп' — должно сработать."""
        assert self.behaviour._is_stop_command("стопка") is True

    def test_stop_command_speak_stop(self):
        assert self.behaviour._is_stop_command("speak stop now") is True

    def test_stop_command_zamolchi(self):
        assert self.behaviour._is_stop_command("замолчи") is True

    def test_stop_command_prekroti(self):
        assert self.behaviour._is_stop_command("прекрати") is True


# ==================== Тесты REGISTER_COMMANDS ====================

class TestRegisterCommands:
    """Проверка детекции команд запоминания лица."""

    def setup_method(self):
        self.behaviour = Behaviour()

    def test_register_command_zapomni(self):
        assert self.behaviour._is_register_command("запомни") is True

    def test_register_command_zapomni_meny(self):
        assert self.behaviour._is_register_command("запомни меня") is True

    def test_register_command_ia(self):
        assert self.behaviour._is_register_command("я -") is True

    def test_register_command_meny_zovut(self):
        assert self.behaviour._is_register_command("меня зовут") is True

    def test_register_command_moyo_imya(self):
        assert self.behaviour._is_register_command("моё имя") is True

    def test_register_command_zovi_meny(self):
        assert self.behaviour._is_register_command("зови меня") is True

    def test_register_command_in_sentence(self):
        assert self.behaviour._is_register_command("запомни меня. я - Иван.") is True

    def test_register_command_not_in_normal_sentence(self):
        assert self.behaviour._is_register_command("привет, как дела") is False

    def test_register_command_not_in_story(self):
        assert self.behaviour._is_register_command("расскажи историю") is False

    def test_register_command_zapomni_english(self):
        assert self.behaviour._is_register_command("zapomni") is True

    def test_register_command_partial_match(self):
        assert self.behaviour._is_register_command("запомни, я хочу представиться") is True

    def test_register_command_not_in_zapret(self):
        """Слово 'запрет' содержит 'запомни' частично — нет, не содержит."""
        assert self.behaviour._is_register_command("запрет") is False


# ==================== Тесты _is_stop_command (отдельный класс) ====================

class TestIsStopCommand:
    """Дополнительные тесты для _is_stop_command."""

    def setup_method(self):
        self.behaviour = Behaviour()

    def test_stop_command_all_variants(self):
        """Проверка всех вариантов стоп-команд."""
        for cmd in STOP_COMMANDS:
            assert self.behaviour._is_stop_command(cmd) is True

    def test_stop_command_empty(self):
        assert self.behaviour._is_stop_command("") is False

    def test_stop_command_whitespace(self):
        assert self.behaviour._is_stop_command("   ") is False

    def test_stop_command_with_numbers(self):
        assert self.behaviour._is_stop_command("стоп123") is True

    def test_stop_command_unicode(self):
        assert self.behaviour._is_stop_command("стоп！") is True

    def test_stop_command_newline(self):
        assert self.behaviour._is_stop_command("\nстоп\n") is True

    def test_stop_command_tab(self):
        assert self.behaviour._is_stop_command("\tстоп\t") is True


# ==================== Тесты NAME_PATTERNS regex ====================

class TestNamePatterns:
    """Проверка regex-паттернов извлечения имени."""

    def setup_method(self):
        self.behaviour = Behaviour()

    def test_pattern_en_dash(self):
        """Имя с en-dash (–)."""
        name = self.behaviour._extract_name_from_text("я – иван")
        assert name == "Иван"

    def test_pattern_em_dash(self):
        """Имя с em-dash (—)."""
        name = self.behaviour._extract_name_from_text("я — мария")
        assert name == "Мария"

    def test_pattern_hyphen(self):
        """Имя с дефисом (-)."""
        name = self.behaviour._extract_name_from_text("я - макс")
        assert name == "Макс"

    def test_pattern_multiple_spaces(self):
        """Имя с несколькими пробелами."""
        name = self.behaviour._extract_name_from_text("я    -    дмитрий")
        assert name == "Дмитрий"

    def test_pattern_space_hyphen_space(self):
        """Имя с пробелами вокруг дефиса."""
        name = self.behaviour._extract_name_from_text("я - елена")
        assert name == "Елена"

    def test_pattern_mixed_dash_types(self):
        """Разные типы тире в разных фразах."""
        n1 = self.behaviour._extract_name_from_text("я - алексей")
        n2 = self.behaviour._extract_name_from_text("я – ольга")
        n3 = self.behaviour._extract_name_from_text("я — петр")
        assert n1 == "Алексей"
        assert n2 == "Ольга"
        assert n3 == "Петр"

    def test_pattern_two_word_name_en_dash(self):
        name = self.behaviour._extract_name_from_text("я – анна мария")
        assert name == "Анна Мария"

    def test_pattern_two_word_name_em_dash(self):
        name = self.behaviour._extract_name_from_text("я — иван петрович")
        assert name == "Иван Петрович"

    def test_pattern_with_comma(self):
        name = self.behaviour._extract_name_from_text("я - сергей, запомни")
        assert name == "Сергей"

    def test_pattern_with_period(self):
        name = self.behaviour._extract_name_from_text("я - нина.")
        assert name == "Нина"

    def test_pattern_mixed_cyrillic_latin(self):
        """Кириллица + латиница в имени."""
        name = self.behaviour._extract_name_from_text("я - иван john")
        assert name == "Иван John"

    def test_pattern_lowercase_name(self):
        """Имя в нижнем регистре — должно стать с заглавной."""
        name = self.behaviour._extract_name_from_text("я - петр")
        assert name == "Петр"
        assert name[0].isupper()

    def test_pattern_uppercase_name(self):
        """Имя в верхнем регистре."""
        name = self.behaviour._extract_name_from_text("я - ПЁТР")
        assert name == "Пётр"

    def test_pattern_single_cyrillic_letter(self):
        """Имя из одной буквы."""
        name = self.behaviour._extract_name_from_text("я - а")
        assert name == "А"

    def test_pattern_no_name_after_dash(self):
        """Тире без имени после него."""
        name = self.behaviour._extract_name_from_text("я -")
        assert name is None

    def test_pattern_only_dash(self):
        """Только тире."""
        name = self.behaviour._extract_name_from_text("—")
        assert name is None

    def test_pattern_empty_string(self):
        name = self.behaviour._extract_name_from_text("")
        assert name is None

    def test_pattern_only_whitespace(self):
        name = self.behaviour._extract_name_from_text("   ")
        assert name is None

    def test_pattern_special_chars_only(self):
        name = self.behaviour._extract_name_from_text("!@#$%^&*()")
        assert name is None

    def test_pattern_name_with_underscore(self):
        """Имя с подчёркиванием — подчёркивание не входит в паттерн."""
        name = self.behaviour._extract_name_from_text("я - иван_иванов")
        assert name == "Иван"

    def test_pattern_name_with_numbers(self):
        """Имя с цифрами — цифры не входят в паттерн."""
        name = self.behaviour._extract_name_from_text("я - иван2024")
        assert name == "Иван"

    def test_pattern_zapomni_meny_zovut(self):
        """Паттерн 'запомни меня зовут' с en-dash."""
        name = self.behaviour._extract_name_from_text("запомни меня зовут – владимир")
        assert name == "Владимир"

    def test_pattern_zapomni_meny_zovut_with_comma(self):
        """Паттерн 'запомни меня зовут' с запятой."""
        name = self.behaviour._extract_name_from_text("запомни, меня зовут, вика")
        assert name == "Вика"

    def test_pattern_zapomni_direct_name(self):
        """Паттерн 'запомни имя' с прямой ссылкой."""
        name = self.behaviour._extract_name_from_text("запомни имя влад")
        assert name == "Влад"

    def test_pattern_zapomni_direct_name_with_comma(self):
        name = self.behaviour._extract_name_from_text("запомни, владимир")
        assert name == "Владимир"

    def test_pattern_three_word_name(self):
        """Имя из трёх слов."""
        name = self.behaviour._extract_name_from_text("я - анна мария иванова")
        assert name == "Анна Мария Иванова"

    def test_pattern_hyphenated_name(self):
        """Имя с дефисом внутри (например, двойная фамилия)."""
        name = self.behaviour._extract_name_from_text("я - мария-анна")
        assert name == "Мария-Анна"

    def test_pattern_english_name_with_hyphen(self):
        """Английское имя с дефисом."""
        name = self.behaviour._extract_name_from_text("я - mary-jane")
        assert name == "Mary-Jane"

    def test_pattern_yo_letter(self):
        """Имя с буквой ё."""
        name = self.behaviour._extract_name_from_text("я - ёлка")
        assert name == "Ёлка"

    def test_pattern_yo_in_name(self):
        name = self.behaviour._extract_name_from_text("меня зовут ёжик")
        assert name == "Ёжик"

    def test_pattern_name_with_exclamation(self):
        name = self.behaviour._extract_name_from_text("я - максим!")
        assert name == "Максим"

    def test_pattern_name_with_question(self):
        name = self.behaviour._extract_name_from_text("я - анна?")
        assert name == "Анна"

    def test_pattern_zapomni_without_meny(self):
        """Паттерн 'запомни' без 'меня'."""
        name = self.behaviour._extract_name_from_text("запомни, зовут сергей")
        assert name == "Сергей"

    def test_pattern_zapomni_with_period(self):
        name = self.behaviour._extract_name_from_text("запомни. зовут нина.")
        assert name == "Нина"

    def test_pattern_zapomni_with_dot(self):
        name = self.behaviour._extract_name_from_text("запомни. виктория")
        assert name == "Виктория"

    def test_pattern_zapomni_with_dash(self):
        name = self.behaviour._extract_name_from_text("запомни - олег")
        assert name == "Олег"

    def test_pattern_zapomni_with_en_dash(self):
        name = self.behaviour._extract_name_from_text("запомни – ольга")
        assert name == "Ольга"

    def test_pattern_zapomni_with_em_dash(self):
        name = self.behaviour._extract_name_from_text("запомни — денис")
        assert name == "Денис"

    def test_pattern_zapomni_with_newline(self):
        name = self.behaviour._extract_name_from_text("запомни\nзовут аня")
        assert name == "Аня"

    def test_pattern_zapomni_with_tab(self):
        name = self.behaviour._extract_name_from_text("запомни\тзовут лена")
        assert name == "Лена"

    def test_pattern_mixed_dash_between_names(self):
        """Разные типы тире между разными именами."""
        n1 = self.behaviour._extract_name_from_text("я - макс")
        n2 = self.behaviour._extract_name_from_text("я – олег")
        n3 = self.behaviour._extract_name_from_text("я — нина")
        assert n1 == "Макс"
        assert n2 == "Олег"
        assert n3 == "Нина"

    def test_pattern_complex_sentence(self):
        """Сложное предложение с именем."""
        name = self.behaviour._extract_name_from_text(
            "привет, я - иван петрович, запомни меня"
        )
        assert name == "Иван Петрович"

    def test_pattern_zapomni_meny_zovut_with_dash(self):
        """Паттерн 'запомни меня зовут' с тире."""
        name = self.behaviour._extract_name_from_text(
            "запомни меня зовут — владимир"
        )
        assert name == "Владимир"

    def test_pattern_zapomni_meny_zovut_with_comma_dash(self):
        name = self.behaviour._extract_name_from_text(
            "запомни, меня зовут - сергей"
        )
        assert name == "Сергей"

    def test_pattern_zapomni_direct_with_comma(self):
        name = self.behaviour._extract_name_from_text(
            "запомни, зовут андрей"
        )
        assert name == "Андрей"

    def test_pattern_zapomni_direct_with_period(self):
        name = self.behaviour._extract_name_from_text(
            "запомни. зовут вика"
        )
        assert name == "Вика"

    def test_pattern_zapomni_direct_with_hyphen(self):
        name = self.behaviour._extract_name_from_text(
            "запомни - олег"
        )
        assert name == "Олег"

    def test_pattern_zapomni_direct_with_en_dash(self):
        name = self.behaviour._extract_name_from_text(
            "запомни – елена"
        )
        assert name == "Елена"

    def test_pattern_zapomni_direct_with_em_dash(self):
        name = self.behaviour._extract_name_from_text(
            "запомни — дмитрий"
        )
        assert name == "Дмитрий"

    def test_pattern_zapomni_direct_with_newline(self):
        name = self.behaviour._extract_name_from_text(
            "запомни\nзовут аня"
        )
        assert name == "Аня"

    def test_pattern_zapomni_direct_with_tab(self):
        name = self.behaviour._extract_name_from_text(
            "запомни\tзовут лена"
        )
        assert name == "Лена"


# ==================== Тесты извлечения имени ====================

class TestExtractName:
    """Проверка извлечения имени из фразы."""

    def setup_method(self):
        self.behaviour = Behaviour()

    def test_extract_name_simple(self):
        name = self.behaviour._extract_name_from_text("я - иван")
        assert name == "Иван"

    def test_extract_name_with_dash(self):
        name = self.behaviour._extract_name_from_text("я – мария")
        assert name == "Мария"

    def test_extract_name_meny_zovut(self):
        name = self.behaviour._extract_name_from_text("меня зовут алексей")
        assert name == "Алексей"

    def test_extract_name_moyo_imya(self):
        name = self.behaviour._extract_name_from_text("моё имя елена")
        assert name == "Елена"

    def test_extract_name_zovi_meny(self):
        name = self.behaviour._extract_name_from_text("зови меня петя")
        assert name == "Петя"

    def test_extract_name_zapomni(self):
        name = self.behaviour._extract_name_from_text("запомни меня зовут ольга")
        assert name == "Ольга"

    def test_extract_name_two_words(self):
        """Имя из двух слов (например, отчество или двойная фамилия)."""
        name = self.behaviour._extract_name_from_text("я - анна мария")
        assert name == "Анна Мария"

    def test_extract_name_cyrillic(self):
        assert self.behaviour._extract_name_from_text("я - дмитрий") == "Дмитрий"

    def test_extract_name_latin(self):
        """Имя на латинице (должно работать, хотя и менее вероятно)."""
        name = self.behaviour._extract_name_from_text("я - john")
        assert name == "John"

    def test_extract_name_no_match(self):
        name = self.behaviour._extract_name_from_text("просто текст без имени")
        assert name is None

    def test_extract_name_empty(self):
        name = self.behaviour._extract_name_from_text("")
        assert name is None

    def test_extract_name_with_punctuation(self):
        name = self.behaviour._extract_name_from_text("я - иван, запомни")
        assert name == "Иван"

    def test_extract_name_with_numbers(self):
        """Имя не должно содержать цифры."""
        name = self.behaviour._extract_name_from_text("я - иван123")
        assert name == "Иван"

    def test_name_is_capitalized(self):
        """Имя всегда с заглавной буквы."""
        name = self.behaviour._extract_name_from_text("меня зовут иван")
        assert name[0].isupper()

    def test_name_single_word(self):
        """Имя из одного слова."""
        name = self.behaviour._extract_name_from_text("я - макс")
        assert name == "Макс"


# ==================== Тесты FaceDetection ====================

class TestFaceDetection:
    """Проверка работы с FaceDetection."""

    def test_create_face_detection(self):
        face = FaceDetection(
            bbox=[100, 200, 300, 400],
            name="unknown",
            confidence=0.95
        )
        assert face.bbox == [100, 200, 300, 400]
        assert face.name == "unknown"
        assert face.confidence == 0.95

    def test_face_detection_model_dump(self):
        face = FaceDetection(
            bbox=[10, 20, 30, 40],
            name="test",
            confidence=0.8
        )
        data = face.model_dump()
        assert data["bbox"] == [10, 20, 30, 40]
        assert data["name"] == "test"
        assert data["confidence"] == 0.8


# ==================== Тесты register_face ====================

class TestRegisterFace:
    """Проверка метода register_face с моками."""

    def setup_method(self):
        self.behaviour = Behaviour()

    @pytest.mark.asyncio
    async def test_register_face_success(self):
        """Успешная регистрация одного лица."""
        # Создаём тестовое лицо
        face = FaceDetection(
            bbox=[100, 100, 200, 200],
            name="unknown",
            confidence=0.95
        )
        self.behaviour._last_faces = [face]

        # Мокаем PostClient
        mock_client = AsyncMock()
        mock_client.post_register = AsyncMock(return_value=True)

        with patch("app.core.behaviour.PostClient") as MockPostClient:
            MockPostClient.return_value.__aenter__.return_value = mock_client
            MockPostClient.return_value.__aexit__.return_value = None

            result = await self.behaviour.register_face("ivan")

        assert result is True
        mock_client.post_register.assert_called_once_with({"username": "ivan"})

    @pytest.mark.asyncio
    async def test_register_face_no_faces(self):
        """Регистрация без обнаруженных лиц."""
        self.behaviour._last_faces = []
        result = await self.behaviour.register_face("ivan")
        assert result is False

    @pytest.mark.asyncio
    async def test_register_face_multiple_faces(self):
        """Регистрация когда обнаружено несколько лиц."""
        face1 = FaceDetection(bbox=[100, 100, 200, 200], name="unknown", confidence=0.9)
        face2 = FaceDetection(bbox=[300, 100, 400, 200], name="unknown", confidence=0.85)
        self.behaviour._last_faces = [face1, face2]

        result = await self.behaviour.register_face("ivan")
        assert result is False

    @pytest.mark.asyncio
    async def test_register_face_post_client_failure(self):
        """Ошибка PostClient при регистрации."""
        face = FaceDetection(bbox=[100, 100, 200, 200], name="unknown", confidence=0.95)
        self.behaviour._last_faces = [face]

        mock_client = AsyncMock()
        mock_client.post_register = AsyncMock(return_value=False)

        with patch("app.core.behaviour.PostClient") as MockPostClient:
            MockPostClient.return_value.__aenter__.return_value = mock_client
            MockPostClient.return_value.__aexit__.return_value = None

            result = await self.behaviour.register_face("ivan")

        assert result is False

    @pytest.mark.asyncio
    async def test_register_face_exception(self):
        """Исключение при работе с PostClient."""
        face = FaceDetection(bbox=[100, 100, 200, 200], name="unknown", confidence=0.95)
        self.behaviour._last_faces = [face]

        with patch("app.core.behaviour.PostClient") as MockPostClient:
            MockPostClient.return_value.__aenter__.side_effect = Exception("Connection refused")
            MockPostClient.return_value.__aexit__.return_value = None

            result = await self.behaviour.register_face("ivan")

        assert result is False

    @pytest.mark.asyncio
    async def test_register_face_username_format(self):
        """Проверка форматирования username."""
        face = FaceDetection(bbox=[100, 100, 200, 200], name="unknown", confidence=0.95)
        self.behaviour._last_faces = [face]

        mock_client = AsyncMock()
        mock_client.post_register = AsyncMock(return_value=True)

        with patch("app.core.behaviour.PostClient") as MockPostClient:
            MockPostClient.return_value.__aenter__.return_value = mock_client
            MockPostClient.return_value.__aexit__.return_value = None

            await self.behaviour.register_face("Иван Петрович")

        call_args = mock_client.post_register.call_args
        username = call_args[0][0]["username"]
        assert username == "иван_петрович"


# ==================== Тесты post_faces ====================

class TestPostFaces:
    """Проверка метода post_faces."""

    def setup_method(self):
        self.behaviour = Behaviour()

    @pytest.mark.asyncio
    async def test_post_faces_saves_last_faces(self):
        """post_faces сохраняет последнее обнаруженное лицо."""
        face1 = FaceDetection(bbox=[100, 100, 200, 200], name="unknown", confidence=0.95)
        face2 = FaceDetection(bbox=[300, 100, 400, 200], name="unknown", confidence=0.85)
        faces = [face1, face2]

        await self.behaviour.post_faces(faces)

        assert len(self.behaviour._last_faces) == 2
        assert self.behaviour._last_faces[0].bbox == [100, 100, 200, 200]
        assert self.behaviour._last_faces[1].bbox == [300, 100, 400, 200]

    @pytest.mark.asyncio
    async def test_post_faces_single_face(self):
        """post_faces с одним лицом."""
        face = FaceDetection(bbox=[100, 100, 200, 200], name="unknown", confidence=0.95)
        await self.behaviour.post_faces([face])

        assert len(self.behaviour._last_faces) == 1

    @pytest.mark.asyncio
    async def test_post_faces_empty_list(self):
        """post_faces с пустым списком."""
        await self.behaviour.post_faces([])

        assert len(self.behaviour._last_faces) == 0


# ==================== Тесты _is_phrase_recent ====================

class TestPhraseRecent:
    """Проверка функции _is_phrase_recent."""

    def test_phrase_recent_same_phrase(self):
        """Одинаковые фразы считаются недавними."""
        from app.core.behaviour import _record_phrase, _is_phrase_recent

        _record_phrase("привет")
        result = _is_phrase_recent("привет")
        assert result is True

    def test_phrase_recent_similar_phrase(self):
        """Похожие фразы считаются недавними."""
        from app.core.behaviour import _record_phrase, _is_phrase_recent

        _record_phrase("как дела")
        result = _is_phrase_recent("как твои дела")
        assert result is True

    def test_phrase_recent_different_phrase(self):
        """Разные фразы не считаются недавними."""
        from app.core.behaviour import _record_phrase, _is_phrase_recent

        _record_phrase("привет мир")
        result = _is_phrase_recent("отличная погода")
        assert result is False


# ==================== Тесты _record_phrase ====================

class TestRecordPhrase:
    """Проверка функции _record_phrase."""

    def test_record_phrase_adds_to_history(self):
        """Фраза добавляется в историю."""
        from app.core.behaviour import _record_phrase, _recent_phrases

        _record_phrase("тестовая фраза")
        assert len(_recent_phrases) > 0
        assert _recent_phrases[-1][0] == "тестовая фраза"

    def test_record_phrase_max_size(self):
        """История не превышает _MAX_RECENT_PHRASES."""
        from app.core.behaviour import _record_phrase, _recent_phrases, _MAX_RECENT_PHRASES

        # Очищаем историю
        _recent_phrases.clear()

        # Добавляем больше фраз, чем лимит
        for i in range(_MAX_RECENT_PHRASES + 10):
            _record_phrase(f"фраза {i}")

        assert len(_recent_phrases) <= _MAX_RECENT_PHRASES


# ==================== Интеграционные тесты ====================

class TestBehaviourIntegration:
    """Интеграционные тесты для Behaviour."""

    def setup_method(self):
        self.behaviour = Behaviour()

    def test_behaviour_initial_state(self):
        """Проверка начального состояния Behaviour."""
        from app.core.behaviour import State

        assert self.behaviour.state == State.SLEEPING
        assert self.behaviour.is_running is False
        assert self.behaviour._current_tts_task is None
        assert self.behaviour._abort_processing is False
        assert self.behaviour._last_faces == []

    def test_behaviour_has_required_methods(self):
        """Проверка наличия всех необходимых методов."""
        assert hasattr(self.behaviour, "_extract_name_from_text")
        assert hasattr(self.behaviour, "_is_register_command")
        assert hasattr(self.behaviour, "_is_stop_command")
        assert hasattr(self.behaviour, "register_face")
        assert hasattr(self.behaviour, "cancel_current_tts")
        assert hasattr(self.behaviour, "post_faces")
        assert hasattr(self.behaviour, "_speak")

    @pytest.mark.asyncio
    async def test_register_face_with_cyrillic_name(self):
        """Регистрация лица с кириллическим именем."""
        face = FaceDetection(
            bbox=[50, 50, 150, 150],
            name="unknown",
            confidence=0.98
        )
        self.behaviour._last_faces = [face]

        mock_client = AsyncMock()
        mock_client.post_register = AsyncMock(return_value=True)

        with patch("app.core.behaviour.PostClient") as MockPostClient:
            MockPostClient.return_value.__aenter__.return_value = mock_client
            MockPostClient.return_value.__aexit__.return_value = None

            result = await self.behaviour.register_face("дмитрий")

        assert result is True
        call_args = mock_client.post_register.call_args
        assert call_args[0][0]["username"] == "дмитрий"

    @pytest.mark.asyncio
    async def test_register_face_with_spaces_in_name(self):
        """Регистрация лица с пробелами в имени."""
        face = FaceDetection(
            bbox=[50, 50, 150, 150],
            name="unknown",
            confidence=0.98
        )
        self.behaviour._last_faces = [face]

        mock_client = AsyncMock()
        mock_client.post_register = AsyncMock(return_value=True)

        with patch("app.core.behaviour.PostClient") as MockPostClient:
            MockPostClient.return_value.__aenter__.return_value = mock_client
            MockPostClient.return_value.__aexit__.return_value = None

            result = await self.behaviour.register_face("иван петрович")

        assert result is True
        call_args = mock_client.post_register.call_args
        # Пробелы должны быть заменены на подчёркивания
        assert call_args[0][0]["username"] == "иван_петрович"
