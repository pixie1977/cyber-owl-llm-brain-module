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
