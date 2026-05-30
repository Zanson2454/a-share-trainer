"""复盘服务 — 每日自动复盘 + 操作复盘"""

import json
from datetime import datetime
from pathlib import Path
from ..config import Config
from ..data.akshare_client import AKShareClient


def _ops_dir() -> Path:
    return Path(Config.OBSIDIAN_VAULT_PATH) / "operations"


# ═══════════════════════════════════════════
# 每日自动复盘
# ═══════════════════════════════════════════

def get_review_template() -> dict:
    """生成每日复盘模板，自动填入当日的市场数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    index_info = ""
    sector_info = ""

    try:
        sh_df = AKShareClient.get_index_data("000001")
        if sh_df is not None and not sh_df.empty:
            latest = sh_df.iloc[-1]
            prev = sh_df.iloc[-2] if len(sh_df) > 1 else latest
            chg = (latest["close"] - prev["close"]) / prev["close"] * 100 if prev["close"] else 0
            vol = latest.get("volume", 0)
            avg_vol = sh_df["volume"].tail(20).mean()
            ratio = vol / avg_vol if avg_vol else 1
            trend = "上涨" if chg > 0 else "下跌"
            index_info = (
                f"上证指数 {latest['close']:.2f}（{trend}{abs(chg):.2f}%），"
                f"成交量{'放大' if ratio > 1.2 else '萎缩' if ratio < 0.8 else '持平'}"
            )
    except Exception:
        index_info = "（数据获取失败）"

    try:
        sectors = AKShareClient.get_hot_sectors()
        if sectors:
            top3 = sectors[:3]
            sector_info = "、".join(f"{s['name']}({s['change']:+.2f}%)" for s in top3)
    except Exception:
        sector_info = "（数据获取失败）"

    content = f"""## 每日复盘 — {today}

### 一、今日大盘
{index_info}

**热点板块**: {sector_info}

### 二、大盘判断复盘

| 判断项 | 盘前判断 | 实际结果 | 对/错 | 原因分析 |
|--------|----------|----------|-------|----------|
| 大盘方向 | | | | |
| 主线板块 | | | | |
| 风险事件 | | | | |

### 三、候选股表现

| 代码 | 名称 | 今日涨跌 | 是否符合预期 | 后续操作 |
|------|------|----------|--------------|----------|
| | | | | |

### 四、假设验证

**我原来的假设是什么？**
>

**验证结果**
- 有效的信号:
- 噪音/失效的信号:

### 五、今日关键教训

>

---

### 复盘检查清单

- [ ] 今天是否按计划执行了？
- [ ] 止损/止盈纪律有没有执行？
- [ ] 有没有因为情绪改变了原定计划？
- [ ] 今天的交易中，哪个决策最值得肯定？
- [ ] 今天的交易中，哪个决策最需要改进？

> 仅用于学习研究，不构成投资建议
"""
    return {"date": today, "content": content, "index_info": index_info, "sector_info": sector_info}


# ═══════════════════════════════════════════
# 操作复盘（手动记录）
# ═══════════════════════════════════════════

def list_operations() -> list[dict]:
    """列出所有操作记录"""
    d = _ops_dir()
    if not d.exists():
        return []
    items = []
    for f in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix != ".json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append(data)
        except Exception:
            pass
    return items


def get_operation(op_id: str) -> dict | None:
    """获取单条操作记录"""
    fp = _ops_dir() / f"{op_id}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def create_operation(data: dict) -> dict:
    """创建操作记录"""
    _ops_dir().mkdir(parents=True, exist_ok=True)
    op_id = datetime.now().strftime("%Y%m%d%H%M%S")
    record = {
        "id": op_id,
        "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "code": data.get("code", ""),
        "name": data.get("name", ""),
        "action": data.get("action", "buy"),
        "price": float(data.get("price", 0)),
        "quantity": int(data.get("quantity", 0)),
        "reason": data.get("reason", ""),
        "outcome": data.get("outcome", ""),
        "profit_pct": float(data.get("profit_pct", 0)) if data.get("profit_pct") else None,
        "lesson": data.get("lesson", ""),
        "tags": data.get("tags", []),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    fp = _ops_dir() / f"{op_id}.json"
    fp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def update_operation(op_id: str, updates: dict) -> dict | None:
    """更新操作记录"""
    fp = _ops_dir() / f"{op_id}.json"
    if not fp.exists():
        return None
    try:
        record = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None
    allowed = {"date", "code", "name", "action", "price", "quantity",
               "reason", "outcome", "profit_pct", "lesson", "tags"}
    for k, v in updates.items():
        if k in allowed:
            record[k] = v
    record["updated_at"] = datetime.now().isoformat()
    fp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def delete_operation(op_id: str) -> bool:
    fp = _ops_dir() / f"{op_id}.json"
    if not fp.exists():
        return False
    fp.unlink()
    return True


def get_operation_stats() -> dict:
    """操作统计"""
    ops = list_operations()
    total = len(ops)
    buy_count = sum(1 for o in ops if o.get("action") == "buy")
    sell_count = sum(1 for o in ops if o.get("action") == "sell")
    win_count = sum(1 for o in ops if o.get("profit_pct") and o["profit_pct"] > 0)
    loss_count = sum(1 for o in ops if o.get("profit_pct") and o["profit_pct"] < 0)
    profits = [o["profit_pct"] for o in ops if o.get("profit_pct") is not None]
    return {
        "total": total,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_count / (win_count + loss_count), 2) if (win_count + loss_count) > 0 else 0,
        "avg_profit": round(sum(profits) / len(profits), 2) if profits else 0,
        "recent_tags": list(set(tag for o in ops[:20] for tag in o.get("tags", [])))[:10],
    }
