"""选股服务 — 五维评分筛选"""

import concurrent.futures
import socket

from ..data.akshare_client import AKShareClient
from ..scorer import StockScore, FundamentalScorer, MarketEnvScorer, TechnicalScorer

_STOCK_TIMEOUT = 8  # 单只股票评分超时（秒）
_MAX_WORKERS = 6    # 并发线程数


def _fetch_sector_stocks(sector_name: str) -> tuple[str, list[str]]:
    """获取单个板块的成分股列表（带超时）"""
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(5)
        import akshare as ak
        df = ak.stock_board_industry_cons_em(symbol=sector_name)
        if df is not None and not df.empty:
            code_col = "代码" if "代码" in df.columns else "code"
            return sector_name, [str(c) for c in df[code_col]]
    except Exception:
        pass
    finally:
        socket.setdefaulttimeout(old_timeout)
    return sector_name, []


def _build_sector_map() -> tuple[dict[str, dict], list[dict], dict[str, str]]:
    """获取热点板块，并发构建板块成分股反向索引"""
    sectors = AKShareClient.get_hot_sectors()
    if not sectors:
        return {}, [], {}

    sector_info: dict[str, dict] = {}
    for s in sectors:
        name = s.get("name", "")
        sector_info[name] = {"change": s.get("change", 0), "category": s.get("category", "一日游")}

    # 并发获取前8个板块的成分股
    stock_to_sector: dict[str, str] = {}
    top_sectors = sectors[:8]
    if top_sectors:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(top_sectors))) as executor:
            futures = {executor.submit(_fetch_sector_stocks, s.get("name", "")): s for s in top_sectors}
            for future in concurrent.futures.as_completed(futures):
                try:
                    sname, codes = future.result(timeout=6)
                    for c in codes:
                        stock_to_sector[c] = sname
                except concurrent.futures.TimeoutError:
                    pass
                except Exception:
                    pass

    return sector_info, sectors, stock_to_sector


def _score_policy_for_stock(code: str, stock_to_sector: dict[str, str],
                            sector_info: dict[str, dict]) -> tuple[float, str]:
    """按个股所属板块返回差异化热点得分"""
    sector_name = stock_to_sector.get(code, "")
    if sector_name and sector_name in sector_info:
        info = sector_info[sector_name]
        cat = info["category"]
        chg = info["change"]
        if cat == "主线":
            # 15-20分，涨幅越大越接近20
            score = min(20, 15 + chg / 2)
            desc = f"所属「{sector_name}」为主线(涨{chg:+.1f}%)"
        elif cat == "支线":
            score = min(15, 10 + chg / 2)
            desc = f"所属「{sector_name}」为支线(涨{chg:+.1f}%)"
        else:
            score = max(5, 10 - abs(chg) / 2)
            desc = f"所属「{sector_name}」为一曰游(涨{chg:+.1f}%)"
        return score, desc
    # 未匹配到热门板块
    return 8, "未匹配当前热门板块"


def _score_market_env() -> tuple[float, str]:
    """用上证指数估算大盘环境；失败时返回中性分"""
    index_df = AKShareClient.get_index_data("000001")
    if index_df is None or index_df.empty:
        return 10.0, "大盘数据待确认"

    latest = index_df.iloc[-1]
    prev_close = index_df.iloc[-2]["close"] if len(index_df) > 1 else latest["close"]
    index_change = (latest["close"] - prev_close) / prev_close * 100 if prev_close else 0
    avg_volume = index_df["volume"].tail(20).mean()
    volume_ratio = latest["volume"] / avg_volume if avg_volume else 1
    trend = MarketEnvScorer.classify_market({
        "price_above_ma20": latest["close"] > index_df["close"].tail(20).mean(),
        "price_above_ma60": latest["close"] > index_df["close"].tail(60).mean(),
    })
    return MarketEnvScorer.score(index_change, volume_ratio, trend), trend


