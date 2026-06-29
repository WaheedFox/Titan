import pytest
from unittest.mock import AsyncMock, MagicMock
from titan.adapter import TelegramAdapter
from titan.bot import Titan


def make_adapter():
    api = MagicMock()
    api.request = AsyncMock(return_value={"ok": True, "result": {}})
    return TelegramAdapter(api), api


def make_bot():
    bot = Titan("fake-token")
    bot._api = MagicMock()
    bot._api.request = AsyncMock(return_value={"ok": True, "result": {}})
    bot.telegram = TelegramAdapter(bot._api)
    return bot


class TestAdapterAttachment:
    def test_bot_has_telegram_attribute(self):
        bot = Titan("fake-token")
        assert hasattr(bot, "telegram")

    def test_bot_telegram_is_adapter(self):
        bot = Titan("fake-token")
        assert isinstance(bot.telegram, TelegramAdapter)

    def test_adapter_uses_same_api(self):
        bot = Titan("fake-token")
        assert bot.telegram._api is bot._api


class TestSendPhoto:
    @pytest.mark.asyncio
    async def test_calls_sendPhoto(self):
        adapter, api = make_adapter()
        await adapter.send_photo(chat_id=100, photo="file_id")
        api.request.assert_called_once_with("sendPhoto", {"chat_id": 100, "photo": "file_id"})

    @pytest.mark.asyncio
    async def test_with_caption(self):
        adapter, api = make_adapter()
        await adapter.send_photo(chat_id=100, photo="file_id", caption="hi")
        call_data = api.request.call_args[0][1]
        assert call_data["caption"] == "hi"

    @pytest.mark.asyncio
    async def test_with_parse_mode(self):
        adapter, api = make_adapter()
        await adapter.send_photo(chat_id=100, photo="file_id", parse_mode="HTML")
        call_data = api.request.call_args[0][1]
        assert call_data["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_without_optional_fields(self):
        adapter, api = make_adapter()
        await adapter.send_photo(chat_id=100, photo="file_id")
        call_data = api.request.call_args[0][1]
        assert "caption" not in call_data
        assert "parse_mode" not in call_data

    @pytest.mark.asyncio
    async def test_with_reply_markup_dict(self):
        adapter, api = make_adapter()
        markup = {"inline_keyboard": []}
        await adapter.send_photo(chat_id=100, photo="file_id", reply_markup=markup)
        call_data = api.request.call_args[0][1]
        assert call_data["reply_markup"] == markup

    @pytest.mark.asyncio
    async def test_with_reply_markup_object(self):
        adapter, api = make_adapter()
        markup = MagicMock()
        markup.to_dict.return_value = {"inline_keyboard": []}
        await adapter.send_photo(chat_id=100, photo="file_id", reply_markup=markup)
        call_data = api.request.call_args[0][1]
        assert call_data["reply_markup"] == {"inline_keyboard": []}


class TestSendVideo:
    @pytest.mark.asyncio
    async def test_calls_sendVideo(self):
        adapter, api = make_adapter()
        await adapter.send_video(chat_id=100, video="file_id")
        api.request.assert_called_once_with("sendVideo", {"chat_id": 100, "video": "file_id"})

    @pytest.mark.asyncio
    async def test_with_caption(self):
        adapter, api = make_adapter()
        await adapter.send_video(chat_id=100, video="file_id", caption="clip")
        call_data = api.request.call_args[0][1]
        assert call_data["caption"] == "clip"


class TestSendDocument:
    @pytest.mark.asyncio
    async def test_calls_sendDocument(self):
        adapter, api = make_adapter()
        await adapter.send_document(chat_id=100, document="file_id")
        api.request.assert_called_once_with("sendDocument", {"chat_id": 100, "document": "file_id"})

    @pytest.mark.asyncio
    async def test_with_caption(self):
        adapter, api = make_adapter()
        await adapter.send_document(chat_id=100, document="file_id", caption="doc")
        call_data = api.request.call_args[0][1]
        assert call_data["caption"] == "doc"


class TestSendAudio:
    @pytest.mark.asyncio
    async def test_calls_sendAudio(self):
        adapter, api = make_adapter()
        await adapter.send_audio(chat_id=100, audio="file_id")
        api.request.assert_called_once_with("sendAudio", {"chat_id": 100, "audio": "file_id"})

    @pytest.mark.asyncio
    async def test_with_caption(self):
        adapter, api = make_adapter()
        await adapter.send_audio(chat_id=100, audio="file_id", caption="song")
        call_data = api.request.call_args[0][1]
        assert call_data["caption"] == "song"


class TestSendSticker:
    @pytest.mark.asyncio
    async def test_calls_sendSticker(self):
        adapter, api = make_adapter()
        await adapter.send_sticker(chat_id=100, sticker="file_id")
        api.request.assert_called_once_with("sendSticker", {"chat_id": 100, "sticker": "file_id"})


class TestSendAnimation:
    @pytest.mark.asyncio
    async def test_calls_sendAnimation(self):
        adapter, api = make_adapter()
        await adapter.send_animation(chat_id=100, animation="file_id")
        api.request.assert_called_once_with("sendAnimation", {"chat_id": 100, "animation": "file_id"})

    @pytest.mark.asyncio
    async def test_with_caption(self):
        adapter, api = make_adapter()
        await adapter.send_animation(chat_id=100, animation="file_id", caption="gif")
        call_data = api.request.call_args[0][1]
        assert call_data["caption"] == "gif"


class TestForwardMessage:
    @pytest.mark.asyncio
    async def test_calls_forwardMessage(self):
        adapter, api = make_adapter()
        await adapter.forward_message(chat_id=100, from_chat_id=200, message_id=5)
        api.request.assert_called_once_with("forwardMessage", {
            "chat_id": 100,
            "from_chat_id": 200,
            "message_id": 5,
        })


class TestCopyMessage:
    @pytest.mark.asyncio
    async def test_calls_copyMessage(self):
        adapter, api = make_adapter()
        await adapter.copy_message(chat_id=100, from_chat_id=200, message_id=5)
        api.request.assert_called_once_with("copyMessage", {
            "chat_id": 100,
            "from_chat_id": 200,
            "message_id": 5,
        })

    @pytest.mark.asyncio
    async def test_with_caption(self):
        adapter, api = make_adapter()
        await adapter.copy_message(chat_id=100, from_chat_id=200, message_id=5, caption="copy")
        call_data = api.request.call_args[0][1]
        assert call_data["caption"] == "copy"


class TestPinMessage:
    @pytest.mark.asyncio
    async def test_calls_pinChatMessage(self):
        adapter, api = make_adapter()
        await adapter.pin_message(chat_id=100, message_id=5)
        api.request.assert_called_once_with("pinChatMessage", {
            "chat_id": 100,
            "message_id": 5,
            "disable_notification": False,
        })

    @pytest.mark.asyncio
    async def test_disable_notification(self):
        adapter, api = make_adapter()
        await adapter.pin_message(chat_id=100, message_id=5, disable_notification=True)
        call_data = api.request.call_args[0][1]
        assert call_data["disable_notification"] is True


class TestUnpinMessage:
    @pytest.mark.asyncio
    async def test_calls_unpinChatMessage(self):
        adapter, api = make_adapter()
        await adapter.unpin_message(chat_id=100, message_id=5)
        api.request.assert_called_once_with("unpinChatMessage", {
            "chat_id": 100,
            "message_id": 5,
        })


class TestUnpinAllMessages:
    @pytest.mark.asyncio
    async def test_calls_unpinAllChatMessages(self):
        adapter, api = make_adapter()
        await adapter.unpin_all_messages(chat_id=100)
        api.request.assert_called_once_with("unpinAllChatMessages", {"chat_id": 100})


class TestGetChat:
    @pytest.mark.asyncio
    async def test_calls_getChat(self):
        adapter, api = make_adapter()
        await adapter.get_chat(chat_id=100)
        api.request.assert_called_once_with("getChat", {"chat_id": 100})


class TestGetChatMemberCount:
    @pytest.mark.asyncio
    async def test_calls_getChatMemberCount(self):
        adapter, api = make_adapter()
        await adapter.get_chat_member_count(chat_id=100)
        api.request.assert_called_once_with("getChatMemberCount", {"chat_id": 100})


class TestSetMyCommands:
    @pytest.mark.asyncio
    async def test_calls_setMyCommands(self):
        adapter, api = make_adapter()
        commands = [{"command": "start", "description": "Start"}]
        await adapter.set_my_commands(commands)
        api.request.assert_called_once_with("setMyCommands", {"commands": commands})


class TestDeleteMyCommands:
    @pytest.mark.asyncio
    async def test_calls_deleteMyCommands(self):
        adapter, api = make_adapter()
        await adapter.delete_my_commands()
        api.request.assert_called_once_with("deleteMyCommands", {})


class TestGetMyCommands:
    @pytest.mark.asyncio
    async def test_calls_getMyCommands(self):
        adapter, api = make_adapter()
        await adapter.get_my_commands()
        api.request.assert_called_once_with("getMyCommands", {})


class TestAdapterViaBotTelegram:
    @pytest.mark.asyncio
    async def test_bot_telegram_send_photo(self):
        bot = make_bot()
        await bot.telegram.send_photo(chat_id=100, photo="file_id")
        bot._api.request.assert_called_once_with("sendPhoto", {"chat_id": 100, "photo": "file_id"})

    @pytest.mark.asyncio
    async def test_bot_telegram_forward_message(self):
        bot = make_bot()
        await bot.telegram.forward_message(chat_id=100, from_chat_id=200, message_id=5)
        bot._api.request.assert_called_once_with("forwardMessage", {
            "chat_id": 100,
            "from_chat_id": 200,
            "message_id": 5,
        })

    @pytest.mark.asyncio
    async def test_bot_telegram_pin_message(self):
        bot = make_bot()
        await bot.telegram.pin_message(chat_id=100, message_id=5)
        bot._api.request.assert_called_once_with("pinChatMessage", {
            "chat_id": 100,
            "message_id": 5,
            "disable_notification": False,
        })
