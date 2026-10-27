"""Disk cache for Elexon payloads."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


class DataCache:
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._fuelhh_path = self.cache_dir / "fuelhh_wind.json"
        self._windfor_path = self.cache_dir / "windfor.json"
        self._meta_path = self.cache_dir / "meta.json"

    def has_data(self) -> bool:
        return self._fuelhh_path.exists() and self._windfor_path.exists()

    def load_fuelhh(self) -> list[dict[str, Any]]:
        return self._read_json(self._fuelhh_path)

    def load_windfor(self) -> list[dict[str, Any]]:
        return self._read_json(self._windfor_path)

    def save(
        self,
        fuelhh: list[dict[str, Any]],
        windfor: list[dict[str, Any]],
    ) -> None:
        self._write_json(self._fuelhh_path, fuelhh)
        self._write_json(self._windfor_path, windfor)
        meta = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "fuelhh_count": len(fuelhh),
            "windfor_count": len(windfor),
        }
        self._write_json(self._meta_path, meta)
        logger.info(
            "cache saved",
            extra={"status": "ok"},
        )

    def meta(self) -> dict[str, Any]:
        if not self._meta_path.exists():
            return {
                "ready": False,
                "updated_at": None,
                "fuelhh_count": 0,
                "windfor_count": 0,
            }
        data = self._read_json(self._meta_path)
        if isinstance(data, list):
            return {"ready": False, "updated_at": None}
        return {
            "ready": self.has_data(),
            "updated_at": data.get("updated_at"),
            "fuelhh_count": data.get("fuelhh_count", 0),
            "windfor_count": data.get("windfor_count", 0),
        }

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f)
        tmp.replace(path)