def _score_one_stock(code: str, market_score: float, market_trend: str,
                     default_policy_desc: str,
                     stock_to_sector: dict[str, str],
                     sector_info: dict[str, dict]) -> dict | None:
    """对单只股票评分，出错时返回 None"""
    try:
        kline = AKShareClient.get_daily_kline(code)
        if kline is None or kline.empty:
            return None

        kline["ma5"] = kline["close"].rolling(5).mean()
        kline["ma20"] = kline["close"].rolling(20).mean()
        kline["ma60"] = kline["close"].rolling(60).mean()

        tech = TechnicalScorer.score(kline)
        fin = AKShareClient.get_financial_data(code)
        industry = fin.get("_industry", "") or ""
        fund = FundamentalScorer.score(fin, industry)

        ps, pd = _score_policy_for_stock(code, stock_to_sector, sector_info)

        return {
            "code": code,
            "name": fin.get("_name", "") or "",
            "industry": industry,
            "scores": {
                "market_env": market_score,
                "policy_hot": ps,
                "fundamental": fund["score"],
                "technical": tech["score"],
                "risk_control": 8,
            },
            "total": round(market_score + ps + fund["score"] + tech["score"] + 8, 1),
            "in_pool": market_score + ps + fund["score"] + tech["score"] + 8 >= 70,
            "technical_desc": tech["desc"],
            "fundamental_desc": fund["desc"],
            "policy_desc": pd or default_policy_desc,
            "reasons": [
                "大盘环境: " + market_trend,
                "技术面: " + tech["desc"],
                "基本面: " + fund["desc"],
            ],
            "risk_points": ["市场系统性风险", "个股流动性风险"],
            "counter_conditions": ["大盘转防守时重新评估", "跌破60日线时重新评估"],
            "confirm_questions": [
                "该股票最近是否有大股东减持公告？",
                "同行业是否有更好的标的？",
                "政策/热点分是否有可靠事件和板块共振支撑？",
            ],
        }
    except Exception:
        return None


def screen_stocks(codes: list[str] | None = None) -> dict:
    """五维评分筛选候选股"""
    result: dict = {
        "market_score": 10.0,
        "market_trend": "震荡",
        "candidates": [],
        "pool_source": "",
        "total_in_pool": 0,
        "error": None,
    }

    if not AKShareClient.check_available():
        result["error"] = "AKShare 未安装，无法获取实时行情"
        return result

    try:
        sector_info, sectors, stock_to_sector = _build_sector_map()
        sector_names = [s.get("name", "") for s in sectors] if sectors else []
        default_policy_desc = "热点板块: " + "、".join(sector_names[:3]) if sector_names else "板块/政策数据待人工确认"
        market_score, market_trend = _score_market_env()
        result["market_score"] = market_score
        result["market_trend"] = market_trend

        # 候选池：涨幅前20，按 涨跌幅×成交额 排序（强度+流动性）
        hot_codes = list(codes or [])
        pool_source = "用户指定"
        if not hot_codes:
            try:
                import akshare as ak
                spot_df = ak.stock_zh_a_spot_em()
                if spot_df is not None and not spot_df.empty:
                    top20 = spot_df.nlargest(20, "涨跌幅").copy()
                    # 按 涨跌幅×成交额 排序，兼顾强度和流动性
                    if "成交额" in top20.columns:
                        top20["_rank"] = top20["涨跌幅"].astype(float) * top20["成交额"].astype(float).rank(pct=True)
                        top20 = top20.sort_values("_rank", ascending=False)
                    hot_codes = top20["代码"].tolist()
                    pool_source = "实时行情（涨幅前20，按强度×流动性排序）"
                else:
                    result["error"] = "无法获取实时行情数据"
                    return result
            except Exception as e:
                result["error"] = f"获取实时行情失败: {e}"
                return result

        result["pool_source"] = pool_source

        # 并发评分
        with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    _score_one_stock, code,
                    market_score, market_trend,
                    default_policy_desc, stock_to_sector, sector_info,
                ): code for code in hot_codes
            }
            for future in concurrent.futures.as_completed(futures):
                code = futures[future]
                try:
                    candidate = future.result(timeout=_STOCK_TIMEOUT)
                    if candidate is not None:
                        result["candidates"].append(candidate)
                except concurrent.futures.TimeoutError:
                    print(f"[筛选] {code} 超时，跳过")
                except Exception as e:
                    print(f"[筛选] {code} 异常: {e}")

        result["candidates"].sort(key=lambda c: c["total"], reverse=True)
        result["total_in_pool"] = sum(1 for c in result["candidates"] if c["in_pool"])

    except Exception as e:
        result["error"] = str(e)

    return result
