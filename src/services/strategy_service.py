"""策略服务 — 策略库管理，支持公式化定义"""

import json
from datetime import datetime
from pathlib import Path
from ..config import Config

STRATEGY_TEMPLATE = {
    "name": "",
    "version": "1.0",
    "created": "",
    "updated": "",
    "status": "开发中",
    "market_env": [],
    "entry_conditions": [],
    "exit_conditions": [],
    "stop_loss_pct": 8,
    "take_profit_pct": 20,
    "position_pct": 80,
    "notes": "",
}

INDICATOR_DEFS = {
    "ma": {"label": "移动均线", "params": ["period"], "example": "ma(5)", "desc": "收盘价的N日均线"},
    "ema": {"label": "指数均线", "params": ["period"], "example": "ema(12)", "desc": "指数加权移动均线"},
    "macd_dif": {"label": "MACD DIF", "params": [], "example": "macd_dif", "desc": "MACD快线(DIF)"},
    "macd_dea": {"label": "MACD DEA", "params": [], "example": "macd_dea", "desc": "MACD慢线(DEA)"},
    "rsi": {"label": "RSI", "params": ["period"], "example": "rsi(14)", "desc": "相对强弱指标"},
    "boll_upper": {"label": "布林上轨", "params": [], "example": "boll_upper", "desc": "布林带上轨(MA20+2σ)"},
    "boll_mid": {"label": "布林中轨", "params": [], "example": "boll_mid", "desc": "布林带中轨(MA20)"},
    "boll_lower": {"label": "布林下轨", "params": [], "example": "boll_lower", "desc": "布林带下轨(MA20-2σ)"},
    "close": {"label": "收盘价", "params": [], "example": "close", "desc": "当日收盘价"},
    "volume": {"label": "成交量", "params": [], "example": "volume", "desc": "当日成交量"},
    "vol_ma": {"label": "均量线", "params": ["period"], "example": "vol_ma(20)", "desc": "N日均量"},
    "atr": {"label": "ATR", "params": ["period"], "example": "atr(14)", "desc": "平均真实波幅"},
}

OPERATORS = [
    {"symbol": ">", "label": "大于"},
    {"symbol": "<", "label": "小于"},
    {"symbol": ">=", "label": "大于等于"},
    {"symbol": "<=", "label": "小于等于"},
    {"symbol": "==", "label": "等于"},
    {"symbol": "cross_above", "label": "上穿(金叉)"},
    {"symbol": "cross_below", "label": "下穿(死叉)"},
]

CONNECTORS = ["AND", "OR"]


def _strategy_dir() -> Path:
    return Path(Config.OBSIDIAN_VAULT_PATH) / "strategies"


def _filepath(name: str) -> Path:
    safe = (name or "").strip().replace("/", "_").replace("\\", "_")
    return _strategy_dir() / f"{safe}.json"


def list_strategies() -> list[dict]:
    """列出已有策略，返回摘要"""
    sd = _strategy_dir()
    if not sd.exists():
        return []
    result = []
    for f in sorted(sd.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix != ".json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "name": data.get("name", f.stem),
                "status": data.get("status", ""),
                "updated": data.get("updated", ""),
                "condition_count": len(data.get("entry_conditions", [])) + len(data.get("exit_conditions", [])),
            })
        except (json.JSONDecodeError, Exception):
            pass
    return result


def get_strategy(name: str) -> dict | None:
    """获取策略完整内容"""
    fp = _filepath(name)
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        data["exists"] = True
        return data
    except Exception:
        return None


def create_strategy(name: str) -> dict | None:
    """创建新策略"""
    safe_name = (name or "").strip()
    if not safe_name:
        return None
    fp = _filepath(safe_name)
    if fp.exists():
        return {"name": safe_name, "created": False, "error": "策略已存在"}
    today = datetime.now().strftime("%Y-%m-%d")
    data = dict(STRATEGY_TEMPLATE)
    data["name"] = safe_name
    data["created"] = today
    data["updated"] = today
    _strategy_dir().mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    data["exists"] = True
    return data


def update_strategy(name: str, updates: dict) -> dict | None:
    """更新策略（保存公式编辑结果）"""
    fp = _filepath(name)
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None
    allowed = {"entry_conditions", "exit_conditions", "stop_loss_pct", "take_profit_pct",
               "position_pct", "status", "market_env", "notes", "name"}
    for key, val in updates.items():
        if key in allowed and key in data:
            data[key] = val
    data["updated"] = datetime.now().strftime("%Y-%m-%d")
    # 改名时移动文件
    new_name = data.get("name", name)
    if new_name != name:
        new_fp = _filepath(new_name)
        fp.rename(new_fp)
        fp = new_fp
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    data["exists"] = True
    return data


def delete_strategy(name: str) -> bool:
    """删除策略"""
    fp = _filepath(name)
    if not fp.exists():
        return False
    fp.unlink()
    return True


def get_indicator_reference() -> dict:
    """返回可用指标和操作符参考"""
    return {
        "indicators": INDICATOR_DEFS,
        "operators": OPERATORS,
        "connectors": CONNECTORS,
    }
