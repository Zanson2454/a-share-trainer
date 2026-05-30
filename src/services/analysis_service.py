"""个股分析服务 — 技术面+基本面+风险点+K线形态"""

import concurrent.futures
import socket

import pandas as pd

from ..data.akshare_client import AKShareClient
from ..scorer import TechnicalScorer
from .pattern_recognition import detect_patterns


def _get_financial_abstract(code: str) -> dict:
    """用 AKShare stock_financial_abstract 获取深度财务指标"""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(5)
        import akshare as ak
        df = ak.stock_financial_abstract(symbol=code)
        if df is None or df.empty:
            return {}
        latest_col = df.columns[2]  # 最新一期
        prev_col = df.columns[3] if len(df.columns) > 3 else latest_col
        prev2_col = df.columns[4] if len(df.columns) > 4 else latest_col

        def get_val(indicator: str, col=None):
            row = df[df["指标"] == indicator]
            if row.empty:
                return None
            c = col or latest_col
            val = row.iloc[0][c]
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        return {
            "eps": get_val("基本每股收益"),
            "eps_prev": get_val("基本每股收益", prev_col),
            "eps_prev2": get_val("基本每股收益", prev2_col),
            "net_profit": get_val("净利润"),
            "net_profit_prev": get_val("净利润", prev_col),
            "deducted_profit": get_val("扣非净利润"),
            "deducted_profit_prev": get_val("扣非净利润", prev_col),
            "revenue": get_val("营业总收入"),
            "revenue_prev": get_val("营业总收入", prev_col),
            "revenue_growth": get_val("营业总收入增长率"),
            "revenue_growth_prev": get_val("营业总收入增长率", prev_col),
            "profit_growth": get_val("归属母公司净利润增长率"),
            "profit_growth_prev": get_val("归属母公司净利润增长率", prev_col),
            "roe": get_val("净资产收益率(ROE)"),
            "debt_ratio": get_val("资产负债率"),
            "_report_period": latest_col,
        }
    except Exception as e:
        print(f"[AKShare] 财务摘要获取失败 {code}: {e}")
        return {}
    finally:
        socket.setdefaulttimeout(old_timeout)


