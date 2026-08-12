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

    def test_telegram_error_retry_after_defaults_to_none(self):
        err = TelegramError("some error")
        assert err.retry_after is None

    def test_telegram_error_retry_after_set_when_provided(self):
        err = TelegramError("Too Many Requests: retry after 30", retry_after=30)
        assert err.retry_after == 30

    def test_telegram_error_retry_after_does_not_affect_message(self):
        msg = "Too Many Requests: retry after 30"
        err = TelegramError(msg, retry_after=30)
        assert str(err) == msg

    def test_telegram_error_with_retry_after_is_still_titan_error(self):
        err = TelegramError("rate limited", retry_after=15)
        assert isinstance(err, TitanError)
