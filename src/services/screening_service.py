"""选股服务 — 五维评分筛选"""

from ..data.akshare_client import AKShareClient
from ..scorer import StockScore, FundamentalScorer, MarketEnvScorer, TechnicalScorer


def _build_sector_map() -> tuple[dict[str, dict], list[dict]]:
    """获取热点板块，构建 板块名→(分类,得分) 映射 + 成分股反向索引"""
    sectors = AKShareClient.get_hot_sectors()
    if not sectors:
        return {}, [], {}

    # 板块名 → 涨跌幅+分类
    sector_info: dict[str, dict] = {}
    for s in sectors:
        name = s.get("name", "")
        cat = s.get("category", "一日游")
        chg = s.get("change", 0)
        sector_info[name] = {"change": chg, "category": cat}

    # 构建 股票代码→板块 反向映射（只覆盖热门板块）
    stock_to_sector: dict[str, str] = {}
    for s in sectors[:8]:  # 最多取前8个板块的成分股
        try:
            import akshare as ak
            df = ak.stock_board_industry_cons_em(symbol=s.get("name", ""))
            if df is not None and not df.empty:
                code_col = "代码" if "代码" in df.columns else "code"
                for code in df[code_col]:
                    stock_to_sector[str(code)] = s.get("name", "")
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

        for code in hot_codes:
            stock = StockScore(code=code)
            kline = AKShareClient.get_daily_kline(code)
            if kline is None or kline.empty:
                continue

            kline["ma5"] = kline["close"].rolling(5).mean()
            kline["ma20"] = kline["close"].rolling(20).mean()
            kline["ma60"] = kline["close"].rolling(60).mean()

            tech = TechnicalScorer.score(kline)
            stock.technical = tech["score"]
            stock.technical_desc = tech["desc"]

            stock.market_env = market_score
            fin = AKShareClient.get_financial_data(code)
            stock.name = fin.get("_name", "") or stock.name

            # 行业相对PE评分
            industry = fin.get("_industry", "") or ""
            stock.industry = industry
            fund = FundamentalScorer.score(fin, industry)
            stock.fundamental = fund["score"]
            stock.fundamental_desc = fund["desc"]

            # 按个股所属板块差异化热点评分
            ps, pd = _score_policy_for_stock(code, stock_to_sector, sector_info)
            stock.policy_hot = ps
            stock.policy_desc = pd or default_policy_desc
            stock.risk_control = 8

            stock.reasons = [
                "大盘环境: " + market_trend,
                "技术面: " + stock.technical_desc,
                "基本面: " + stock.fundamental_desc,
            ]
            stock.risk_points = ["市场系统性风险", "个股流动性风险"]
            stock.counter_conditions = ["大盘转防守时重新评估", "跌破60日线时重新评估"]
            stock.confirm_questions = [
                "该股票最近是否有大股东减持公告？",
                "同行业是否有更好的标的？",
                "政策/热点分是否有可靠事件和板块共振支撑？",
            ]

            if stock.in_pool:
                result["candidates"].append({
                    "code": stock.code,
                    "name": stock.name,
                    "industry": stock.industry,
                    "scores": {
                        "market_env": stock.market_env,
                        "policy_hot": stock.policy_hot,
                        "fundamental": stock.fundamental,
                        "technical": stock.technical,
                        "risk_control": stock.risk_control,
                    },
                    "total": round(stock.total, 1),
                    "in_pool": stock.in_pool,
                    "technical_desc": stock.technical_desc,
                    "fundamental_desc": stock.fundamental_desc,
                    "policy_desc": stock.policy_desc,
                    "reasons": stock.reasons,
                    "risk_points": stock.risk_points,
                    "counter_conditions": stock.counter_conditions,
                    "confirm_questions": stock.confirm_questions,
                })

        result["total_in_pool"] = len(result["candidates"])

    except Exception as e:
        result["error"] = str(e)

    return result
