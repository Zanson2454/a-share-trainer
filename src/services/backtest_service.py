"""回测服务 — 策略历史验证"""

import pandas as pd
from ..data.akshare_client import AKShareClient
from ..backtest import BacktestEngine, BacktestResult


def _simple_ma_cross_strategy(df, shares, cash):
    """均线金叉买入，死叉卖出"""
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
    """均线金叉增强版：趋势过滤 + 成交量确认 + 葛兰威尔加仓"""
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

    # 死叉卖出
    if prev_ma5 >= prev_ma20 and ma5 < ma20 and shares > 0:
        return {"action": "sell", "quantity": shares, "reason": "MA5下穿MA20死叉"}

    # 金叉买入（放松趋势和成交量要求，避免过于严格）
    golden_cross = prev_ma5 <= prev_ma20 and ma5 > ma20
    if golden_cross and shares == 0:
        # 趋势过滤：仅在 ma200 有效且价格低于 ma200 时跳过
        if ma200 > 0 and price <= ma200:
            return None
        # 成交量确认：至少达到均量的 1.2 倍
        if pd.notna(vol_ma20) and vol_ma20 > 0 and volume < vol_ma20 * 1.2:
            return None
        qty = int(cash * 0.8 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty, "reason": "金叉(趋势+放量确认)"}

    # 葛兰威尔回调加仓
    if shares > 0 and cash > 0:
        near_ma20 = ma20 > 0 and (price - ma20) / ma20 <= 0.01
        prev_close = prev["close"]
        prev_near_ma20 = ma20 > 0 and (prev_close - ma20) / ma20 > 0.01
        if near_ma20 and prev_near_ma20 and price > ma20:
            add_qty = int(cash * 0.3 / price) // 100 * 100
            if add_qty > 0:
                return {"action": "buy", "quantity": add_qty, "reason": "葛兰威尔买点2: 回踩MA20获支撑"}
    return None


def _macd_cross_strategy(df, shares, cash):
    """MACD金叉买入，死叉卖出"""
    if len(df) < 60:
        return None
    close = df["close"]
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = 2 * (dif - dea)
    if len(macd_bar) < 2:
        return None
    prev_dif, cur_dif = dif.iloc[-2], dif.iloc[-1]
    prev_dea, cur_dea = dea.iloc[-2], dea.iloc[-1]
    price = close.iloc[-1]
    if prev_dif <= prev_dea and cur_dif > cur_dea and shares == 0:
        qty = int(cash * 0.8 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty, "reason": "MACD金叉(DIF上穿DEA)"}
    if prev_dif >= prev_dea and cur_dif < cur_dea and shares > 0:
        return {"action": "sell", "quantity": shares, "reason": "MACD死叉(DIF下穿DEA)"}
    return None


def _rsi_oversold_strategy(df, shares, cash):
    """RSI超卖买入，超买卖出"""
    if len(df) < 30:
        return None
    close = df["close"]
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    if len(rsi) < 2:
        return None
    prev_rsi, cur_rsi = rsi.iloc[-2], rsi.iloc[-1]
    price = close.iloc[-1]
    if prev_rsi <= 30 and cur_rsi > 30 and shares == 0:
        qty = int(cash * 0.8 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty, "reason": f"RSI超卖反弹(RSI={cur_rsi:.1f})"}
    if prev_rsi >= 70 and cur_rsi < 70 and shares > 0:
        return {"action": "sell", "quantity": shares, "reason": f"RSI超买回落(RSI={cur_rsi:.1f})"}
    return None


def _bollinger_breakout_strategy(df, shares, cash):
    """布林带突破上轨买入，跌破中轨卖出"""
    if len(df) < 30:
        return None
    close = df["close"]
    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20
    if len(ma20) < 2:
        return None
    prev_close, cur_close = close.iloc[-2], close.iloc[-1]
    prev_upper, cur_upper = upper.iloc[-2], upper.iloc[-1]
    prev_ma20, cur_ma20 = ma20.iloc[-2], ma20.iloc[-1]
    price = cur_close
    if prev_close <= prev_upper and cur_close > cur_upper and shares == 0:
        qty = int(cash * 0.6 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty, "reason": "布林带突破上轨"}
    if prev_close >= prev_ma20 and cur_close < cur_ma20 and shares > 0:
        return {"action": "sell", "quantity": shares, "reason": "跌破布林中轨(MA20)"}
    return None


