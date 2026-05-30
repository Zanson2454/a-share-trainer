"""
/问财 — 一句话选股（同花顺问财风格）
用法: /问财 低位横盘3个月以上 非ST 放量
"""

import re
from ..data.akshare_client import AKShareClient


# ── 关键词解析器 ──────────────────────────────────

def parse_query(text: str) -> dict:
    """从自然语言中提取筛选条件"""
    conds = {
        "exclude_st": True,       # 默认排除ST
        "min_days": 0,            # 横盘天数
        "max_range_pct": 999,     # 最大振幅(%)
        "position": None,         # 位置: 'low'低位, 'high'高位
        "min_volume_ratio": 0,    # 最小量比(放量)
        "max_pe": 99999,          # 最大市盈率
        "min_mktcap": 0,          # 最小市值(亿)
        "keywords": [],           # 匹配的关键词(用于回复)
    }

    text_lower = text.lower()

    # ── 排除条件 ──
    if "非st" in text_lower or "排除st" in text_lower or "不含st" in text_lower:
        conds["exclude_st"] = True
        conds["keywords"].append("非ST")
    if "包含st" in text_lower or "含st" in text_lower:
        conds["exclude_st"] = False

    # ── 横盘 ──
    if "横盘" in text:
        conds["keywords"].append("横盘")
        conds["max_range_pct"] = 20  # 默认振幅<20%

    # 振幅百分比
    m = re.search(r'振幅[<>≤]?\s*(\d+)\s*%', text)
    if m:
        conds["max_range_pct"] = int(m.group(1))
        conds["keywords"].append(f"振幅<{m.group(1)}%")
    m = re.search(r'(\d+)%\s*(?:以[内下]|振幅)', text)
    if m:
        conds["max_range_pct"] = int(m.group(1))

    # ── 时间 ──
    # "3个月" → 60天, "60天" → 60天
    m = re.search(r'(\d+)\s*个?\s*月', text)
    if m:
        conds["min_days"] = int(m.group(1)) * 20
        conds["keywords"].append(f"{m.group(1)}个月")
    m = re.search(r'(\d+)\s*天', text)
    if m:
        conds["min_days"] = max(conds["min_days"], int(m.group(1)))
        conds["keywords"].append(f"{m.group(1)}天")
    m = re.search(r'(\d+)\s*周', text)
    if m:
        conds["min_days"] = max(conds["min_days"], int(m.group(1)) * 5)
    m = re.search(r'(\d+)\s*年', text)
    if m:
        conds["min_days"] = max(conds["min_days"], int(m.group(1)) * 240)

    # ── 位置 ──
    if "低位" in text or "底部" in text or "底部区域" in text:
        conds["position"] = "low"
        conds["keywords"].append("低位")
    elif "高位" in text or "顶部" in text:
        conds["position"] = "high"
        conds["keywords"].append("高位")

    # ── 放量/缩量 ──
    m = re.search(r'放量\s*(\d+)?\s*倍?', text)
    if m or "放量" in text:
        ratio = int(m.group(1)) if (m and m.group(1)) else 1.5
        conds["min_volume_ratio"] = ratio
        conds["keywords"].append(f"放量{ratio}倍")
    if "缩量" in text:
        conds["min_volume_ratio"] = -1  # 标记缩量
        conds["keywords"].append("缩量")

    # ── 基本面 ──
    m = re.search(r'市盈率\s*[<≤]?\s*(\d+)', text)
    if m:
        conds["max_pe"] = int(m.group(1))
        conds["keywords"].append(f"PE<{m.group(1)}")
    m = re.search(r'pe\s*[<≤]?\s*(\d+)', text_lower)
    if m:
        conds["max_pe"] = int(m.group(1))

    m = re.search(r'市值\s*[>≥]?\s*(\d+)\s*亿', text)
    if m:
        conds["min_mktcap"] = int(m.group(1))
        conds["keywords"].append(f"市值>{m.group(1)}亿")

    # ── 突破 ──
    if "突破" in text:
        conds["keywords"].append("突破")

    # ── 均线交叉（520战法核心） ──
    m = re.search(r'(\d+)\s*日?(?:均)?线\s*(?:上穿|金叉)\s*(\d+)', text)
    if m:
        conds["ma_cross"] = (int(m.group(1)), int(m.group(2)))
        conds["keywords"].append(f"MA{m.group(1)}金叉MA{m.group(2)}")
    elif "金叉" in text:
        conds["ma_cross"] = (5, 20)  # 默认520
        conds["keywords"].append("金叉")
    elif "520" in text or "5.20" in text:
        conds["ma_cross"] = (5, 20)
        conds["keywords"].append("520战法")
    elif "死叉" in text:
        conds["ma_cross"] = (20, 5)  # 反着来，找死叉
        conds["keywords"].append("死叉")

    # 如果没匹配到任何特定条件，至少设置默认天数
    if not conds["keywords"]:
        conds["keywords"].append("默认条件")

    return conds


# ── 单只股票横盘检查 ──────────────────────────────

