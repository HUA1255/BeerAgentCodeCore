from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_FILENAME = "beercode.yaml"
EXAMPLE_FILENAME = "beercode.example.yaml"
REQUIRED_FIELDS = ("name", "protocol", "model", "api_key")
ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    protocol: str
    model: str
    api_key: str
    base_url: str | None = None


def load_providers(directory: Path, env: Mapping[str, str] | None = None) -> list[Provider]:
    env = os.environ if env is None else env
    data = _read_yaml(Path(directory) / CONFIG_FILENAME)
    items = data.get("providers") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ConfigError(f"{CONFIG_FILENAME} 需要一个非空的 `providers` 列表，每项描述一个供应商。可参考 {EXAMPLE_FILENAME}。")
    return [_parse_provider(index, item, env) for index, item in enumerate(items, start=1)]


def _read_yaml(path: Path) -> object:
    if not path.is_file():
        raise ConfigError(f"未找到配置文件 {CONFIG_FILENAME}（{path}）。可复制 {EXAMPLE_FILENAME} 为 {CONFIG_FILENAME} 后按需修改。")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        where = f"第 {mark.line + 1} 行第 {mark.column + 1} 列" if mark else "未知位置"
        raise ConfigError(f"{CONFIG_FILENAME} 不是合法的 YAML（{where}）：{getattr(error, 'problem', None) or error}") from None


def _parse_provider(index: int, item: object, env: Mapping[str, str]) -> Provider:
    label = f"第 {index} 个供应商"
    if not isinstance(item, dict):
        raise ConfigError(f"{CONFIG_FILENAME} 中 `providers` 的{label}应为包含 name、protocol、model、api_key 等字段的映射。")
    for field in REQUIRED_FIELDS:
        if item.get(field) in (None, ""):
            raise ConfigError(f"{CONFIG_FILENAME} 中{label}缺少必填字段 `{field}`。")
    protocol = str(item["protocol"])
    from beercode.protocols import FACTORIES

    if protocol not in FACTORIES:
        allowed = "、".join(sorted(FACTORIES))
        raise ConfigError(f"{CONFIG_FILENAME} 中{label}（{item['name']}）的 `protocol` 为 {protocol!r}，仅支持 {allowed}。")
    return Provider(
        name=str(item["name"]),
        protocol=protocol,
        model=str(item["model"]),
        api_key=_resolve_api_key(str(item["api_key"]), label, env),
        base_url=item.get("base_url"),
    )


def _resolve_api_key(raw: str, label: str, env: Mapping[str, str]) -> str:
    reference = ENV_REFERENCE.fullmatch(raw.strip())
    if reference is None:
        return raw
    variable = reference.group(1)
    value = env.get(variable)
    if not value:
        raise ConfigError(f"{CONFIG_FILENAME} 中{label}的 `api_key` 引用了环境变量 {variable}，但该变量未设置或为空。")
    return value