def _analyze_fundamental_quick(pe: float | None, fin_abs: dict) -> dict:
    """基本面快速分析法：PE、营收利润同步、EPS环比、PEG"""
    result = {
        "pe_dynamic": pe,
        "pe_level": "",
        "pe_explanation": "",
        "revenue_profit_sync": "",
        "revenue_profit_detail": "",
        "eps_qoq": "",
        "eps_qoq_detail": "",
        "peg": None,
        "peg_level": "",
        "peg_explanation": "",
    }

    # ── 1. 动态市盈率 (PE) ──
    if pe is not None and pe > 0:
        if pe < 20:
            result["pe_level"] = "偏低"
        elif pe < 40:
            result["pe_level"] = "合理"
        elif pe < 80:
            result["pe_level"] = "偏高"
        else:
            result["pe_level"] = "极高"

        years = round(pe, 1)
        result["pe_explanation"] = (
            f"动态PE={pe:.1f}，即按当前盈利水平，约需{years}年回本。"
            f"PE=股价÷每股收益(年化)。"
            f"动态PE使用最近一季度数据年化计算，变动较快；"
            f"TTM(滚动PE)使用过去4个季度实际数据，更为平滑稳定。"
            f"当前PE处于{result['pe_level']}水平。"
        )
    else:
        result["pe_explanation"] = "PE数据暂不可用（可能盈利为负）"

    # ── 2. 营收与利润同步分析 ──
    rev_g = fin_abs.get("revenue_growth")
    prof_g = fin_abs.get("profit_growth")
    deducted = fin_abs.get("deducted_profit")
    net_profit = fin_abs.get("net_profit")

    if rev_g is not None and prof_g is not None:
        sync_gap = abs(rev_g - prof_g)
        if sync_gap < 10:
            result["revenue_profit_sync"] = "同步"
            result["revenue_profit_detail"] = (
                f"营收增速{rev_g:+.1f}%，利润增速{prof_g:+.1f}%，两者基本同步，"
                f"增长质量较好。"
            )
        elif prof_g > rev_g + 10:
            result["revenue_profit_sync"] = "利润增速远超营收"
            result["revenue_profit_detail"] = (
                f"营收增速{rev_g:+.1f}%，利润增速{prof_g:+.1f}%，利润增速显著高于营收，"
                f"需确认是否为一次性收益或费用缩减所致。"
            )
        else:
            result["revenue_profit_sync"] = "增收不增利"
            result["revenue_profit_detail"] = (
                f"营收增速{rev_g:+.1f}%，利润增速{prof_g:+.1f}%，收入增长但利润未能同步，"
                f"可能是成本上升或竞争加剧。"
            )
    else:
        result["revenue_profit_sync"] = "数据不足"

    # 检查是否主业增长（扣非 vs 净利润）
    if deducted is not None and net_profit is not None and net_profit > 0:
        ratio = deducted / net_profit
        if ratio < 0.7:
            result["revenue_profit_detail"] += (
                f" 扣非净利润仅占净利润的{ratio*100:.0f}%，非经常性收益占比大，"
                f"需关注盈利可持续性。"
            )
        elif ratio > 0.9:
            if not result["revenue_profit_detail"]:
                result["revenue_profit_detail"] = ""
            result["revenue_profit_detail"] += " 扣非净利润与净利润基本一致，主业盈利扎实。"

    # ── 3. 每股收益环比 ──
    eps = fin_abs.get("eps")
    eps_p = fin_abs.get("eps_prev")
    eps_p2 = fin_abs.get("eps_prev2")
    if eps is not None and eps_p is not None:
        qoq = (eps - eps_p) / abs(eps_p) * 100 if eps_p != 0 else 0
        if qoq > 5:
            result["eps_qoq"] = "环比增长"
            trend = "上升"
        elif qoq < -5:
            result["eps_qoq"] = "环比下降"
            trend = "下降"
        else:
            result["eps_qoq"] = "环比持平"
            trend = "持平"

        detail = f"最新EPS={eps:.2f}，上期EPS={eps_p:.2f}，环比{qoq:+.1f}%。"
        if eps_p2 is not None and eps_p is not None:
            prev_qoq = (eps_p - eps_p2) / abs(eps_p2) * 100 if eps_p2 != 0 else 0
            if qoq < prev_qoq:
                detail += f" 增速较上期（{prev_qoq:+.1f}%）放缓，需关注趋势变化。"
            elif qoq > prev_qoq:
                detail += f" 增速较上期（{prev_qoq:+.1f}%）加快，业绩加速{trend}。"
        result["eps_qoq_detail"] = detail
    else:
        result["eps_qoq"] = "数据不足"

    # ── 4. PEG 比值 ──
    if prof_g is not None and pe is not None and pe > 0:
        peg = prof_g / pe
        result["peg"] = round(peg, 2)
        if peg > 1.5:
            result["peg_level"] = "低估"
            result["peg_explanation"] = (
                f"PEG={peg:.2f} > 1，净利润增速({prof_g:.1f}%)远超市盈率({pe:.1f})，"
                f"按PEG估值当前股价可能被低估，业绩增长强劲。"
            )
        elif peg >= 0.8:
            result["peg_level"] = "合理"
            result["peg_explanation"] = (
                f"PEG={peg:.2f} ≈ 1，净利润增速({prof_g:.1f}%)与市盈率({pe:.1f})"
                f"基本匹配，估值处于合理区间。"
            )
        else:
            result["peg_level"] = "高估"
            result["peg_explanation"] = (
                f"PEG={peg:.2f} < 1，净利润增速({prof_g:.1f}%)低于市盈率({pe:.1f})，"
                f"按PEG估值当前股价可能偏高，需业绩加速来消化估值。"
            )
    else:
        result["peg_explanation"] = "缺少利润增速或PE数据，无法计算PEG"

    return result


