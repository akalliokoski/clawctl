"""Paramiko-based SSH/SFTP helpers."""

import os

import paramiko

DEFAULT_KEY = os.path.expanduser("~/.ssh/openclaw_ed25519")


def get_ssh_client(
    host: str,
    user: str = "root",
    key_path: str = DEFAULT_KEY,
) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, key_filename=key_path, timeout=30)
    return client


def run_cmd(host: str, command: str, user: str = "root") -> str:
    """Run a remote command and return stdout. Raises RuntimeError on non-zero exit."""
    client = get_ssh_client(host, user)
    try:
        _, stdout, stderr = client.exec_command(command)
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