def _check_sideways(kline_df, conds: dict = None) -> dict | None:
    """根据条件字典检查单只股票"""
    if kline_df is None or len(kline_df) < 20:
        return None
    if conds is None:
        conds = {}

    min_days = conds.get("min_days", 0)
    max_range_pct = conds.get("max_range_pct", 999)
    position = conds.get("position")
    min_vol_ratio = conds.get("min_volume_ratio", 0)

    days = max(min_days, 20) if min_days > 0 else 60
    recent = kline_df.tail(min(days, len(kline_df)))
    high = recent["high"].max()
    low = recent["low"].min()
    close = recent["close"].iloc[-1]
    volume = recent["volume"].iloc[-1]
    vol_ma20 = recent["volume"].tail(20).mean()
    vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1

    # 振幅检查（仅在用户指定了横盘条件时生效）
    price_range = (high - low) / low * 100
    has_sideways_cond = min_days > 0 or max_range_pct < 999
    if has_sideways_cond and price_range > max_range_pct:
        return None

    # 位置检查（仅在横盘模式下）
    pos = (close - low) / (high - low) if high > low else 0.5
    if has_sideways_cond:
        if position == "low" and pos > 0.4:
            return None
        if position == "high" and pos < 0.6:
            return None

    # 量能检查
    if min_vol_ratio > 0 and vol_ratio < min_vol_ratio:
        return None
    if min_vol_ratio < 0 and vol_ratio > 0.8:  # 缩量标记，不够明显
        return None

    # 均线交叉检查
    ma_cross_info = ""
    if conds.get("ma_cross"):
        ma_short, ma_long = conds["ma_cross"]
        ma_s_col = f"ma{ma_short}"
        ma_l_col = f"ma{ma_long}"
        if ma_s_col not in recent.columns or ma_l_col not in recent.columns:
            return None
        today_s = recent[ma_s_col].iloc[-1]
        today_l = recent[ma_l_col].iloc[-1]
        prev_s = recent[ma_s_col].iloc[-2]
        prev_l = recent[ma_l_col].iloc[-2]
        if not (prev_s <= prev_l and today_s > today_l):
            return None
        ma_cross_info = f"MA{ma_short}↑MA{ma_long}"

    return {
        "high": round(high, 2),
        "low": round(low, 2),
        "close": round(close, 2),
        "range_pct": round(price_range, 1),
        "position": round(pos, 2),
        "vol_ratio": round(vol_ratio, 2),
        "ma_cross": ma_cross_info,
    }


# ── 执行 ──────────────────────────────────────────

def execute(args: list = None) -> str:
    query = " ".join(args) if args else ""
    if not query:
        return (
            "## 🔍 问财选股\n\n"
            "请输入选股条件，例如：\n"
            "- `/问财 低位横盘3个月 非ST`\n"
            "- `/问财 横盘 放量 市盈率小于20`\n"
            "- `/问财 底部区域 振幅15% 60天`"
        )

    conds = parse_query(query)
    lines = [f"## 🔍 问财选股", ""]
    lines.append(f"> 查询：{query}")
    lines.append(f"> 条件：{' · '.join(conds['keywords'])}")
    lines.append("")

    if not AKShareClient.check_available():
        return "❌ 数据源不可用"

    try:
        # 获取候选池
        pool = AKShareClient.get_stock_pool(
            min_mktcap=max(conds["min_mktcap"], 10),
            max_pe=conds["max_pe"],
            exclude_st=conds["exclude_st"],
        )
        if pool.empty:
            return "❌ 无符合条件的股票"

        scan_count = min(len(pool), 100)  # 最多扫100只
        results = []

        for _, row in pool.head(scan_count).iterrows():
            code = row["code"]
            name = row["name"]

            kline = AKShareClient.get_daily_kline(code)
            if kline is None or kline.empty:
                continue

            # 计算均线（金叉/死叉判断需要）
            if conds.get("ma_cross"):
                ma_s, ma_l = conds["ma_cross"]
                kline[f"ma{ma_s}"] = kline["close"].rolling(ma_s).mean()
                kline[f"ma{ma_l}"] = kline["close"].rolling(ma_l).mean()

            info = _check_sideways(kline, conds)
            if info is None:
                continue

            results.append({
                "code": code, "name": name,
                "mktcap": row["mktcap"], "pe": row.get("pe", 0),
                "info": info,
            })

        # 输出
        if not results:
            lines.append(f"⚠️ 扫描{scan_count}只，无匹配结果")
            lines.append("建议：放宽条件后重试")
        else:
            # 按振幅排序（越窄越靠前）
            results.sort(key=lambda x: x["info"]["range_pct"])

            lines.append("| 代码 | 名称 | 市值(亿) | PE | 区间 | 振幅 | 位置 | 量比 | 信号 |")
            lines.append("|------|------|----------|-----|------|------|------|------|------|")

            for r in results[:20]:
                info = r["info"]
                pos_emoji = "⭐底" if info["position"] < 0.3 else ("↑低" if info["position"] < 0.5 else "↓高")
                signal = info.get("ma_cross", "") or ""
                lines.append(
                    f"| {r['code']} | {r['name']} | {r['mktcap']:.0f} | "
                    f"{r['pe']:.0f} | {info['low']}~{info['high']} | "
                    f"{info['range_pct']}% | {pos_emoji} | {info['vol_ratio']:.1f}x | {signal} |"
                )

            lines.append("")
            lines.append(f"✅ 扫描{scan_count}只，命中{len(results)}只")

    except Exception as e:
        lines.append(f"❌ 出错: {e}")

    return "\n".join(lines)
