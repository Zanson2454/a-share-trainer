"""K线形态识别 — 三角形、头肩顶底、旗形、双顶底、单边趋势"""

import pandas as pd
import numpy as np


def _find_peaks(series: pd.Series, order: int = 5):
    """找局部极大值"""
    from scipy.signal import argrelextrema
    idx = argrelextrema(series.values, np.greater_equal, order=order)[0]
    return [(int(i), float(series.iloc[i])) for i in idx]


def _find_troughs(series: pd.Series, order: int = 5):
    """找局部极小值"""
    from scipy.signal import argrelextrema
    idx = argrelextrema(series.values, np.less_equal, order=order)[0]
    return [(int(i), float(series.iloc[i])) for i in idx]


def _pct(a: float, b: float) -> float:
    """两个价格之间的百分比差"""
    return abs(a - b) / max(abs(a), abs(b)) * 100 if max(abs(a), abs(b)) > 0 else 0


def _merge_close_points(points: list[tuple[int, float]], min_dist: int = 8,
                        keep_higher: bool = True) -> list[tuple[int, float]]:
    """合并太近的极值点，保留更极端的（峰值保留更高的，谷值保留更低的）"""
    if not points:
        return points
    merged = [points[0]]
    for idx, val in points[1:]:
        prev_idx, prev_val = merged[-1]
        if idx - prev_idx <= min_dist:
            if (keep_higher and val > prev_val) or (not keep_higher and val < prev_val):
                merged[-1] = (idx, val)
        else:
            merged.append((idx, val))
    return merged


