"""Tests for SSH utility functions."""

import pytest

from clawctl.ssh_utils import _validate_host


class TestValidateHost:
    """Test hostname validation to prevent command injection."""

    def test_valid_hostname(self) -> None:
        _validate_host("openclaw-vps")

    def test_valid_ip(self) -> None:
        _validate_host("192.168.1.1")

    def test_valid_fqdn(self) -> None:
        _validate_host("my-server.tail1234.ts.net")

    def test_empty_host_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("")

    def test_semicolon_injection_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("host; rm -rf /")

    def test_backtick_injection_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("`whoami`")

    def test_pipe_injection_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("host | cat /etc/passwd")

    def test_dollar_injection_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("$(whoami)")

    def test_space_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("host name")

    def test_ampersand_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid hostname"):
            _validate_host("host&cmd")
