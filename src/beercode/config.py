from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_FILENAME = "beercode.yaml"


@dataclass(frozen=True)
class Provider:
    name: str
    protocol: str
    model: str
    api_key: str
    base_url: str | None = None


def load_providers(directory: Path) -> list[Provider]:
    data = yaml.safe_load((Path(directory) / CONFIG_FILENAME).read_text(encoding="utf-8"))
    return [
        Provider(
            name=str(item["name"]),
            protocol=str(item["protocol"]),
            model=str(item["model"]),
            api_key=str(item["api_key"]),
            base_url=item.get("base_url"),
        )
        for item in data["providers"]
    ]
