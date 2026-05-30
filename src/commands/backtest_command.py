"""
/回测 策略名 开始日期 结束日期 — 策略历史回测
"""
from ..data.akshare_client import AKShareClient
from ..backtest import BacktestEngine
from ..obsidian_sync import ObsidianSync


def _simple_ma_cross_strategy(df, shares, cash):
    """均线金叉买入，死叉卖出（基础版，无趋势过滤）"""
    if len(df) < 60:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    ma5 = latest.get("ma5", 0)
    ma20 = latest.get("ma20", 0)
    prev_ma5 = prev.get("ma5", 0)
    prev_ma20 = prev.get("ma20", 0)
    price = latest["close"]
    if prev_ma5 <= prev_ma20 and ma5 > ma20 and shares == 0:
        qty = int(cash * 0.8 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty, "reason": "MA5上穿MA20金叉"}
    if prev_ma5 >= prev_ma20 and ma5 < ma20 and shares > 0:
        return {"action": "sell", "quantity": shares, "reason": "MA5下穿MA20死叉"}
    return None


def _ma_cross_enhanced_strategy(df, shares, cash):
    """
    均线金叉增强版：
    1. 道氏趋势过滤 — 只在200日均线上方做多
    2. 成交量确认 — 金叉日量 > 20日均量 × 1.5
    3. 葛兰威尔买点2 — 持仓后回调至20日均线获支撑时加仓
    """
    if len(df) < 200:
        return None
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = latest["close"]
    ma5 = latest.get("ma5", 0)
    ma20 = latest.get("ma20", 0)
    ma200 = latest.get("ma200", 0)
    prev_ma5 = prev.get("ma5", 0)
    prev_ma20 = prev.get("ma20", 0)
    volume = latest.get("volume", 0)
    vol_ma20 = latest.get("vol_ma20", 0)

    # 死叉卖出（不受趋势过滤影响，持仓就必须检查）
    if prev_ma5 >= prev_ma20 and ma5 < ma20 and shares > 0:
        return {"action": "sell", "quantity": shares, "reason": "MA5下穿MA20死叉"}

    # ── 买点1：金叉买入 ──
    golden_cross = prev_ma5 <= prev_ma20 and ma5 > ma20
    if golden_cross and shares == 0:
        # 过滤1：200日均线趋势确认
        if ma200 <= 0 or price <= ma200:
            return None  # 趋势不配合，不做多
        # 过滤2：成交量确认
        if vol_ma20 > 0 and volume < vol_ma20 * 1.5:
            return None  # 缩量金叉，不参与
        qty = int(cash * 0.8 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty,
                    "reason": "金叉(趋势+放量确认)"}

    # ── 买点2：葛兰威尔回调加仓 ──
    if shares > 0 and cash > 0:
        # 价格回踩20日均线附近（收盘在MA20上方1%以内）
        near_ma20 = ma20 > 0 and (price - ma20) / ma20 <= 0.01
        # 且前一天收盘在MA20上方较远处（今天是回调日）
        prev_close = prev["close"]
        prev_near_ma20 = ma20 > 0 and (prev_close - ma20) / ma20 > 0.01
        if near_ma20 and prev_near_ma20 and price > ma20:
            add_qty = int(cash * 0.3 / price) // 100 * 100  # 用剩余现金30%加仓
            if add_qty > 0:
                return {"action": "buy", "quantity": add_qty,
                        "reason": "葛兰威尔买点2: 回踩MA20获支撑"}

    return None


# 策略注册表 — 新增策略在此注册
STRATEGY_REGISTRY = {
    "均线金叉": _simple_ma_cross_strategy,
    "均线金叉增强版": _ma_cross_enhanced_strategy,
    "ma_cross": _simple_ma_cross_strategy,
    "ma_cross_plus": _ma_cross_enhanced_strategy,
}


def execute(args: list = None) -> str:
    """执行 /回测 命令"""
    if not args or len(args) < 3:
        return "❌ 参数不足。示例：`/回测 均线金叉 2024-01-01 2024-12-31`"

    strategy_name = args[0]
    start_date = args[1].replace("-", "")
    end_date = args[2].replace("-", "")

    # 验证策略名
    strategy_fn = STRATEGY_REGISTRY.get(strategy_name)
    if strategy_fn is None:
        available = "、".join(sorted(set(STRATEGY_REGISTRY.keys()) - {"ma_cross", "ma_cross_plus"}))
        return (
            f"❌ 未知策略「{strategy_name}」\n"
            f"当前支持的策略: {available}\n"
            f"示例: `/回测 均线金叉 {args[1]} {args[2]}`"
        )

    if not AKShareClient.check_available():
        guide = AKShareClient.install_guide()
        return ("❌ 数据源不可用。请确认：" + guide + "\n\n"
                "回测依赖本地数据管道获取历史K线。\n\n"
                "如需更完整数据，可额外配置 Tushare：\n"
                "1. 注册 https://tushare.pro\n"
                "2. 获取 token\n"
                "3. 在 .env 中设置 TUSHARE_TOKEN=你的token")

    lines = []
    lines.append("## 🔬 策略回测 — " + strategy_name)
    lines.append("")

    try:
        test_code = "000300"
        kline = AKShareClient.get_index_data(test_code, start_date, end_date)
        benchmark = AKShareClient.get_index_data("000300", start_date, end_date)

        if kline is None or kline.empty:
            return "❌ 无法获取 " + test_code + " 的回测数据（区间 " + start_date + "-" + end_date + "）"

        kline["ma5"] = kline["close"].rolling(5).mean()
        kline["ma20"] = kline["close"].rolling(20).mean()
        kline["ma200"] = kline["close"].rolling(200).mean()
        kline["vol_ma20"] = kline["volume"].rolling(20).mean()

        result = BacktestEngine.run(
            kline_df=kline,
            strategy_fn=strategy_fn,
            strategy_name=strategy_name,
            benchmark_df=benchmark,
        )

        lines.append(result.to_report())
        lines.append("")
        lines.append("### 数据说明")
        lines.append("- 回测标的: 沪深300指数 (" + test_code + ")")
        lines.append("- 数据源: Sina 财经优先，AKShare 兜底")
        lines.append("- 数据区间: " + result.start_date + " ~ " + result.end_date)
        # 标注未复权（Sina 源）
        lines.append("- ⚠️ 当前为未复权数据，长期回测结果可能因除权除息失真")

        ObsidianSync.save_backtest(strategy_name, "\n".join(lines))

    except Exception as e:
        lines.append("❌ 回测执行出错: " + str(e))
        lines.append("")
        lines.append("可能原因：")
        lines.append("- 日期格式错误（正确格式: 2024-01-01）")
        lines.append("- 数据源暂时不可用")
        lines.append("- 指定区间内无交易数据")

    lines.append("")
    lines.append("> ⚠️ 仅用于学习研究，不构成投资建议。回测结果不代表未来表现。")
    return "\n".join(lines)
