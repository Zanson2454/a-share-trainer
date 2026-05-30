"""
消息推送 — 钉钉/企业微信/个人微信
"""
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from .config import Config


class DingTalkBot:
    """钉钉机器人消息推送"""

    @staticmethod
    def _sign() -> tuple:
        """生成钉钉签名"""
        timestamp = str(round(time.time() * 1000))
        secret = Config.DINGTALK_SECRET
        if not secret:
            return timestamp, ""
        string_to_sign = timestamp + "\n" + secret
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    @classmethod
    def send_markdown(cls, title: str, text: str) -> bool:
        """发送 Markdown 消息到钉钉"""
        if not Config.has_dingtalk():
            print("[钉钉] 未配置 Webhook，跳过发送")
            return False
        webhook = Config.DINGTALK_WEBHOOK_URL
        timestamp, sign = cls._sign()
        if sign:
            webhook = webhook + "&timestamp=" + timestamp + "&sign=" + sign
        payload = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        }
        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            result = resp.json()
            if result.get("errcode") == 0:
                print("[钉钉] 发送成功")
                return True
            else:
                print("[钉钉] 发送失败: " + str(result))
                return False
        except Exception as e:
            print("[钉钉] 发送异常: " + str(e))
            return False

    @classmethod
    def send_text(cls, content: str) -> bool:
        """发送纯文本消息"""
        if not Config.has_dingtalk():
            return False
        webhook = Config.DINGTALK_WEBHOOK_URL
        timestamp, sign = cls._sign()
        if sign:
            webhook = webhook + "&timestamp=" + timestamp + "&sign=" + sign
        payload = {"msgtype": "text", "text": {"content": content}}
        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            return resp.json().get("errcode") == 0
        except Exception as e:
            print("[钉钉] 发送异常: " + str(e))
            return False


class WeComBot:
    """企业微信机器人（预留）"""

    @staticmethod
    def send_markdown(content: str) -> bool:
        if not Config.has_wecom():
            print("[企业微信] 未配置 Webhook，跳过发送")
            return False
        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        try:
            resp = requests.post(Config.WECOM_WEBHOOK_URL, json=payload, timeout=10)
            return resp.json().get("errcode") == 0
        except Exception as e:
            print("[企业微信] 发送异常: " + str(e))
            return False


class MessageBus:
    """消息总线 — 同时推送到多个渠道"""

    @staticmethod
    def broadcast_markdown(title: str, text: str):
        """推送到所有已配置渠道"""
        DingTalkBot.send_markdown(title, text)
        WeComBot.send_markdown(text)

    @staticmethod
    def status() -> str:
        """返回渠道配置状态"""
        lines = ["## 消息渠道状态"]
        dingtalk_status = "✅ 已配置" if Config.has_dingtalk() else "❌ 未配置（设置 DINGTALK_WEBHOOK_URL）"
        wecom_status = "✅ 已配置" if Config.has_wecom() else "❌ 未配置（设置 WECOM_WEBHOOK_URL）"
        lines.append("- 钉钉: " + dingtalk_status)
        lines.append("- 企业微信: " + wecom_status)
        return "\n".join(lines)
