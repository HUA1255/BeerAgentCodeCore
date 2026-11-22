from beercode.config import Provider, load_providers

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
