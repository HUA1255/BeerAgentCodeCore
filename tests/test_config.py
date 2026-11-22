import re
import subprocess
from pathlib import Path

import pytest
import yaml

from beercode.config import ConfigError, Provider, load_providers

CONFIG = """\
providers:
  - name: OpenCode Go
    protocol: openai
    model: deepseek-v4.1-flash
    base_url: https://opencode.ai/inference/go/openai/v1
    api_key: sk-first
  - name: Other
    protocol: openai
    model: other-model
    api_key: sk-second
"""


def test_providers_are_read_from_beercode_yaml_in_order(tmp_path):
    (tmp_path / "beercode.yaml").write_text(CONFIG, encoding="utf-8")

    providers = load_providers(tmp_path)

    assert providers == [
        Provider(
            name="OpenCode Go",
            protocol="openai",
            model="deepseek-v4.1-flash",
            base_url="https://opencode.ai/inference/go/openai/v1",
            api_key="sk-first",
        ),
        Provider(name="Other", protocol="openai", model="other-model", api_key="sk-second", base_url=None),
    ]


def test_missing_config_file_suggests_copying_example(tmp_path):
    with pytest.raises(ConfigError) as error:
        load_providers(tmp_path)

    assert "beercode.yaml" in str(error.value)
    assert "beercode.example.yaml" in str(error.value)


def write(tmp_path, text):
    (tmp_path / "beercode.yaml").write_text(text, encoding="utf-8")


def test_malformed_yaml_is_reported_with_location(tmp_path):
    write(tmp_path, "providers:\n  - name: a\n   bad: : x\n")

    with pytest.raises(ConfigError) as error:
        load_providers(tmp_path)

    assert "YAML" in str(error.value)
    assert "第 3 行" in str(error.value)


FULL = {"name": "Alpha", "protocol": "openai", "model": "m1", "api_key": "sk-alpha"}


def write_providers(tmp_path, *providers):
    write(tmp_path, yaml.safe_dump({"providers": list(providers)}, allow_unicode=True))


@pytest.mark.parametrize("field", ["name", "protocol", "model", "api_key"])
def test_missing_required_field_names_provider_and_field(tmp_path, field):
    broken = {k: v for k, v in FULL.items() if k != field}
    write_providers(tmp_path, FULL, broken)

    with pytest.raises(ConfigError) as error:
        load_providers(tmp_path)

    assert "第 2 个供应商" in str(error.value)
    assert f"`{field}`" in str(error.value)
    assert "缺少" in str(error.value)


def test_unknown_protocol_is_rejected_with_allowed_values(tmp_path):
    write_providers(tmp_path, {**FULL, "protocol": "gemini"})

    with pytest.raises(ConfigError) as error:
        load_providers(tmp_path)

    message = str(error.value)
    assert "第 1 个供应商" in message and "protocol" in message
    assert "gemini" in message and "anthropic" in message and "openai" in message


@pytest.mark.parametrize(
    "text",
    ["", "providers: []\n", "providers: hello\n", "other: 1\n", "- a\n", "providers:\n  - just-a-string\n"],
)
def test_config_without_a_usable_provider_list_is_rejected(tmp_path, text):
    write(tmp_path, text)

    with pytest.raises(ConfigError) as error:
        load_providers(tmp_path)

    assert "providers" in str(error.value) or "供应商" in str(error.value)


def test_api_key_can_reference_an_environment_variable(tmp_path):
    write_providers(tmp_path, {**FULL, "api_key": "${ALPHA_KEY}"})

    providers = load_providers(tmp_path, env={"ALPHA_KEY": "sk-from-env"})

    assert providers[0].api_key == "sk-from-env"


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_NAMES = re.compile(r"^\s*api_key:\s*\$\{(\w+)\}", re.MULTILINE)


def test_example_config_is_valid_and_lists_three_recommended_providers(tmp_path):
    example = (REPO_ROOT / "beercode.example.yaml").read_text(encoding="utf-8")
    write(tmp_path, example)
    env = {name: f"value-of-{name}" for name in ENV_NAMES.findall(example)}

    providers = load_providers(tmp_path, env=env)

    assert len(providers) == 3
    assert providers[0] == Provider(
        name=providers[0].name,
        protocol="openai",
        model="deepseek-v4.1-flash",
        base_url="https://opencode.ai/inference/go/openai/v1",
        api_key="value-of-OPENCODE_API_KEY",
    )
    assert "OpenCode Go" in providers[0].name
    assert providers[1].protocol == "openai" and providers[1].base_url
    assert providers[2].protocol == "anthropic"
    assert "Settings › Privacy › Regions" in example and "Global" in example
    assert "curl https://opencode.ai/inference/go/v1/models" in example


def test_real_config_is_ignored_by_git():
    result = subprocess.run(["git", "check-ignore", "-q", "beercode.yaml"], cwd=REPO_ROOT)

    assert result.returncode == 0


def test_unset_environment_variable_is_named_in_the_error(tmp_path):
    write_providers(tmp_path, FULL, {**FULL, "name": "Beta", "api_key": "${BETA_KEY}"})

    with pytest.raises(ConfigError) as error:
        load_providers(tmp_path, env={})

    message = str(error.value)
    assert "BETA_KEY" in message and "第 2 个供应商" in message and "api_key" in message