def _linear_trend(series: pd.Series) -> tuple[float, float]:
    """线性回归斜率及方向一致性（R²）"""
    y = series.values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    y_pred = np.polyval(np.polyfit(x, y, 1), x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return float(slope), float(r2)


def _swing_size(pct_val: float, n_bars: int) -> str:
    """判断波动幅度等级"""
    if pct_val > 40:
        return "极大"
    elif pct_val > 25:
        return "大"
    elif pct_val > 15:
        return "中等"
    return "小"


def _unilateral_confidence(r2: float, move_pct: float, n_bars: int, bars_from_end: int) -> int:
    """单边趋势置信度 0-10 分"""
    score = 0
    # R² 拟合度 (0-4)
    if r2 >= 0.9: score += 4
    elif r2 >= 0.8: score += 3
    elif r2 >= 0.7: score += 2
    elif r2 >= 0.6: score += 1
    # 幅度 (0-3)
    if move_pct >= 40: score += 3
    elif move_pct >= 25: score += 2
    elif move_pct >= 15: score += 1
    # 持续时间 (0-2)
    if n_bars >= 60: score += 2
    elif n_bars >= 30: score += 1
    # 时效性 (0-1)
    if bars_from_end <= 5: score += 1
    return min(10, score)


def _classical_confidence(broken: bool, move_pct: float, n_bars: int) -> int:
    """经典形态置信度 0-10 分"""
    if broken:
        score = 6
    else:
        score = 3
    if move_pct >= 10: score += 2
    elif move_pct >= 5: score += 1
    if n_bars >= 40: score += 2
    elif n_bars >= 20: score += 1
    return min(10, score)


def detect_patterns(kline: pd.DataFrame) -> list[dict]:
    """
    检测K线形态，返回已识别的形态列表。
    """
    if kline is None or len(kline) < 40:
        return []

    close = kline["close"].reset_index(drop=True)
    high = kline["high"].reset_index(drop=True)
    low = kline["low"].reset_index(drop=True)
    dates = kline["date"].reset_index(drop=True)
    n = len(close)

    # 均线
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    # 找极值点
    peaks = _merge_close_points(_find_peaks(high, order=5), min_dist=8, keep_higher=True)
    troughs = _merge_close_points(_find_troughs(low, order=5), min_dist=8, keep_higher=False)
    peaks_wide = _merge_close_points(_find_peaks(high, order=8), min_dist=12, keep_higher=True)
    troughs_wide = _merge_close_points(_find_troughs(low, order=8), min_dist=12, keep_higher=False)

    patterns = []

    # 经典形态只看最近一段（避免检测到几年前的历史形态）
    recent_start = max(0, n - 250)
    recent_peaks = [p for p in peaks if p[0] >= recent_start]
    recent_troughs = [t for t in troughs if t[0] >= recent_start]
    recent_peaks_wide = [p for p in peaks_wide if p[0] >= recent_start]
    recent_troughs_wide = [t for t in troughs_wide if t[0] >= recent_start]

    # ── 单边趋势（优先检测，覆盖长周期）──
    for p in _find_unilateral_downtrend(high, low, close, ma20, ma60, n):
        patterns.append(p)
    for p in _find_unilateral_uptrend(high, low, close, ma20, ma60, n):
        patterns.append(p)

    # ── 经典形态（仅最近250根K线）──
    for p in _find_double_top(recent_peaks_wide, close, n):
        patterns.append(p)
    for p in _find_double_bottom(recent_troughs_wide, close, n):
        patterns.append(p)
    for p in _find_head_shoulders_top(recent_peaks, close, n):
        patterns.append(p)
    for p in _find_head_shoulders_bottom(recent_troughs, close, n):
        patterns.append(p)
    for p in _find_ascending_triangle(recent_peaks_wide, recent_troughs_wide, close, n):
        patterns.append(p)
    for p in _find_bull_flag(high, low, close, n):
        patterns.append(p)
    for p in _find_bear_flag(high, low, close, n):
        patterns.append(p)

    # 转日期
    for p in patterns:
        si, ei = p["start_idx"], p["end_idx"]
        p["start_date"] = str(dates.iloc[min(si, n - 1)])[:10]
        p["end_date"] = str(dates.iloc[min(ei, n - 1)])[:10]
        p.pop("start_idx", None)
        p.pop("end_idx", None)

    # 去重：同类型只保留最显著的（按 price_move 降序）
    best = {}
    for p in patterns:
        key = p["name"]
        move = abs(p.get("price_move", 0))
        if key not in best or move > abs(best[key].get("price_move", 0)):
            best[key] = p

    # 单边上涨和单边下跌冲突：保留最近发生的（start_date 更晚的）
    uni_up = best.pop("单边上涨", None)
    uni_down = best.pop("单边下跌", None)
    if uni_up and uni_down:
        # 比较哪个开始得更晚（即更近期的趋势）
        if uni_up.get("start_date", "") >= uni_down.get("start_date", ""):
            best["单边上涨"] = uni_up
        else:
            best["单边下跌"] = uni_down
    elif uni_up:
        best["单边上涨"] = uni_up
    elif uni_down:
        best["单边下跌"] = uni_down

    # 清理内部字段
    for p in best.values():
        p.pop("price_move", None)

    return sorted(best.values(), key=lambda x: x["end_date"])


# ═══════════════════════════════════════════════════════════════
# 单边趋势
# ═══════════════════════════════════════════════════════════════

def _find_unilateral_downtrend(high, low, close, ma20, ma60, n):
    """
    单边下跌：从最近的重要高点持续下跌。
    检测从窗口内最高点至今的下跌趋势，兼容"先涨后跌"的V型反转。
    """
    window = min(120, n)
    seg_high = high.iloc[-window:]
    seg_low = low.iloc[-window:]
    seg_close = close.iloc[-window:]

    # 找窗口内最高点
    hh_pos = int(np.argmax(seg_high.values))  # 窗口内相对位置
    hh_val = float(seg_high.max())

    # 只看最高点之后的走势
    after_high_close = seg_close.iloc[hh_pos:]
    after_high_low = seg_low.iloc[hh_pos:]
    if len(after_high_close) < 10:
        return []

    # 最高点之后的跌幅
    ll_val = float(after_high_low.min())
    decline = (hh_val - ll_val) / hh_val * 100 if hh_val > 0 else 0
    if decline < 15:
        return []

    # 线性回归确认最高点之后的下跌趋势
    slope, r2 = _linear_trend(after_high_close)
    if slope >= 0:
        return []
    if r2 < 0.5:
        return []

    last_close = float(close.iloc[-1])
    ma20_val = float(ma20.iloc[-1]) if pd.notna(ma20.iloc[-1]) else last_close
    ma60_val = float(ma60.iloc[-1]) if pd.notna(ma60.iloc[-1]) else last_close

    from_peak = (hh_val - last_close) / hh_val * 100 if hh_val > 0 else 0

    near_bottom = last_close < ll_val * 1.05
    if near_bottom:
        signal = "B"
        signal_desc = "已跌至前低附近，可能超跌反弹"
    elif last_close < ma60_val:
        signal = "观望"
        signal_desc = "均线空头排列，继续观望"
    else:
        signal = "观望"
        signal_desc = "下跌趋势中，等待企稳信号"

    target = ll_val + (hh_val - ll_val) * 0.236
    dur_bars = len(after_high_close)
    conf = _unilateral_confidence(r2, decline, dur_bars, 0)

    return [{
        "name": "单边下跌",
        "type": "bearish",
        "start_idx": n - window + hh_pos,
        "end_idx": n - 1,
        "entry_price": round(last_close, 2),
        "stop_loss": round(ll_val * 0.95, 2),
        "target": round(target, 2),
        "confidence": conf,
        "description": (
            f"从高点{hh_val:.1f}持续下跌至{ll_val:.1f}，跌幅{decline:.1f}%，"
            f"距高点已跌{from_peak:.1f}%。{signal_desc}"
        ),
        "signal": signal,
        "signal_price": round(last_close, 2),
        "price_move": -decline,
    }]


def _find_unilateral_uptrend(high, low, close, ma20, ma60, n):
    """
    单边上涨：从最近的重要低点持续上涨。
    检测从窗口内最低点至今的上涨趋势，兼容"先跌后涨"的V型反转。
    """
    window = min(120, n)
    seg_high = high.iloc[-window:]
    seg_low = low.iloc[-window:]
    seg_close = close.iloc[-window:]

    # 找窗口内最低点
    ll_pos = int(np.argmin(seg_low.values))
    ll_val = float(seg_low.min())

    # 只看最低点之后的走势
    after_low_close = seg_close.iloc[ll_pos:]
    after_low_high = seg_high.iloc[ll_pos:]
    if len(after_low_close) < 10:
        return []

    # 最低点之后的涨幅
    hh_val = float(after_low_high.max())
    rise = (hh_val - ll_val) / ll_val * 100 if ll_val > 0 else 0
    if rise < 15:
        return []

    # 线性回归确认最低点之后的上涨趋势
    slope, r2 = _linear_trend(after_low_close)
    if slope <= 0:
        return []
    if r2 < 0.5:
        return []

    last_close = float(close.iloc[-1])
    ma20_val = float(ma20.iloc[-1]) if pd.notna(ma20.iloc[-1]) else last_close
    ma60_val = float(ma60.iloc[-1]) if pd.notna(ma60.iloc[-1]) else last_close

    from_low = (last_close - ll_val) / ll_val * 100 if ll_val > 0 else 0

    near_top = last_close > hh_val * 0.95
    if near_top:
        signal = "S"
        signal_desc = "已涨至前高附近，可能见顶回落"
    elif last_close > ma20_val:
        signal = "观望"
        signal_desc = "多头趋势延续，但已不宜追高"
    else:
        signal = "观望"
        signal_desc = "上涨趋势中，关注回调确认"

    target = hh_val + (hh_val - ll_val) * 0.236
    dur_bars = len(after_low_close)
    conf = _unilateral_confidence(r2, rise, dur_bars, 0)

    return [{
        "name": "单边上涨",
        "type": "bullish",
        "start_idx": n - window + ll_pos,
        "end_idx": n - 1,
        "entry_price": round(last_close, 2),
        "stop_loss": round(ll_val + (hh_val - ll_val) * 0.618, 2),
        "target": round(target, 2),
        "confidence": conf,
        "description": (
            f"从低点{ll_val:.1f}持续上涨至{hh_val:.1f}，涨幅{rise:.1f}%，"
            f"距低点已涨{from_low:.1f}%。{signal_desc}"
        ),
        "signal": signal,
        "signal_price": round(last_close, 2),
        "price_move": rise,
    }]


# ═══════════════════════════════════════════════════════════════
# 双顶 / 双底
# ═══════════════════════════════════════════════════════════════

def _find_double_top(peaks, close, n):
    """双顶：两个相近高度的峰，中间有谷"""
    results = []
    for i in range(len(peaks) - 2):
        p1_idx, p1_val = peaks[i]
        for j in range(i + 1, min(i + 4, len(peaks))):
            p2_idx, p2_val = peaks[j]
            if p2_idx - p1_idx < 10:
                continue
            if _pct(p1_val, p2_val) > 5:
                continue
            between = close.iloc[p1_idx:p2_idx + 1]
            valley_val = float(between.min())
            valley_idx = int(between.idxmin()) if hasattr(between, 'idxmin') else p1_idx + int(np.argmin(between.values))
            if (p1_val - valley_val) / p1_val < 0.03:
                continue
            neckline = valley_val
            broken = float(close.iloc[-1]) < neckline if p2_idx < n - 3 else False
            target = neckline - (p1_val - neckline)
            move_pct = (p1_val - valley_val) / p1_val * 100
            conf = _classical_confidence(broken, move_pct, p2_idx - p1_idx)
            results.append({
                "name": "双顶(M顶)",
                "type": "bearish",
                "start_idx": p1_idx,
                "end_idx": p2_idx,
                "entry_price": round(neckline, 2),
                "stop_loss": round(max(p1_val, p2_val) * 1.02, 2),
                "target": round(max(target, 0), 2),
                "confidence": conf,
                "description": f"两峰{p1_val:.1f}/{p2_val:.1f}，颈线{neckline:.1f}" +
                               ("，已跌破颈线，看跌信号" if broken else "，等待跌破颈线确认"),
                "signal": "S" if broken else "观望",
                "signal_price": round(neckline, 2),
                "price_move": -(p1_val - valley_val) / p1_val * 100,
            })
    return results


def _find_double_bottom(troughs, close, n):
    """双底：两个相近深度的谷，中间有峰"""
    results = []
    for i in range(len(troughs) - 2):
        t1_idx, t1_val = troughs[i]
        for j in range(i + 1, min(i + 4, len(troughs))):
            t2_idx, t2_val = troughs[j]
            if t2_idx - t1_idx < 10:
                continue
            if _pct(t1_val, t2_val) > 5:
                continue
            between = close.iloc[t1_idx:t2_idx + 1]
            peak_val = float(between.max())
            if (peak_val - t1_val) / t1_val < 0.03:
                continue
            neckline = peak_val
            broken = float(close.iloc[-1]) > neckline if t2_idx < n - 3 else False
            target = neckline + (neckline - t1_val)
            move_pct = (neckline - t1_val) / t1_val * 100
            conf = _classical_confidence(broken, move_pct, t2_idx - t1_idx)
            results.append({
                "name": "双底(W底)",
                "type": "bullish",
                "start_idx": t1_idx,
                "end_idx": t2_idx,
                "entry_price": round(neckline, 2),
                "stop_loss": round(min(t1_val, t2_val) * 0.98, 2),
                "target": round(target, 2),
                "confidence": conf,
                "description": f"两底{t1_val:.1f}/{t2_val:.1f}，颈线{neckline:.1f}" +
                               ("，已突破颈线，看涨信号" if broken else "，等待突破颈线确认"),
                "signal": "B" if broken else "观望",
                "signal_price": round(neckline, 2),
                "price_move": (neckline - t1_val) / t1_val * 100,
            })
    return results


# ═══════════════════════════════════════════════════════════════
# 头肩顶 / 头肩底
# ═══════════════════════════════════════════════════════════════

def _find_head_shoulders_top(peaks, close, n):
    """头肩顶：三个峰，中峰最高，左右峰相近且低于中峰"""
    results = []
    for i in range(len(peaks) - 2):
        left = peaks[i]
        head = peaks[i + 1]
        right = peaks[i + 2]
        if not (head[1] > left[1] and head[1] > right[1]):
            continue
        if _pct(left[1], right[1]) > 8:
            continue
        if right[0] - left[0] < 20:
            continue
        between_lh = close.iloc[left[0]:head[0] + 1]
        valley_l = float(between_lh.min())
        between_hr = close.iloc[head[0]:right[0] + 1]
        valley_r = float(between_hr.min())
        neckline = (valley_l + valley_r) / 2
        broken = float(close.iloc[-1]) < neckline if right[0] < n - 3 else False
        target = neckline - (head[1] - neckline)
        move_pct = (head[1] - neckline) / head[1] * 100
        conf = _classical_confidence(broken, move_pct, right[0] - left[0])
        results.append({
            "name": "头肩顶",
            "type": "bearish",
            "start_idx": left[0],
            "end_idx": right[0],
            "entry_price": round(neckline, 2),
            "stop_loss": round(head[1] * 1.02, 2),
            "target": round(max(target, 0), 2),
            "confidence": conf,
            "description": f"左肩{left[1]:.1f}/头{head[1]:.1f}/右肩{right[1]:.1f}，颈线{neckline:.1f}" +
                           ("，已跌破颈线" if broken else ""),
            "signal": "S" if broken else "观望",
            "signal_price": round(neckline, 2),
            "price_move": -(head[1] - neckline) / head[1] * 100,
        })
    return results


def _find_head_shoulders_bottom(troughs, close, n):
    """头肩底：三个谷，中谷最低，左右谷相近且高于中谷"""
    results = []
    for i in range(len(troughs) - 2):
        left = troughs[i]
        head = troughs[i + 1]
        right = troughs[i + 2]
        if not (head[1] < left[1] and head[1] < right[1]):
            continue
        if _pct(left[1], right[1]) > 8:
            continue
        if right[0] - left[0] < 20:
            continue
        between_lh = close.iloc[left[0]:head[0] + 1]
        peak_l = float(between_lh.max())
        between_hr = close.iloc[head[0]:right[0] + 1]
        peak_r = float(between_hr.max())
        neckline = (peak_l + peak_r) / 2
        broken = float(close.iloc[-1]) > neckline if right[0] < n - 3 else False
        target = neckline + (neckline - head[1])
        move_pct = (neckline - head[1]) / head[1] * 100
        conf = _classical_confidence(broken, move_pct, right[0] - left[0])
        results.append({
            "name": "头肩底",
            "type": "bullish",
            "start_idx": left[0],
            "end_idx": right[0],
            "entry_price": round(neckline, 2),
            "stop_loss": round(head[1] * 0.98, 2),
            "target": round(target, 2),
            "confidence": conf,
            "description": f"左肩{left[1]:.1f}/头{head[1]:.1f}/右肩{right[1]:.1f}，颈线{neckline:.1f}" +
                           ("，已突破颈线" if broken else ""),
            "signal": "B" if broken else "观望",
            "signal_price": round(neckline, 2),
            "price_move": (neckline - head[1]) / head[1] * 100,
        })
    return results


# ═══════════════════════════════════════════════════════════════
# 上升三角形
# ═══════════════════════════════════════════════════════════════

def _find_ascending_triangle(peaks, troughs, close, n):
    """上升三角形：水平上沿 + 逐步抬高的下沿"""
    results = []
    recent_peaks = peaks[-6:] if len(peaks) >= 6 else peaks
    recent_troughs = troughs[-6:] if len(troughs) >= 6 else troughs
    if len(recent_peaks) < 3 or len(recent_troughs) < 3:
        return results

    # 检查上沿是否水平（最后几个峰在同一水平）
    peak_vals = [p[1] for p in recent_peaks[-4:]]
    peak_mean = sum(peak_vals) / len(peak_vals)
    if max(peak_vals) - min(peak_vals) > peak_mean * 0.03:
        return results

    # 检查下沿是否逐步抬高
    trough_vals = [t[1] for t in recent_troughs[-3:]]
    if len(trough_vals) < 3:
        return results
    if not all(trough_vals[i] < trough_vals[i + 1] for i in range(len(trough_vals) - 1)):
        return results

    resistance = peak_mean
    last_close = float(close.iloc[-1])
    broken = last_close > resistance
    base = trough_vals[0]
    target = resistance + (resistance - base)
    move_pct = (target - resistance) / resistance * 100
    conf = _classical_confidence(broken, move_pct, recent_peaks[-1][0] - recent_troughs[0][0])
    results.append({
        "name": "上升三角形",
        "type": "bullish",
        "start_idx": recent_troughs[0][0],
        "end_idx": recent_peaks[-1][0],
        "entry_price": round(resistance, 2),
        "stop_loss": round(trough_vals[-1] * 0.98, 2),
        "target": round(target, 2),
        "confidence": conf,
        "description": f"压力{resistance:.1f}水平，支撑从{base:.1f}逐步抬高至{trough_vals[-1]:.1f}" +
                       ("，已突破" if broken else "，等待突破"),
        "signal": "B" if broken else "观望",
        "signal_price": round(resistance, 2),
        "price_move": (target - resistance) / resistance * 100,
    })
    return results


# ═══════════════════════════════════════════════════════════════
# 旗形
# ═══════════════════════════════════════════════════════════════

def _find_bull_flag(high, low, close, n):
    """上升旗形：急涨（旗杆）+ 下斜整理（旗面）"""
    results = []
    if n < 30:
        return results
    window = min(60, n)
    seg_close = close.iloc[-window:]
    seg_high = high.iloc[-window:]
    seg_low = low.iloc[-window:]

    # 找旗杆：窗口前半段的急涨
    mid = window // 2
    first_half = seg_close.iloc[:mid]
    if len(first_half) < 5:
        return results

    first_max = float(first_half.max())
    first_min = float(first_half.min())
    pole_move = (first_max - first_min) / first_min if first_min > 0 else 0

    # 旗杆涨幅需要 >8%
    if pole_move < 0.08:
        return results

    # 旗面高点是否下斜（整理阶段）
    pole_high = float(seg_high.iloc[mid:].max())
    q1 = seg_high.iloc[mid:mid + (window - mid) // 2]
    q2 = seg_high.iloc[mid + (window - mid) // 2:]
    if len(q1) < 2 or len(q2) < 2:
        return results
    q1_high = float(q1.max())
    q2_high = float(q2.max())
    if not (q2_high < q1_high * 1.01):
        return results

    # 回调不能太深
    recent_low = float(seg_low.iloc[-10:].min())
    if recent_low < first_min * 0.97:
        return results

    last_close_val = float(close.iloc[-1])
    upper_line = pole_high
    broken = last_close_val > upper_line
    pole_height = first_max - first_min
    target = upper_line + pole_height

    flag_conf = _classical_confidence(broken, pole_move * 100, window)
    results.append({
        "name": "上升旗形",
        "type": "bullish",
        "start_idx": n - window,
        "end_idx": n - 1,
        "entry_price": round(upper_line, 2),
        "stop_loss": round(recent_low * 0.98, 2),
        "target": round(target, 2),
        "confidence": flag_conf,
        "description": f"旗杆涨幅{pole_move*100:.1f}%，旗面整理中" +
                       ("，已突破上轨" if broken else "，等待突破上轨"),
        "signal": "B" if broken else "观望",
        "signal_price": round(upper_line, 2),
        "price_move": pole_move * 100,
    })
    return results


def _find_bear_flag(high, low, close, n):
    """下跌旗形：急跌（旗杆）+ 上斜反弹（旗面）"""
    results = []
    if n < 30:
        return results
    window = min(60, n)
    seg_close = close.iloc[-window:]
    seg_high = high.iloc[-window:]
    seg_low = low.iloc[-window:]

    mid = window // 2
    first_half = seg_close.iloc[:mid]
    if len(first_half) < 5:
        return results

    first_max = float(first_half.max())
    first_min = float(first_half.min())
    pole_drop = (first_max - first_min) / first_max if first_max > 0 else 0

    # 旗杆跌幅需要 >8%
    if pole_drop < 0.08:
        return results

    # 旗面低点是否上斜
    pole_low = float(seg_low.iloc[mid:].min())
    q1 = seg_low.iloc[mid:mid + (window - mid) // 2]
    q2 = seg_low.iloc[mid + (window - mid) // 2:]
    if len(q1) < 2 or len(q2) < 2:
        return results
    q1_low = float(q1.min())
    q2_low = float(q2.min())
    if not (q2_low > q1_low * 0.99):
        return results

    # 反弹不能太高
    recent_high = float(seg_high.iloc[-10:].max())
    if recent_high > first_max * 0.97:
        return results

    last_close_val = float(close.iloc[-1])
    lower_line = pole_low
    broken = last_close_val < lower_line
    pole_height = first_max - first_min
    target = lower_line - pole_height

    flag_conf = _classical_confidence(broken, pole_drop * 100, window)
    results.append({
        "name": "下跌旗形",
        "type": "bearish",
        "start_idx": n - window,
        "end_idx": n - 1,
        "entry_price": round(lower_line, 2),
        "stop_loss": round(recent_high * 1.02, 2),
        "target": round(max(target, 0), 2),
        "confidence": flag_conf,
        "description": f"旗杆跌幅{pole_drop*100:.1f}%，旗面反弹中" +
                       ("，已跌破下轨" if broken else "，等待跌破下轨"),
        "signal": "S" if broken else "观望",
        "signal_price": round(lower_line, 2),
        "price_move": -pole_drop * 100,
    })
    return results
