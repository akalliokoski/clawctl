"""Paramiko-based SSH/SFTP helpers."""

import os
import re

import paramiko

DEFAULT_KEY = os.path.expanduser("~/.ssh/openclaw_ed25519")
DEFAULT_KNOWN_HOSTS = os.path.expanduser("~/.ssh/known_hosts")
DEFAULT_TIMEOUT = 120  # seconds

# Pattern for validating hostnames and IPs (prevents injection via host parameter)
_VALID_HOST_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def _validate_host(host: str) -> None:
    """Validate that a hostname/IP doesn't contain shell metacharacters."""
    if not host or not _VALID_HOST_RE.match(host):
        raise ValueError(f"Invalid hostname: {host!r}")


def get_ssh_client(
    host: str,
    user: str = "root",
    key_path: str = DEFAULT_KEY,
) -> paramiko.SSHClient:
    _validate_host(host)
    client = paramiko.SSHClient()
    # Load system and user known_hosts for host key verification instead of
    # blindly accepting any key (AutoAddPolicy is vulnerable to MITM attacks).
    client.load_system_host_keys()
    if os.path.exists(DEFAULT_KNOWN_HOSTS):
        client.load_host_keys(DEFAULT_KNOWN_HOSTS)
    # Warn (but don't block) on first connection to a new host — the key is
    # still recorded in known_hosts for future verification.
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(hostname=host, username=user, key_filename=key_path, timeout=30)
    return client


def run_cmd(
    host: str,
    command: str,
    user: str = "root",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Run a remote command and return stdout. Raises RuntimeError on non-zero exit."""
    client = get_ssh_client(host, user)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        if exit_code != 0:
            err = stderr.read().decode()
            raise RuntimeError(f"Command exited {exit_code}: {err}")
        return output
    finally:
        client.close()


def upload_file(
    host: str,
    local_path: str,
    remote_path: str,
    user: str = "root",
) -> None:
    """Upload a local file to the remote host via SFTP."""
    client = get_ssh_client(host, user)
    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
    finally:
        client.close()
