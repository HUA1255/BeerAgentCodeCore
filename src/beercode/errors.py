from __future__ import annotations

import anthropic
import httpx2
import openai


class RequestFailed(Exception):
    pass


class IncompleteReply(Exception):
    pass


STATUS_MESSAGES = {
    401: "鉴权失败（401）：请检查供应商的 api_key 是否正确",
    403: "无权访问（403）：请检查供应商的 api_key 权限",
    404: "模型或接口不存在（404）：请检查 model 与 base_url 配置",
    429: "请求过于频繁或额度不足（429）：请稍后再试",
}

DISCONNECTED = "连接中途断开：本轮回复不完整，已丢弃，请重试"
UNREACHABLE = "网络连接失败：无法连接到模型服务，请检查网络或 base_url"
TIMED_OUT = "请求超时：模型服务长时间无响应，请稍后再试"

TIMEOUTS = (openai.APITimeoutError, anthropic.APITimeoutError, httpx2.TimeoutException)
CONNECTION_ERRORS = (openai.APIConnectionError, anthropic.APIConnectionError)


def describe(error: BaseException) -> str:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return STATUS_MESSAGES.get(status) or (f"服务端错误（{status}）：模型服务暂时不可用，请稍后再试" if status >= 500 else f"请求失败（{status}）")
    if isinstance(error, TIMEOUTS):
        return TIMED_OUT
    if isinstance(error, CONNECTION_ERRORS):
        return UNREACHABLE
    if isinstance(error, (IncompleteReply, httpx2.TransportError)):
        return DISCONNECTED
    return f"请求失败：{type(error).__name__}"
