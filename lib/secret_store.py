"""
SecretStore — per-plugin encrypted secret management.

Secrets are stored at:  ~/.config/zeroclaw/plugins/<plugin>/secrets.toml
Encryption key at:      ~/.config/zeroclaw/.key  (chmod 600)

On-disk format:
    whoop_client_id = "ENC:v1:<fernet_token>"
    token_expires_at = "2026-05-01T00:00:00Z"   # plaintext OK for non-secrets

Plugin code reads secrets via the convenience wrapper:
    from secret_store import zc_secret_get
    client_id = zc_secret_get("whoop", "whoop_client_id")
"""

import os
import stat
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        sys.exit("tomllib not available. Python >=3.11 has it built-in, or: pip install tomli")

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    sys.exit(
        "cryptography package not found.\n"
        "Install with: pip install cryptography"
    )

_CONFIG_ROOT = Path.home() / ".config" / "zeroclaw"
_KEY_FILE = _CONFIG_ROOT / ".key"
_PLUGINS_DIR = _CONFIG_ROOT / "plugins"
_ENC_PREFIX = "ENC:v1:"


class SecretStore:
    """Encrypt/decrypt secrets for a single plugin."""

    def __init__(self, plugin_name: str) -> None:
        self.plugin_name = plugin_name
        self.secrets_path = _PLUGINS_DIR / plugin_name / "secrets.toml"
        self._fernet = Fernet(self._load_or_create_key())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """Return an ENC:v1:... ciphertext string."""
        token = self._fernet.encrypt(plaintext.encode())
        return _ENC_PREFIX + token.decode()

    def decrypt(self, value: str) -> str:
        """Decrypt an ENC:v1:... value. Returns plaintext values unchanged."""
        if not value.startswith(_ENC_PREFIX):
            return value  # stored plaintext (e.g. token_expires_at)
        token = value[len(_ENC_PREFIX):].encode()
        try:
            return self._fernet.decrypt(token).decode()
        except InvalidToken:
            sys.exit(
                "Failed to decrypt a secret — key mismatch or corrupted value.\n"
                f"  plugin:  {self.plugin_name}\n"
                f"  keyfile: {_KEY_FILE}\n"
                "If you rotated the key, re-set secrets with: "
                "python scripts/plugin_secrets.py set <plugin> <key>"
            )

    def set(self, key: str, value: str, encrypt: bool = True) -> None:
        """Encrypt (unless encrypt=False) and persist a secret."""
        secrets = self._read_raw()
        secrets[key] = self.encrypt(value) if encrypt else value
        self._write_raw(secrets)

    def get(self, key: str) -> str:
        """Read and decrypt a secret. Exits with a helpful message if missing."""
        secrets = self._read_raw()
        if key not in secrets:
            sys.exit(
                f"Secret '{key}' not found for plugin '{self.plugin_name}'.\n"
                f"Set it with: python scripts/plugin_secrets.py set {self.plugin_name} {key}"
            )
        return self.decrypt(secrets[key])

    def list_keys(self) -> list[str]:
        """Return all stored key names (values are not exposed)."""
        return list(self._read_raw().keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_or_create_key(self) -> bytes:
        if _KEY_FILE.exists():
            key = _KEY_FILE.read_bytes().strip()
            if len(key) != 44:  # Fernet keys are 44 base64 chars
                sys.exit(f"Key file at {_KEY_FILE} looks corrupted. Delete it and re-set secrets.")
            return key

        _CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        _KEY_FILE.write_bytes(key)
        _restrict_file(_KEY_FILE)
        return key

    def _read_raw(self) -> dict:
        if not self.secrets_path.exists():
            return {}
        with open(self.secrets_path, "rb") as f:
            return tomllib.load(f)

    def _write_raw(self, secrets: dict) -> None:
        self.secrets_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# ZeroWhoop plugin secrets — managed by secret_store.py, do not edit manually\n"]
        for k, v in secrets.items():
            # Escape any double quotes in the value (shouldn't happen with Fernet, but safe)
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k} = "{escaped}"\n')
        self.secrets_path.write_text("".join(lines), encoding="utf-8")
        _restrict_file(self.secrets_path)


def _restrict_file(path: Path) -> None:
    """Best-effort chmod 600 (owner read/write only)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except (OSError, NotImplementedError):
        pass  # Windows has limited chmod support; silently skip


def zc_secret_get(plugin_name: str, key: str) -> str:
    """
    Convenience wrapper for plugin code.

    Usage:
        from secret_store import zc_secret_get
        token = zc_secret_get("whoop", "whoop_access_token")
    """
    return SecretStore(plugin_name).get(key)
