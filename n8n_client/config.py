"""Multi-client configuration management for n8n API credentials."""

import json
import subprocess
from pathlib import Path

KEYCHAIN_SERVICE = "n8n-claude-code"


def _keychain_set(account: str, password: str) -> None:
    """Store a password in macOS Keychain. Updates if already exists."""
    # Delete existing entry first (ignore errors if not found)
    subprocess.run(
        ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account],
        capture_output=True,
    )
    subprocess.run(
        [
            "security", "add-generic-password",
            "-s", KEYCHAIN_SERVICE,
            "-a", account,
            "-w", password,
        ],
        capture_output=True,
        check=True,
    )


def _keychain_get(account: str) -> str | None:
    """Retrieve a password from macOS Keychain. Returns None if not found."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _keychain_delete(account: str) -> None:
    """Delete a password from macOS Keychain. Ignores errors if not found."""
    subprocess.run(
        ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account],
        capture_output=True,
    )


class ConfigManager:
    def __init__(self, config_path: str | None = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).resolve().parent.parent / ".n8n_config.json"

    def _load(self) -> dict:
        if not self.config_path.exists():
            return {"clients": {}, "active_client": ""}
        with open(self.config_path) as f:
            return json.load(f)

    def _save(self, config: dict):
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _enrich_with_api_key(self, name: str, info: dict) -> dict:
        """Add api_key from Keychain to client info dict."""
        enriched = dict(info)
        api_key = _keychain_get(name)
        if not api_key:
            # Fallback: check if api_key is still in config (migration support)
            api_key = info.get("api_key", "")
        enriched["api_key"] = api_key
        return enriched

    def list_clients(self) -> dict[str, dict]:
        return self._load().get("clients", {})

    def get_active_client_name(self) -> str:
        return self._load().get("active_client", "")

    def get_active_client(self) -> tuple[str, dict] | None:
        config = self._load()
        name = config.get("active_client", "")
        if not name or name not in config.get("clients", {}):
            return None
        return name, self._enrich_with_api_key(name, config["clients"][name])

    def add_client(self, name: str, base_url: str, api_key: str, description: str = ""):
        _keychain_set(name, api_key)
        config = self._load()
        config.setdefault("clients", {})[name] = {
            "base_url": base_url.rstrip("/"),
            "description": description,
        }
        if not config.get("active_client"):
            config["active_client"] = name
        self._save(config)

    def remove_client(self, name: str):
        config = self._load()
        clients = config.get("clients", {})
        if name not in clients:
            raise KeyError(f"Client '{name}' not found")
        del clients[name]
        _keychain_delete(name)
        if config.get("active_client") == name:
            config["active_client"] = next(iter(clients), "")
        self._save(config)

    def switch_client(self, name: str):
        config = self._load()
        if name not in config.get("clients", {}):
            raise KeyError(f"Client '{name}' not found")
        config["active_client"] = name
        self._save(config)

    def get_client(self, name: str) -> tuple[str, dict]:
        """Get a specific client by name. Returns (name, info) or raises KeyError."""
        config = self._load()
        clients = config.get("clients", {})
        if name not in clients:
            raise KeyError(f"Client '{name}' not found")
        return name, self._enrich_with_api_key(name, clients[name])

    def has_config(self) -> bool:
        return self.config_path.exists() and bool(self._load().get("clients"))
