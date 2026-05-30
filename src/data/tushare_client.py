"""
Tushare 数据客户端 — 复权因子 / 交易日历 / 停复牌
120积分即可使用，注册即送。
"""

import os
import pandas as pd
from typing import Optional

import tushare as ts

TOKEN = os.getenv("TUSHARE_TOKEN", "")
_pro = None


def _get_pro():
    """延迟初始化 Tushare Pro API"""
    global _pro
    if _pro is None:
        if not TOKEN:
            raise RuntimeError("TUSHARE_TOKEN 未设置，请在 .env 中配置")
        ts.set_token(TOKEN)
        _pro = ts.pro_api()
    return _pro


def get_adj_factor(
    ts_code: str = None,
    trade_date: str = None,
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """
    获取复权因子
    :param ts_code: 股票代码，格式 '000001.SZ'。传 None 获取当日全市场。
    :param trade_date: 交易日期 YYYYMMDD
    """
    pro = _get_pro()
    kwargs = {}
    if ts_code:
        kwargs["ts_code"] = ts_code
    if trade_date:
        kwargs["trade_date"] = trade_date
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    return pro.adj_factor(**kwargs)


def get_trade_cal(
    exchange: str = "SSE",
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """
    获取交易日历
    :param exchange: SSE上交所 SZSE深交所
    :return: DataFrame with cal_date, is_open (1开市 0休市), pretrade_date
    """
    pro = _get_pro()
    kwargs = {"exchange": exchange}
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date
    return pro.trade_cal(**kwargs)


def get_suspend_info(
    ts_code: str = None,
    suspend_date: str = None,
    resume_date: str = None,
) -> pd.DataFrame:
    """
    获取停复牌信息
    :param ts_code: 股票代码
    :param suspend_date: 停牌日期 YYYYMMDD
    """
    pro = _get_pro()
    kwargs = {}
    if ts_code:
        kwargs["ts_code"] = ts_code
    if suspend_date:
        kwargs["suspend_date"] = suspend_date
    if resume_date:
        kwargs["resume_date"] = resume_date
    return pro.suspend_d(**kwargs)


# ── 财务指标（ROE / 负债率 / 增速） ──────────────


def _code_to_ts_code(code: str) -> str:
    """普通代码 → Tushare格式: 600519 → 600519.SH, 000001 → 000001.SZ"""
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif code.startswith(("8", "4")):
        return f"{code}.BJ"
    raise ValueError(f"不支持的股票代码: {code}")


def get_financial_indicators(code: str, period: str = None) -> dict:
    """
    获取最新一期财务指标（Tushare fina_indicator，带1小时缓存）

    :param code: 股票代码，如 '600519'
    :param period: 报告期，如 '20251231'。不传取最新一期。
    :return: {"roe": 34.5, "debt_to_assets": 16.4, "or_yoy": 6.5, "profit_yoy": 8.2, ...}
             查询失败返回空 dict
    """
    import json
    import os
    import time

    # 缓存策略：API限频1次/小时，缓存1小时
    cache_dir = os.path.expanduser("~/.cache/stock_data")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"ts_fin_{code}.json")
    cache_ttl = 3600  # 1小时

    # 检查缓存
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < cache_ttl:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.loads(f.read())
                    if cached:
                        return cached
        except (json.JSONDecodeError, IOError):
            pass

    # 调API
    try:
        pro = _get_pro()
        ts_code = _code_to_ts_code(code)

        kwargs = {
            "ts_code": ts_code,
            "fields": "ts_code,end_date,roe,roe_yoy,debt_to_assets,or_yoy,"
                      "profit_dedt_yoy,grossprofit_margin,netprofit_margin",
        }
        if period:
            kwargs["period"] = period

        df = pro.fina_indicator(**kwargs)
        if df is None or df.empty:
            return {}

        # 优先取年报（end_date 以 1231 结尾），否则取最新
        annual = df[df["end_date"].str.endswith("1231")]
        if not annual.empty:
            latest = annual.iloc[0]  # 最新的年报
        else:
            latest = df.iloc[0]      # 兜底取最新一条
        result = {
            "roe": float(latest.get("roe", None)) if latest.get("roe") else None,
            "roe_yoy": float(latest.get("roe_yoy", None)) if latest.get("roe_yoy") else None,
            "debt_to_assets": float(latest.get("debt_to_assets", None)) if latest.get("debt_to_assets") else None,
            "or_yoy": float(latest.get("or_yoy", None)) if latest.get("or_yoy") else None,
            "profit_yoy": float(latest.get("profit_dedt_yoy", None)) if latest.get("profit_dedt_yoy") else None,
            "gross_margin": float(latest.get("grossprofit_margin", None)) if latest.get("grossprofit_margin") else None,
            "net_margin": float(latest.get("netprofit_margin", None)) if latest.get("netprofit_margin") else None,
            "report_date": str(latest.get("end_date", "")),
        }

        # 写缓存
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)

        return result
    except Exception as e:
        # 如果API调用失败但有旧缓存（即使过期），也返回旧缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    old = json.loads(f.read())
                    if old:
                        print(f"[Tushare] API失败，使用旧缓存 {code} (报告期: {old.get('report_date', '?')})")
                        return old
            except (json.JSONDecodeError, IOError):
                pass
        print(f"[Tushare] 获取财务指标失败 {code}: {e}")
        return {}


# ── 测试 ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("测试 1: 交易日历 (2026年5月)")
    cal = get_trade_cal(start_date="20260501", end_date="20260531")
    if not cal.empty:
        open_days = cal[cal["is_open"] == 1]
        print(f"  交易日: {len(open_days)} 天")
        print(f"  休市日: {len(cal) - len(open_days)} 天")

    print()
    print("=" * 50)
    print("测试 2: 停复牌 (最近)")
    susp = get_suspend_info(suspend_date="20260529")
    print(f"  当日停牌: {len(susp)} 只")

    print()
    print("=" * 50)
    print("测试 3: 复权因子 (贵州茅台)")
    adj = get_adj_factor(ts_code="600519.SH", start_date="20260501", end_date="20260529")
    print(f"  复权因子条数: {len(adj)}")
    if not adj.empty:
        print(f"  最新: {adj.iloc[-1]['trade_date']} factor={adj.iloc[-1]['adj_factor']}")

    print()
    print("✅ Tushare 客户端验证完成")