def _generate_recommendation(
    code: str, name: str, close: float, trend: str,
    mas: dict, vol_label: str, vol_ratio: float,
    tech_score: float, tech_desc: str,
    support_1: float, support_2: float,
    resistance_1: float, resistance_2: float,
    patterns: list[dict], fin: dict, quick: dict,
) -> dict:
    """综合技术面、形态、估值生成操作建议"""
    score = 0
    buy_conditions: list[str] = []
    sell_conditions: list[str] = []

    # ── 趋势评分（-5 ~ +5）──
    if trend == "上升":
        score += 3
    elif trend == "下降":
        score -= 3
        buy_conditions.append(f"趋势转为震荡或上升（站稳MA20={resistance_2:.2f}上方）")

    ma5_dir = mas.get("ma5", {}).get("direction", "")
    ma20_dir = mas.get("ma20", {}).get("direction", "")

    if close > mas.get("ma5", {}).get("value", close):
        score += 1
    if close < mas.get("ma60", {}).get("value", close):
        score -= 1
        buy_conditions.append("价格站上MA60确认中期趋势")

    if ma5_dir == "up" and ma20_dir == "up":
        score += 2
    elif ma5_dir == "down" and ma20_dir == "down":
        score -= 1

    # ── 成交量（-2 ~ +2）──
    if vol_label == "放量":
        score += 2
    elif vol_label == "缩量":
        score -= 1
        buy_conditions.append("成交量放大至20日均量1.2倍以上")

    # ── 技术评分（-3 ~ +3）──
    if tech_score >= 18:
        score += 2
    elif tech_score >= 12:
        score += 1
    elif tech_score < 8:
        score -= 2

    # ── 形态信号（-4 ~ +4）──
    b_signals = [p for p in patterns if p.get("signal") == "B"]
    s_signals = [p for p in patterns if p.get("signal") == "S"]
    if b_signals:
        score += min(len(b_signals) * 2, 4)
    if s_signals:
        score -= min(len(s_signals) * 2, 4)

    # ── 估值评分（-3 ~ +3）──
    pe = fin.get("pe")
    peg_level = quick.get("peg_level", "")
    if pe is not None and pe > 0:
        if pe < 20:
            score += 2
        elif pe < 40:
            score += 1
        elif pe > 80:
            score -= 2
        elif pe > 40:
            score -= 1
    if peg_level == "低估":
        score += 2
        buy_conditions.append("PEG低估+业绩确认，可分批建仓")
    elif peg_level == "高估":
        score -= 1
        sell_conditions.append("估值偏高，若业绩增速放缓应考虑减仓")

    # ── 确定操作建议 ──
    if score >= 5:
        action = "买入"
    elif score >= 2:
        action = "买入"
    elif score <= -5:
        action = "卖出"
    elif score <= -2:
        action = "卖出"
    else:
        action = "观望"

    # 0-10 置信度（基于综合得分的绝对值映射）
    confidence = max(1, min(10, 5 + score // 2))

    # ── 入场区间和止盈止损 ──
    entry_low = round(max(support_1, close * 0.97), 2)
    entry_high = round(min(resistance_2, close * 1.03), 2)
    entry_zone = f"{entry_low:.2f} - {entry_high:.2f}" if entry_low < entry_high else f"{entry_high:.2f}附近"

    stop_loss = round(min(support_2, entry_low * 0.95), 2)

    targets: list[float] = []
    if resistance_1 > close:
        targets.append(round(resistance_1, 2))
    if close + (close - stop_loss) * 1.5 > resistance_1:
        targets.append(round(close + (close - stop_loss) * 1.5, 2))

    # ── 生成买卖条件列表 ──
    if trend == "上升":
        sell_conditions.append(f"跌破MA20（{mas.get('ma20', {}).get('value', 0):.2f}）止盈")
        sell_conditions.append(f"放量跌破支撑{entry_low:.2f}止损")
    elif trend == "下降":
        sell_conditions.append("反弹至MA20附近减仓")
    else:
        sell_conditions.append(f"跌破前低{support_1:.2f}止损")

    if b_signals:
        for p in b_signals[:2]:
            buy_conditions.append(f"{p['name']}：{p.get('description', '')}")
    if s_signals:
        for p in s_signals[:2]:
            sell_conditions.append(f"{p['name']}：{p.get('description', '')}")

    # 去重 + 限制数量
    buy_conditions = list(dict.fromkeys(buy_conditions))[:4]
    sell_conditions = list(dict.fromkeys(sell_conditions))[:4]

    # ── 摘要 ──
    trend_word = {"上升": "多头", "震荡": "震荡", "下降": "空头"}.get(trend, "")
    pe_word = f"PE={pe:.1f}" if pe else ""
    summary = f"{trend_word}趋势，技术评分{tech_score:.0f}/25"
    if pe_word:
        summary += f"，{pe_word}"

    return {
        "action": action,
        "confidence": confidence,
        "summary": summary,
        "timeframe": "中短线（4-12周），基于日线数据的技术面+形态+估值综合判断",
        "buy_conditions": buy_conditions,
        "sell_conditions": sell_conditions,
        "entry_zone": entry_zone,
        "stop_loss": stop_loss,
        "targets": targets,
    }


def _compute_timeframe_trend(kline: pd.DataFrame, period_label: str, label: str) -> dict:
    """对已聚合的K线计算趋势"""
    if len(kline) < 20:
        return {"period": period_label, "trend": "数据不足", "close": 0, "ma20": 0, "ma60": 0, "label": label}
    kline["ma20"] = kline["close"].rolling(20).mean()
    kline["ma60"] = kline["close"].rolling(60).mean()
    latest = kline.iloc[-1]
    close = float(latest["close"])
    ma20 = float(latest.get("ma20", close))
    ma60 = float(latest.get("ma60", close))

    if close > ma20 and ma20 > ma60:
        trend = "上升"
    elif close < ma20 and ma20 < ma60:
        trend = "下降"
    elif close > ma20:
        trend = "上升"
    elif close < ma60:
        trend = "下降"
    else:
        trend = "震荡"
    return {"period": period_label, "trend": trend, "close": round(close, 2), "ma20": round(ma20, 2), "ma60": round(ma60, 2), "label": label}


def _compute_multi_timeframe(daily_kline: pd.DataFrame) -> list[dict]:
    """从日线数据计算短中长期趋势"""
    if daily_kline is None or daily_kline.empty:
        return []
    daily_kline = daily_kline.copy()
    daily_kline.set_index("date", inplace=True)

    results: list[dict] = []

    # 短期 = 日线
    results.append(_compute_timeframe_trend(daily_kline.reset_index(), "日线", "短期"))

    # 中期 = 周线（日线 resample 到周）
    weekly = daily_kline.resample("W").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    weekly = weekly.reset_index()
    weekly.rename(columns={"index": "date"}, inplace=True)
    if "date" not in weekly.columns:
        weekly.insert(0, "date", weekly.index)
    results.append(_compute_timeframe_trend(weekly, "周线", "中期"))

    # 长期 = 月线
    monthly = daily_kline.resample("ME").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    monthly = monthly.reset_index()
    if "date" not in monthly.columns:
        monthly.insert(0, "date", monthly.index)
    results.append(_compute_timeframe_trend(monthly, "月线", "长期"))

    return results


def analyze_stock(code: str) -> dict | None:
    """分析单只股票，返回结构化数据"""
    kline = AKShareClient.get_daily_kline(code)
    if kline is None or kline.empty:
        return None

    # 技术面计算（CPU-only，可并行）
    kline["ma5"] = kline["close"].rolling(5).mean()
    kline["ma20"] = kline["close"].rolling(20).mean()
    kline["ma60"] = kline["close"].rolling(60).mean()
    latest = kline.iloc[-1]
    prev = kline.iloc[-2] if len(kline) > 1 else latest

    close = float(latest["close"])
    ma20_val = float(latest.get("ma20", close))
    ma60_val = float(latest.get("ma60", close))

    # MA-based trend
    if close > ma20_val and ma20_val > ma60_val:
        trend = "上升"
    elif close < ma20_val and ma20_val < ma60_val:
        trend = "下降"
    elif close > ma20_val:
        trend = "上升"
    elif close < ma60_val:
        trend = "下降"
    else:
        trend = "震荡"

    # Short-term rate of change can override MA-based classification
    # (catches sharp reversals where MAs haven't yet adapted)
    n_bars = len(kline)
    chg_10d = (close - float(kline["close"].iloc[-11])) / float(kline["close"].iloc[-11]) if n_bars > 11 else 0
    chg_20d = (close - float(kline["close"].iloc[-21])) / float(kline["close"].iloc[-21]) if n_bars > 21 else 0

    if chg_20d < -0.10:
        trend = "下降"
    elif chg_20d > 0.10:
        trend = "上升"
    elif chg_10d < -0.08:
        trend = "下降"
    elif chg_10d > 0.08:
        trend = "上升"

    mas = {}
    for label, key in [("ma5", "ma5"), ("ma20", "ma20"), ("ma60", "ma60")]:
        val = float(latest.get(key, 0))
        prev_val = float(prev.get(key, val))
        mas[label] = {"value": round(val, 2), "direction": "up" if val >= prev_val else "down"}

    avg_vol_20 = float(kline["volume"].tail(20).mean())
    vol = float(latest["volume"])
    vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1
    if vol_ratio > 1.5:
        vol_label = "放量"
    elif vol_ratio < 0.5:
        vol_label = "缩量"
    else:
        vol_label = "正常"

    support_1 = float(kline["low"].tail(20).min())
    resistance_1 = float(kline["high"].tail(20).max())
    tech = TechnicalScorer.score(kline)
    patterns = detect_patterns(kline)

    # 财务数据与摘要并发获取（两者均为独立 I/O 调用）
    fin = {}
    fin_abs = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fin_future = executor.submit(AKShareClient.get_financial_data, code)
        fin_abs_future = executor.submit(_get_financial_abstract, code)
        fin = fin_future.result(timeout=8) or {}
        fin_abs = fin_abs_future.result(timeout=8) or {}

    quick = _analyze_fundamental_quick(fin.get("pe"), fin_abs)

    # 若 fin_abs 有更准的数据，优先使用
    if fin_abs.get("roe") is not None:
        fin["roe"] = fin_abs["roe"]
    if fin_abs.get("debt_ratio") is not None:
        fin["debt_ratio"] = fin_abs["debt_ratio"]
    if fin_abs.get("revenue_growth") is not None:
        fin["revenue_growth"] = fin_abs["revenue_growth"]
    if fin_abs.get("profit_growth") is not None:
        fin["profit_growth"] = fin_abs["profit_growth"]

    name = fin.get("_name", "") if fin else ""

    # 数据来源与时间范围
    first_date = str(kline["date"].iloc[0])[:10]
    last_date = str(kline["date"].iloc[-1])[:10]
    data_range = f"{first_date} ~ {last_date}"
    data_source = "Sina 财经（不复权日线）"

    # 综合建议
    recommendation = _generate_recommendation(
        code=code, name=name, close=close, trend=trend, mas=mas,
        vol_label=vol_label, vol_ratio=vol_ratio,
        tech_score=tech["score"], tech_desc=tech["desc"],
        support_1=support_1, support_2=ma60_val,
        resistance_1=resistance_1, resistance_2=ma20_val,
        patterns=patterns, fin=fin, quick=quick,
    )

    # ── 多周期趋势（短期日线/中期周线/长期月线）──
    multi_timeframe = _compute_multi_timeframe(kline)

    return {
        "code": code,
        "name": name,
        "quick": quick,
        "patterns": patterns,
        "recommendation": recommendation,
        "data_source": data_source,
        "data_range": data_range,
        "multi_timeframe": multi_timeframe,
        "technical": {
            "trend": trend,
            "close": round(close, 2),
            "ma5": mas["ma5"]["value"],
            "ma20": mas["ma20"]["value"],
            "ma60": mas["ma60"]["value"],
            "ma_directions": mas,
            "volume": round(vol, 0),
            "avg_volume_20": round(avg_vol_20, 0),
            "volume_ratio": round(vol_ratio, 2),
            "volume_label": vol_label,
            "support_1": round(support_1, 2),
            "support_2": round(ma60_val, 2),
            "resistance_1": round(resistance_1, 2),
            "resistance_2": round(ma20_val, 2),
            "score": round(tech["score"], 1),
            "score_desc": tech["desc"],
        },
        "financial": {
            "pe": fin.get("pe"),
            "pb": fin.get("pb"),
            "roe": fin.get("roe"),
            "revenue_growth": fin.get("revenue_growth"),
            "profit_growth": fin.get("profit_growth"),
            "debt_ratio": fin.get("debt_ratio"),
        } if fin else {},
        "risk_points": [
            "大盘系统性下跌风险",
            "行业政策变动风险",
            "个股流动性风险（日成交额是否过小）",
            "业绩暴雷风险（财报发布窗口期）",
        ],
        "observe_signals": [
            "能否站稳 MA20 上方（趋势确认）",
            "成交量是否持续放大（资金进场）",
            "同板块是否有共振效应",
            "是否有突破20日高点压力位的尝试",
        ],
    }
