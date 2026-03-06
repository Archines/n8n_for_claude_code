"""Multi-client configuration management for n8n API credentials."""

import json
import os
from pathlib import Path


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

    def list_clients(self) -> dict[str, dict]:
        return self._load().get("clients", {})

    def get_active_client_name(self) -> str:
        return self._load().get("active_client", "")

    def get_active_client(self) -> tuple[str, dict] | None:
        config = self._load()
        name = config.get("active_client", "")
        if not name or name not in config.get("clients", {}):
            return None
        return name, config["clients"][name]

    def add_client(self, name: str, base_url: str, api_key: str, description: str = ""):
        config = self._load()
        config.setdefault("clients", {})[name] = {
            "base_url": base_url.rstrip("/"),
            "api_key": api_key,
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
        return name, clients[name]

    def has_config(self) -> bool:
        return self.config_path.exists() and bool(self._load().get("clients"))
