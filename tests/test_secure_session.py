"""Tests for token storage precedence in secure_session."""

from unittest.mock import MagicMock, patch

import pytest

from monarch_mcp_server import secure_session as ss
from monarch_mcp_server.secure_session import TOKEN_ENV_VAR, SecureMonarchSession


@pytest.fixture
def session(tmp_path, monkeypatch):
    """A session with no keyring backend and an isolated file fallback."""
    monkeypatch.setattr(ss, "_TOKEN_DIR", tmp_path / ".monarch-mcp-server")
    monkeypatch.setattr(ss, "_TOKEN_FILE", tmp_path / ".monarch-mcp-server" / "token")
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    with patch.object(ss, "_keyring_available", return_value=False):
        yield SecureMonarchSession()


@pytest.fixture(autouse=True)
def no_legacy_cleanup():
    """Keep tests away from the real home directory."""
    with patch.object(SecureMonarchSession, "_cleanup_old_session_files"):
        yield


class TestEnvTokenPrecedence:
    def test_env_token_is_loaded(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        assert session.load_token() == "env-token"

    def test_env_token_beats_stored_token(self, session, monkeypatch):
        session.save_token("stored-token")
        assert session.load_token() == "stored-token"

        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        assert session.load_token() == "env-token"

    def test_env_token_is_stripped(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "  padded-token\n")
        assert session.load_token() == "padded-token"

    @pytest.mark.parametrize("value", ["", "   ", "\n\t "])
    def test_blank_env_token_falls_through_to_storage(
        self, session, monkeypatch, value
    ):
        session.save_token("stored-token")
        monkeypatch.setenv(TOKEN_ENV_VAR, value)
        assert session.load_token() == "stored-token"

    def test_no_token_anywhere_returns_none(self, session):
        assert session.load_token() is None

    def test_env_token_builds_client(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        fake_cls = MagicMock()
        with patch.object(ss, "MonarchMoney", fake_cls):
            client = session.get_authenticated_client()
        fake_cls.assert_called_once_with(token="env-token")
        assert client is fake_cls.return_value


class TestEnvTokenPresent:
    def test_false_when_unset(self, session):
        assert session.env_token_present() is False

    def test_false_when_blank(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "   ")
        assert session.env_token_present() is False

    def test_true_when_set(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        assert session.env_token_present() is True


class TestTokenSource:
    def test_none_when_no_token(self, session):
        assert session.token_source() is None

    def test_reports_env(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        assert session.token_source() == f"${TOKEN_ENV_VAR}"

    def test_reports_file_fallback(self, session):
        session.save_token("stored-token")
        assert session.token_source() == "file"

    def test_reports_keyring(self, session, monkeypatch):
        session._use_keyring = True
        fake_keyring = MagicMock()
        fake_keyring.get_password.return_value = "keyring-token"
        monkeypatch.setitem(__import__("sys").modules, "keyring", fake_keyring)
        assert session.token_source() == "keyring"

    def test_never_returns_the_token_itself(self, session, monkeypatch):
        monkeypatch.setenv(TOKEN_ENV_VAR, "super-secret-token")
        assert "super-secret-token" not in session.token_source()


class TestDeleteTokenWithEnvSet:
    def test_clears_storage_but_warns_env_still_active(
        self, session, monkeypatch, caplog
    ):
        session.save_token("stored-token")
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")

        with caplog.at_level("WARNING"):
            session.delete_token()

        assert TOKEN_ENV_VAR in caplog.text
        # Storage is cleared, but the env var still authenticates.
        assert session.load_token() == "env-token"
        monkeypatch.delenv(TOKEN_ENV_VAR)
        assert session.load_token() is None

    def test_no_warning_when_env_unset(self, session, caplog):
        session.save_token("stored-token")
        with caplog.at_level("WARNING"):
            session.delete_token()
        assert TOKEN_ENV_VAR not in caplog.text
        assert session.load_token() is None


class TestSaveTokenWithEnvSet:
    def test_warns_that_saved_token_is_shadowed(self, session, monkeypatch, caplog):
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        with caplog.at_level("WARNING"):
            session.save_token("stored-token")
        assert TOKEN_ENV_VAR in caplog.text
        # Saved, but dormant while the env var is set.
        assert session.load_token() == "env-token"
        monkeypatch.delenv(TOKEN_ENV_VAR)
        assert session.load_token() == "stored-token"
