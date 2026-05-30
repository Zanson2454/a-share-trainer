"""
/横盘 — 寻找低位长期横盘的非ST股票
横盘定义：过去N个交易日内，最高价/最低价 < 1 + range_pct
"""

from ..data.akshare_client import AKShareClient
from ..obsidian_sync import ObsidianSync


def _is_sideways(kline_df, days: int = 60, max_range_pct: float = 0.20) -> dict | None:
    """
    判断股票是否处于横盘整理状态
    :param kline_df: 日K线 DataFrame (需有 date, close, high, low)
    :param days: 观察的交易天数
    :param max_range_pct: 最大振幅（如0.20=20%以内算横盘）
    :return: None if not sideways, else dict with metrics
    """
    if kline_df is None or len(kline_df) < days:
        return None

    recent = kline_df.tail(days)
    high = recent["high"].max()
    low = recent["low"].min()
    close = recent["close"].iloc[-1]
    ma20 = recent["close"].tail(20).mean()

    price_range = (high - low) / low

    # 振幅太大 → 不是横盘
    if price_range > max_range_pct:
        return None

    # 当前价格在区间中的位置（0=底部，1=顶部）
    position = (close - low) / (high - low) if high > low else 0.5

    return {
        "high": round(high, 2),
        "low": round(low, 2),
        "close": round(close, 2),
        "range_pct": round(price_range * 100, 1),
        "position": round(position, 2),
        "ma20": round(ma20, 2),
        "days": days,
    }


def execute(args: list = None) -> str:
    """执行 /横盘 命令"""
    lines = ["## 📊 低位横盘筛选", ""]

    # 解析参数（可选）
    days = 60
    max_range = 0.20
    top_n = 15

    if args:
        try:
            days = int(args[0]) if len(args) >= 1 else 60
            max_range = float(args[1]) / 100 if len(args) >= 2 else 0.20
        except ValueError:
            pass

    lines.append(f"> 条件：近{days}个交易日振幅 < {max_range*100:.0f}%、非ST、PE>0")
    lines.append(f"> 扫描范围：全A股市值前100只")
    lines.append("")

    if not AKShareClient.check_available():
        return "❌ 数据源不可用"

    try:
        # 从 Sina 获取候选池（市值前100只）
        pool = AKShareClient.get_stock_pool(min_mktcap=50, max_pe=500, exclude_st=True)
        if pool.empty:
            return "❌ 无法获取股票列表"

        candidates = pool.head(100)  # 只扫市值前100只，控制时间

        results = []
        scanned = 0
        lines.append("| 代码 | 名称 | 市值(亿) | 区间 | 振幅 | 位置 |")
        lines.append("|------|------|----------|------|------|------|")

        for _, row in candidates.iterrows():
            code = row["code"]
            name = row["name"]
            mktcap = row["mktcap"]

            scanned += 1
            kline = AKShareClient.get_daily_kline(code)
            if kline is None or kline.empty:
                continue

            info = _is_sideways(kline, days=days, max_range_pct=max_range)
            if info is None:
                continue

            high = info["high"]
            low = info["low"]
            rng = info["range_pct"]
            pos = info["position"]

            # 优先展示低位（position < 0.4 = 偏底部）
            priority = "⭐" if pos < 0.3 else ("↑" if pos < 0.5 else "↓")
            pos_label = "底部" if pos < 0.3 else ("偏低" if pos < 0.5 else "偏高")

            lines.append(
                f"| {code} | {name} | {mktcap:.0f} | {low:.2f}~{high:.2f} | "
                f"{rng}% | {priority} {pos_label} |"
            )
            results.append({"code": code, "name": name, "info": info, "mktcap": mktcap})

        if not results:
            lines.append("")
            lines.append(f"⚠️ 扫描{scanned}只股票，无满足横盘条件的")
            lines.append(f"建议：放宽振幅参数，如 `/横盘 60 25`（振幅放宽到25%）")
        else:
            lines.append("")
            lines.append(f"✅ 扫描{scanned}只，{len(results)}只符合横盘条件")
            lines.append("")
            lines.append("> ⭐=底部区域 ↑=偏低位 ↓=区间偏高")
            lines.append("> 底部区域的横盘股向上突破概率更高")

    except Exception as e:
        lines.append(f"❌ 筛选出错: {e}")

    lines.append("")
    lines.append("> ⚠️ 仅用于学习研究，不构成投资建议")
    return "\n".join(lines)
