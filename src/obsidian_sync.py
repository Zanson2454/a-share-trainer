"""
Obsidian 同步 — 将生成内容写入 A股训练场 Vault
"""
from datetime import datetime
from pathlib import Path
from .config import Config


class ObsidianSync:
    """Obsidian Vault 双向同步"""

    VAULT_PATH = Path(Config.OBSIDIAN_VAULT_PATH)

    @classmethod
    def ensure_dir(cls, subpath: str) -> Path:
        """确保目录存在"""
        p = cls.VAULT_PATH / subpath
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def save_note(cls, directory: str, filename: str, content: str) -> str:
        """保存笔记到 Vault，返回完整文件路径"""
        d = cls.ensure_dir(directory)
        filepath = d / filename
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    @classmethod
    def save_daily_learning(cls, topic: str, content: str, questions: list) -> str:
        """保存每日学习笔记"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = today + "_" + topic + ".md"
        parts = [
            "---",
            "date: " + today,
            "topic: " + topic,
            "category: 学习",
            "tags: [学习, A股]",
            "---",
            "",
            content,
            "",
            "## 教练提问",
        ]
        for i, q in enumerate(questions, 1):
            parts.append("")
            parts.append(str(i) + ". " + q)
        full = "\n".join(parts)
        return cls.save_note("01_学习", filename, full)

    @classmethod
    def save_stock_analysis(cls, code: str, name: str, content: str) -> str:
        """保存个股分析"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = today + "_" + code + "_" + name + ".md"
        parts = [
            "---",
            "date: " + today,
            "code: " + code,
            "name: " + name,
            "status: 观察中",
            "---",
            "",
            content,
        ]
        return cls.save_note("04_个股", filename, "\n".join(parts))

    @classmethod
    def save_review(cls, content: str) -> str:
        """保存每日复盘"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = "复盘_" + today + ".md"
        parts = [
            "---",
            "date: " + today,
            "market_env: 待确认",
            "---",
            "",
            content,
        ]
        return cls.save_note("06_复盘", filename, "\n".join(parts))

    @classmethod
    def save_strategy(cls, name: str, content: str) -> str:
        """保存策略"""
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("无效的策略名称")
        filename = name + ".md"
        return cls.save_note("05_策略", filename, content)

    @classmethod
    def save_backtest(cls, strategy_name: str, content: str) -> str:
        """保存回测报告"""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = today + "_" + strategy_name + "_回测.md"
        return cls.save_note("07_回测", filename, content)