def _ma_bullish_alignment_strategy(df, shares, cash):
    """均线多头排列买入（MA5>MA20>MA60），跌破MA60卖出"""
    if len(df) < 60:
        return None
    # 按需补充MA列（必须在取latest/prev之前）
    for ma_n in [5, 20, 60]:
        col = f"ma{ma_n}"
        if col not in df.columns:
            df[col] = df["close"].rolling(ma_n).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    price = latest["close"]
    ma5, ma20, ma60 = latest["ma5"], latest["ma20"], latest["ma60"]
    prev_ma5, prev_ma20, prev_ma60 = prev["ma5"], prev["ma20"], prev["ma60"]

    # 多头排列买入：MA5 > MA20 > MA60 且刚形成
    is_bullish = ma5 > ma20 > ma60
    was_bullish = prev_ma5 > prev_ma20 > prev_ma60
    if is_bullish and not was_bullish and shares == 0:
        qty = int(cash * 0.8 / price) // 100 * 100
        if qty > 0:
            return {"action": "buy", "quantity": qty, "reason": "均线多头排列(MA5>MA20>MA60)"}

    # 跌破MA60止损，或死叉(MA5下穿MA20)止盈
    if shares > 0:
        prev_above_ma60 = prev["close"] > prev_ma60
        cur_below_ma60 = price < ma60
        dead_cross = prev_ma5 >= prev_ma20 and ma5 < ma20
        if (not prev_above_ma60 and cur_below_ma60) or dead_cross:
            return {"action": "sell", "quantity": shares, "reason": "均线多头破坏(破MA60或死叉)"}
    return None


def _turtle_trading_strategy(df, shares, cash):
    """海龟交易法则：20日/55日突破买入，10日/20日跌破卖出"""
    if len(df) < 60:
        return None
    high = df["high"]
    low = df["low"]
    close = df["close"]
    high_20 = high.rolling(20).max()
    high_55 = high.rolling(55).max()
    low_10 = low.rolling(10).min()
    low_20 = low.rolling(20).min()
    if len(high_20) < 2:
        return None
    prev_close, cur_close = close.iloc[-2], close.iloc[-1]
    price = cur_close

    # 买入：突破20日或55日高点
    if shares == 0:
        breakout_20 = prev_close <= high_20.iloc[-2] and cur_close > high_20.iloc[-1]
        breakout_55 = prev_close <= high_55.iloc[-2] and cur_close > high_55.iloc[-1]
        if breakout_20 or breakout_55:
            atr = (high - low).rolling(20).mean().iloc[-1]
            stop_price = price - 2 * atr
            risk_per_share = price - stop_price
            if risk_per_share > 0:
                qty = int((cash * 0.01) / risk_per_share) // 100 * 100
            else:
                qty = int(cash * 0.8 / price) // 100 * 100
            if qty > 0:
                label = "20日" if breakout_20 else "55日"
                return {"action": "buy", "quantity": qty, "reason": f"海龟{label}突破(止损={stop_price:.2f})"}

    # 卖出：跌破10日或20日低点
    if shares > 0:
        exit_10 = prev_close >= low_10.iloc[-2] and cur_close < low_10.iloc[-1]
        exit_20 = prev_close >= low_20.iloc[-2] and cur_close < low_20.iloc[-1]
        if exit_10 or exit_20:
            label = "10日" if exit_10 else "20日"
            return {"action": "sell", "quantity": shares, "reason": f"海龟{label}跌破退出"}
    return None


# ── 四大理论参数默认值 ──
DEFAULT_PARAMS = {
    "trend_ma": 200,        # 道氏 D1: 趋势均线周期
    "fast_ma": 5,           # 信号快线
    "slow_ma": 20,          # 信号慢线
    "volume_mult": 1.5,     # 道氏 D3: 量能确认倍数
    "overbought_bias": 15,  # 葛兰威尔 S8: 乖离止盈阈值 %
    "oversold_bias": -15,   # 葛兰威尔 B4: 乖离超跌阈值 %
    "pullback_tolerance": 1,# 葛兰威尔 B2: 回调加仓容忍度 %
    "gann_retrace": 50,     # 江恩 G1: 回调位 %
    "gann_tolerance": 3,    # 江恩 G1: 容忍度 %
    "add_position_ratio": 30,# 葛兰威尔 B2: 加仓资金比例 %
    "first_position_ratio": 80,  # 首仓资金比例 %
    "gann_resonance_bonus": 90,  # 江恩共振仓位加成 %
}

