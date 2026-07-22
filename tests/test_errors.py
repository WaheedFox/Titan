import pytest
from titan.errors import TitanError
from titan.telegram import TelegramError


class TestErrors:
    def test_titan_error_is_exception(self):
        with pytest.raises(TitanError):
            raise TitanError("something went wrong")

    def test_titan_error_message(self):
        err = TitanError("test message")
        assert str(err) == "test message"

    def test_telegram_error_is_titan_error(self):
        err = TelegramError("api error")
        assert isinstance(err, TitanError)
        assert isinstance(err, Exception)

    def test_telegram_error_can_be_caught_as_titan_error(self):
        with pytest.raises(TitanError):
            raise TelegramError("telegram failed")

    def test_telegram_error_message(self):
        err = TelegramError("bad token")
        assert str(err) == "bad token"
