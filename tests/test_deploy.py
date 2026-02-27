"""Tests for deploy module input validation."""

from clawctl.deploy import _VALID_CHANNEL_RE, _VALID_CODE_RE


class TestChannelValidation:
    """Test channel name regex to prevent command injection."""

    def test_valid_channels(self) -> None:
        for ch in ["telegram", "discord", "slack", "matrix-bridge"]:
            assert _VALID_CHANNEL_RE.match(ch), f"Should accept: {ch}"

    def test_rejects_injection(self) -> None:
        for bad in ["; rm -rf /", "$(cmd)", "`cmd`", "a" * 50, "", "1bad", "UPPER"]:
            assert not _VALID_CHANNEL_RE.match(bad), f"Should reject: {bad}"


class TestCodeValidation:
    """Test pairing code regex to prevent command injection."""

    def test_valid_codes(self) -> None:
        for code in ["abc123", "a1b2c3d4e5", "ABCDEF", "test-code_1"]:
            assert _VALID_CODE_RE.match(code), f"Should accept: {code}"

    def test_rejects_injection(self) -> None:
        for bad in ["; rm -rf /", "$(cmd)", "`cmd`", "", "a b c", "x" * 200]:
            assert not _VALID_CODE_RE.match(bad), f"Should reject: {bad}"