# 参数可调范围（前端用）
PARAM_RANGES = {
    "trend_ma": {"min": 100, "max": 300, "step": 10, "label": "趋势均线周期", "options": [150, 200, 250]},
    "fast_ma": {"min": 3, "max": 15, "step": 1, "label": "信号快线", "options": [3, 5, 10]},
    "slow_ma": {"min": 10, "max": 60, "step": 5, "label": "信号慢线", "options": [10, 20, 30]},
    "volume_mult": {"min": 1.0, "max": 3.0, "step": 0.1, "label": "量能确认倍数"},
    "overbought_bias": {"min": 5, "max": 30, "step": 1, "label": "乖离止盈阈值%"},
    "oversold_bias": {"min": -30, "max": -5, "step": 1, "label": "乖离超跌阈值%"},
    "pullback_tolerance": {"min": 0.3, "max": 5, "step": 0.1, "label": "回调加仓容忍度%"},
    "gann_retrace": {"min": 20, "max": 80, "step": 1, "label": "江恩回调位%", "options": [33, 50, 66]},
    "gann_tolerance": {"min": 1, "max": 8, "step": 0.5, "label": "江恩容忍度%"},
    "add_position_ratio": {"min": 10, "max": 60, "step": 5, "label": "加仓资金比例%"},
    "first_position_ratio": {"min": 40, "max": 100, "step": 5, "label": "首仓资金比例%"},
    "gann_resonance_bonus": {"min": 60, "max": 100, "step": 5, "label": "江恩共振仓位加成%"},
}


def _ensure_mas(df, periods):
    """确保 df 有指定周期的均线列"""
    for p in periods:
        col = f"ma{p}"
        if col not in df.columns:
            df[col] = df["close"].rolling(p).mean()


