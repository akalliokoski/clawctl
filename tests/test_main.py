"""Tests for CLI entry point."""

from typer.testing import CliRunner

from clawctl.main import app

runner = CliRunner()


def test_app_help() -> None:
    """The CLI should show help text with all four command groups."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "server" in result.output
    assert "deploy" in result.output
    assert "status" in result.output
    assert "tunnel" in result.output


def test_server_help() -> None:
    result = runner.invoke(app, ["server", "--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "destroy" in result.output


def test_deploy_help() -> None:
    result = runner.invoke(app, ["deploy", "--help"])
    assert result.exit_code == 0
    assert "push" in result.output
    assert "logs" in result.output


def test_status_help() -> None:
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    assert "check" in result.output
    assert "doctor" in result.output


def test_tunnel_help() -> None:
    result = runner.invoke(app, ["tunnel", "--help"])
    assert result.exit_code == 0
    assert "open" in result.output
    assert "ssh" in result.output
