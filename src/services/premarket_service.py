"""盘前服务 — 大盘环境、政策方向、热点板块、风险事件、道氏确认"""

import concurrent.futures
from datetime import datetime
from ..data.akshare_client import AKShareClient
from ..scorer import MarketEnvScorer


def check_dow_confirmation() -> dict:
    """
    道氏理论指数相互确认 — 三组指数对照

    判断两个代表不同经济环节的指数是否同步接近近期高点。
    同步 = 趋势可靠，背离 = 假突破风险。

    :return: 确认结果字典
    """
    pairs = [
        {
            "name": "沪深300 ↔ 创业板指",
            "index_a": ("000300", "沪深300"),
            "index_b": ("399006", "创业板指"),
            "desc": "传统经济 ↔ 新经济",
        },
        {
            "name": "上证指数 ↔ 深证成指",
            "index_a": ("000001", "上证指数"),
            "index_b": ("399001", "深证成指"),
            "desc": "沪市 ↔ 深市",
        },
        {
            "name": "上证50 ↔ 中证1000",
            "index_a": ("000016", "上证50"),
            "index_b": ("000852", "中证1000"),
            "desc": "大票 ↔ 小票",
        },
    ]

    results = []

    for pair in pairs:
        code_a, name_a = pair["index_a"]
        code_b, name_b = pair["index_b"]

        try:
            df_a = AKShareClient.get_index_data(code_a, start_date="20260101")
            df_b = AKShareClient.get_index_data(code_b, start_date="20260101")

            if df_a is None or df_a.empty or df_b is None or df_b.empty:
                results.append({
                    "name": pair["name"],
                    "desc": pair["desc"],
                    "status": "unknown",
                    "signal": "⚠️ 数据不足",
                    "detail": "",
                })
                continue

            close_a = float(df_a["close"].iloc[-1])
            close_b = float(df_b["close"].iloc[-1])
            high_20_a = float(df_a["high"].tail(20).max())
            high_20_b = float(df_b["high"].tail(20).max())
            high_60_a = float(df_a["high"].tail(60).max())
            high_60_b = float(df_b["high"].tail(60).max())

            gap_20_a = (close_a - high_20_a) / high_20_a * 100
            gap_20_b = (close_b - high_20_b) / high_20_b * 100

            near_high_a = gap_20_a > -2.0
            near_high_b = gap_20_b > -2.0

            if near_high_a and near_high_b:
                status = "confirmed"
                signal = "✅ 同步确认"
                detail = (
                    f"{name_a} {close_a:.0f}（距20日高 {high_20_a:.0f}，差 {abs(gap_20_a):.1f}%）| "
                    f"{name_b} {close_b:.0f}（距20日高 {high_20_b:.0f}，差 {abs(gap_20_b):.1f}%）"
                )
            elif near_high_a and not near_high_b:
                status = "divergence"
                signal = f"⚠️ 背离 — {name_a}走强但{name_b}未跟上"
                detail = (
                    f"{name_a} 距20日高仅 {abs(gap_20_a):.1f}%，"
                    f"{name_b} 距20日高差 {abs(gap_20_b):.1f}%"
                )
            elif near_high_b and not near_high_a:
                status = "divergence"
                signal = f"⚠️ 背离 — {name_b}走强但{name_a}未跟上"
                detail = (
                    f"{name_b} 距20日高仅 {abs(gap_20_b):.1f}%，"
                    f"{name_a} 距20日高差 {abs(gap_20_a):.1f}%"
                )
            else:
                status = "not_confirmed"
                signal = "— 两个指数均远离高点"
                detail = ""

            results.append({
                "name": pair["name"],
                "desc": pair["desc"],
                "status": status,
                "signal": signal,
                "detail": detail,
            })

        except Exception:
            results.append({
                "name": pair["name"],
                "desc": pair["desc"],
                "status": "unknown",
                "signal": "⚠️ 获取数据失败",
                "detail": "",
            })

    confirmed_count = sum(1 for r in results if r["status"] == "confirmed")
    diverged_count = sum(1 for r in results if r["status"] == "divergence")

    if confirmed_count >= 2:
        overall = "✅ 2组以上同步确认，趋势信号可靠"
    elif confirmed_count == 1 and diverged_count == 0:
        overall = "🔶 仅1组确认，趋势信号偏弱"
    elif diverged_count >= 2:
        overall = "⚠️ 2组以上背离，趋势可靠性降低，注意假突破风险"
    elif diverged_count == 1:
        overall = "🔶 存在1组背离，需谨慎"
    else:
        overall = "— 无明确趋势确认信号"

    return {
        "pairs": results,
        "overall": overall,
    }


def get_premarket_analysis() -> dict:
    """获取盘前环境分析，返回结构化数据"""
    today = datetime.now().strftime("%Y-%m-%d")

    result = {
        "date": today,
        "market_env": {
            "index_code": "000001",
            "index_name": "上证指数",
            "close": 0.0,
            "change_pct": 0.0,
            "trend": "震荡",
            "advice": "震荡 50%（仓位建议）",
        },
        "policy_direction": [
            {"level": "长期政策", "content": "待补充 — 请查阅近期国务院/证监会文件", "industry": "", "status": ""},
            {"level": "短期催化", "content": "待补充 — 降准降息/行业补贴等", "industry": "", "status": ""},
            {"level": "小作文", "content": "不参与未经证实的传言", "industry": "", "status": "⚠️ 跳过"},
        ],
        "hot_sectors": [],
        "main_lines": [],
        "risks": [
            {"risk_type": "政策风险", "event": "待补充", "assessment": ""},
            {"risk_type": "外部风险", "event": "待补充 — 地缘政治/汇率等", "assessment": ""},
            {"risk_type": "流动性风险", "event": "待补充", "assessment": ""},
        ],
        "observe_questions": [
            "今天的大盘环境适合进攻还是防守？你的仓位应该调整吗？",
            "主线板块是否有持续性？支线是否会升级为主线？",
            "有没有需要避开的风险事件？",
            "你今天最关注的1-2只股票是什么？为什么？",
        ],
    }

    if not AKShareClient.check_available():
        return result

    # 并发获取指数数据和热点板块
    # 热点板块 AKShare API 经常超时(>8s)且总是失败，仅 index 阻塞等待
    from datetime import timedelta
    start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    index_future = executor.submit(
        AKShareClient.get_index_data, "000001", start_date=start_date
    )
    sector_future = executor.submit(AKShareClient.get_hot_sectors)

    try:
        index_df = index_future.result(timeout=3)
        if index_df is not None and not index_df.empty:
            latest = index_df.iloc[-1]
            close = float(latest["close"])
            open_price = float(latest["open"])
            chg = (close - open_price) / open_price * 100 if open_price > 0 else 0

            ma20 = float(index_df["close"].tail(20).mean())
            ma60 = float(index_df["close"].tail(60).mean())
            trend = MarketEnvScorer.classify_market({
                "price_above_ma20": close > ma20,
                "price_above_ma60": close > ma60,
            })

            advice_map = {
                "进攻": "进攻 80%（仓位建议）",
                "震荡": "震荡 50%（仓位建议）",
                "防守": "防守 30%以下（仓位建议）",
            }

            result["market_env"] = {
                "index_code": "000001",
                "index_name": "上证指数",
                "close": round(close, 2),
                "change_pct": round(chg, 2),
                "trend": trend,
                "advice": advice_map.get(trend, "震荡 50%（仓位建议）"),
            }
    except Exception:
        pass

    executor.shutdown(wait=False)
    return result