def _make_layered_strategy(p: dict):
    """工厂函数：根据 12 个参数创建可分层的策略函数"""
    trend_ma = p["trend_ma"]
    fast_ma = p["fast_ma"]
    slow_ma = p["slow_ma"]
    vol_mult = p["volume_mult"]
    overbought = p["overbought_bias"] / 100
    oversold = p["oversold_bias"] / 100
    pullback_tol = p["pullback_tolerance"] / 100
    gann_retrace = p["gann_retrace"] / 100
    gann_tol = p["gann_tolerance"] / 100
    add_ratio = p["add_position_ratio"] / 100
    first_ratio = p["first_position_ratio"] / 100
    gann_bonus_ratio = p["gann_resonance_bonus"] / 100
    layer = p.get("layer", 4)
    # 最小 bar 数：金叉检测需要 slow_ma 根K线即可
    # trend_ma 可能需要更长预热，但未就绪时(NaN)趋势过滤条件自然为假→不过滤
    min_bars = max(slow_ma + 5, 30)

    def strategy(df, shares, cash):
        if len(df) < min_bars:
            return None

        close_series = df["close"]
        _ensure_mas(df, [fast_ma, slow_ma, trend_ma])
        fast_col, slow_col, trend_col = f"ma{fast_ma}", f"ma{slow_ma}", f"ma{trend_ma}"

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        price = latest["close"]
        ma_f = latest[fast_col]
        ma_s = latest[slow_col]
        ma_t = latest[trend_col]
        prev_f = prev[fast_col]
        prev_s = prev[slow_col]
        volume = latest.get("volume", 0)

        # ── 共用的金叉/死叉检测 ──
        golden_cross = prev_f <= prev_s and ma_f > ma_s
        dead_cross = prev_f >= prev_s and ma_f < ma_s
        bias = (price - ma_s) / ma_s if ma_s > 0 else 0

        # ── 卖出逻辑（所有层共用） ──
        if shares > 0:
            # 死叉卖出
            if dead_cross:
                return {"action": "sell", "quantity": shares, "reason": f"死叉(MA{fast_ma}↓MA{slow_ma})"}
            # 乖离止盈 S8（L2+）
            if layer >= 2 and overbought > 0 and bias >= overbought:
                return {"action": "sell", "quantity": shares, "reason": f"乖离止盈(偏差{bias*100:.1f}%)"}
            # 跌破趋势线止损
            if ma_t > 0 and price < ma_t:
                return {"action": "sell", "quantity": shares, "reason": f"跌破MA{trend_ma}止损"}

        # ── 买入逻辑 ──
        if shares == 0 and golden_cross:
            # 层1+：趋势过滤 D1
            if layer >= 1 and ma_t > 0 and price <= ma_t:
                return None
            # 层1+：成交量验证 D3
            if layer >= 1:
                vol_ma = latest.get("vol_ma20", 0)
                if pd.notna(vol_ma) and vol_ma > 0 and volume < vol_ma * vol_mult:
                    return None

            # 仓位比例
            use_ratio = first_ratio

            # 层3+：江恩回调共振 G1
            gann_boost = False
            if layer >= 3:
                recent_high = df["high"].iloc[-60:].max()
                recent_low = df["low"].iloc[-60:].min()
                swing_range = recent_high - recent_low
                if swing_range > 0:
                    retrace_price = recent_high - swing_range * gann_retrace
                    if abs(price - retrace_price) / recent_high <= gann_tol:
                        gann_boost = True
                        use_ratio = max(use_ratio, gann_bonus_ratio)

            qty = int(cash * use_ratio / price) // 100 * 100
            if qty <= 0:
                return None
            reason = f"金叉买入(MA{fast_ma}↑MA{slow_ma})"
            if gann_boost:
                reason += f" + 江恩{int(gann_retrace*100)}%回调共振"
            return {"action": "buy", "quantity": qty, "reason": reason}

        # ── 持仓中的加仓逻辑 ──
        if shares > 0 and cash > 0:
            # 层2+：葛兰威尔 B2 回调加仓
            if layer >= 2:
                if ma_s > 0 and abs(price - ma_s) / ma_s <= pullback_tol:
                    prev_bias = abs(prev["close"] - ma_s) / ma_s
                    if prev_bias > pullback_tol and price > ma_s:
                        add_qty = int(cash * add_ratio / price) // 100 * 100
                        if add_qty > 0:
                            return {"action": "buy", "quantity": add_qty, "reason": f"葛兰威尔B2: 回踩MA{slow_ma}加仓"}

            # 层4：葛兰威尔 B3 — 跌破均线后快速收回
            if layer >= 4:
                if "ma_breach_date" not in strategy.__dict__:
                    strategy.ma_breach_date = None
                if price < ma_s:
                    if strategy.ma_breach_date is None:
                        strategy.ma_breach_date = len(df)
                else:
                    if strategy.ma_breach_date is not None:
                        days_below = len(df) - strategy.ma_breach_date
                        if days_below <= 3:
                            # 3日内收回，确认买入
                            recover_qty = int(cash * add_ratio / price) // 100 * 100
                            if recover_qty > 0:
                                strategy.ma_breach_date = None
                                return {"action": "buy", "quantity": recover_qty, "reason": f"葛兰威尔B3: {days_below}日内收回MA{slow_ma}"}
                        strategy.ma_breach_date = None

            # 层4：葛兰威尔 B4 超跌反弹
            if layer >= 4:
                if oversold < 0 and bias <= oversold:
                    bounce_qty = int(cash * add_ratio / price) // 100 * 100
                    if bounce_qty > 0:
                        return {"action": "buy", "quantity": bounce_qty, "reason": f"葛兰威尔B4: 超跌反弹(偏差{bias*100:.1f}%)"}

        return None

    # 存储层号供外部查看
    strategy.layer = layer
    strategy.params = p
    return strategy


# ── 预注册的分层策略（使用默认参数） ──
def _make_layer(name, layer, **overrides):
    p = DEFAULT_PARAMS.copy()
    p["layer"] = layer
    p.update(overrides)
    fn = _make_layered_strategy(p)
    fn._display_name = name
    return fn


