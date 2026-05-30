"""
A股训练系统 — 配置管理
加载 .env 环境变量，提供统一配置入口
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """全局配置单例"""

    # --- 数据源 ---
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

    # --- 消息推送 ---
    DINGTALK_WEBHOOK_URL = os.getenv("DINGTALK_WEBHOOK_URL", "")
    DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "")
    WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "")
    WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")

    # --- Obsidian ---
    OBSIDIAN_VAULT_PATH = os.getenv(
        "OBSIDIAN_VAULT_PATH",
        str(Path.home() / "Documents/obsidian/A股训练场")
    )

    # --- 风控 ---
    SIMULATED_CAPITAL = float(os.getenv("SIMULATED_CAPITAL", "100000"))
    MAX_SINGLE_POSITION = float(os.getenv("MAX_SINGLE_POSITION", "0.3"))
    MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))

    # --- 调试 ---
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> list[str]:
        """检查必要配置是否完整，返回缺失项列表"""
        missing = []
        # 数据源至少有一个可用
        # AKShare 无需配置，Tushare 可选
        return missing

    @classmethod
    def has_dingtalk(cls) -> bool:
        """钉钉是否已配置"""
        return bool(cls.DINGTALK_WEBHOOK_URL)

    @classmethod
    def has_wecom(cls) -> bool:
        """企业微信是否已配置"""
        return bool(cls.WECOM_WEBHOOK_URL)