STRATEGY_REGISTRY = {
    # 经典策略
    "均线金叉": _simple_ma_cross_strategy,
    "均线金叉增强版": _ma_cross_enhanced_strategy,
    "MACD金叉": _macd_cross_strategy,
    "RSI超卖反弹": _rsi_oversold_strategy,
    "布林带突破": _bollinger_breakout_strategy,
    "均线多头排列": _ma_bullish_alignment_strategy,
    "海龟交易法则": _turtle_trading_strategy,
    # 分层回测 L0-L4
    "L0-纯金叉死叉": _make_layer("L0-纯金叉死叉", 0),
    "L1-道氏趋势过滤": _make_layer("L1-道氏趋势过滤", 1),
    "L2-葛兰威尔加仓止盈": _make_layer("L2-葛兰威尔加仓止盈", 2),
    "L3-江恩回调共振": _make_layer("L3-江恩回调共振", 3),
    "L4-完整四大理论": _make_layer("L4-完整四大理论", 4),
}

INDEX_CODES = {"000001", "399001", "000300", "000016", "399006", "000688", "000905"}


def get_default_params() -> dict:
    return {"params": DEFAULT_PARAMS, "ranges": PARAM_RANGES}


def run_backtest(strategy_name: str, start_date: str, end_date: str,
                 code: str = "000300", custom_params: dict | None = None) -> dict:
    """执行策略回测，返回结构化结果。可传入 custom_params 覆盖默认参数。"""
    # 自定义参数 → 生成策略
    if custom_params:
        p = DEFAULT_PARAMS.copy()
        p.update(custom_params)
        # 推断 layer: 如果用户传入 layer 则用，否则默认完整层
        p.setdefault("layer", 4)
        strategy_fn = _make_layered_strategy(p)
    else:
        strategy_fn = STRATEGY_REGISTRY.get(strategy_name)

    if strategy_fn is None:
        known = [k for k in STRATEGY_REGISTRY if not k.startswith("ma_")]
        available = "、".join(sorted(set(known)))
        return {"error": f"未知策略「{strategy_name}」，可用: {available}，或传入 custom_params 自定义参数"}

    if not AKShareClient.check_available():
        return {"error": "数据源不可用，请确认 AKShare 或 Sina fetcher 已配置"}

    is_index = code in INDEX_CODES
    if is_index:
        kline = AKShareClient.get_index_data(code, start_date, end_date)
    else:
        kline = AKShareClient.get_daily_kline(code, start_date, end_date)

    if kline is None or kline.empty:
        return {"error": f"无法获取 {code} 在 {start_date}~{end_date} 的K线数据"}

    # 预计算均线和成交量指标（策略内部 _ensure_mas 会补充特定周期的）
    kline["ma5"] = kline["close"].rolling(5).mean()
    kline["ma20"] = kline["close"].rolling(20).mean()
    kline["ma200"] = kline["close"].rolling(200).mean()
    kline["vol_ma20"] = kline["volume"].rolling(20).mean()

    benchmark = AKShareClient.get_index_data("000300", start_date, end_date)
    result = BacktestEngine.run(
        kline_df=kline,
        strategy_fn=strategy_fn,
        strategy_name=strategy_name,
        benchmark_df=benchmark,
    )

    # 权益曲线
    equity_curve = []
    if result.equity_curve:
        df = kline.sort_values("date").reset_index(drop=True)
        for i, eq in enumerate(result.equity_curve):
            dt = str(df.iloc[min(i, len(df) - 1)]["date"])[:10]
            equity_curve.append({"date": dt, "equity": round(eq, 2)})

    return {
        "strategy_name": result.strategy_name,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "test_code": code,
        "metrics": {
            "trade_count": result.trade_count,
            "win_count": result.win_count,
            "win_rate": round(result.win_rate, 4),
            "max_drawdown": round(result.max_drawdown, 4),
            "annual_return": round(result.annual_return, 4),
            "profit_loss_ratio": round(result.profit_loss_ratio, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "max_consecutive_loss": result.max_consecutive_loss,
            "total_return": round(result.total_return, 4),
            "benchmark_return": round(result.benchmark_return, 4),
        },
        "equity_curve": equity_curve,
        "trades": [
            {
                "date": str(t.get("date", ""))[:10],
                "action": t.get("action", ""),
                "price": round(t.get("price", 0), 2),
                "quantity": t.get("quantity", 0),
                "reason": t.get("reason", ""),
            }
            for t in result.trades
        ],
        "overfit_risk": result.overfit_risk,
        "data_issues": result.data_issues,
    }
