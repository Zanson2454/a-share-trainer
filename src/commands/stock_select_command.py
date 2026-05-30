"""
/选股 — 五维评分模型筛选候选股
"""
from ..data.akshare_client import AKShareClient
from ..scorer import StockScore, FundamentalScorer, MarketEnvScorer, TechnicalScorer
from ..obsidian_sync import ObsidianSync


DEFAULT_UNIVERSE = ["600519", "000858", "300750", "002594", "601318"]


def _score_market_env() -> tuple[float, str]:
    """用上证指数估算大盘环境；失败时返回中性分。"""
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


def execute(args: list = None) -> str:
    """执行 /选股 命令"""
    if not AKShareClient.check_available():
        return "❌ AKShare 未安装。请运行：`" + AKShareClient.install_guide() + "`"

    lines = []
    lines.append("## 🔍 选股评分 — 五维模型")
    lines.append("")
    lines.append("> 评分标准：大盘环境(20) + 政策/热点(20) + 基本面(25) + 技术面(25) + 风控(10)")
    lines.append("> 总分 ≥ 70 进入观察池")
    lines.append("")

    candidates = []

    try:
        sectors = AKShareClient.get_hot_sectors()
        sector_names = [s.get("name", "") for s in sectors] if sectors else []
        policy_score = 15 if sectors else 5
        policy_desc = "热点板块: " + "、".join(sector_names[:3]) if sectors else "板块/政策数据待人工确认"
        market_score, market_desc = _score_market_env()

        lines.append("### 候选股评分")
        lines.append("")
        if not sectors:
            lines.append("> ⚠️ 板块数据暂不可用，政策/热点分按待确认处理")
            lines.append("")

        hot_codes = []
        hot_source = "实时行情"
        try:
            # 优先用 Sina 全A股列表筛选
            pool = AKShareClient.get_stock_pool(min_mktcap=50, max_pe=200)
            if not pool.empty:
                # 取市值前20只作为候选
                hot_codes = pool["code"].head(20).tolist()
                hot_source = f"Sina全A股筛选(市值>50亿,PE<200,共{len(pool)}只)"
            else:
                hot_source = "Sina数据为空 → 默认观察池"
        except Exception:
            hot_source = "数据获取失败 → 默认观察池"

        if not hot_codes:
            hot_codes = DEFAULT_UNIVERSE

        # 告知用户候选池来源
        lines.append(f"### 候选池来源: {hot_source}")
        lines.append(f"观察池: {' '.join(hot_codes[:5])}")
        if hot_source != "实时行情":
            lines.append("> ⚠️ 当前使用默认观察池，非实时热门股。配置 akshare 后可获取真实涨幅榜。")
        lines.append("")

        for code in hot_codes[:5]:
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
            fund = FundamentalScorer.score(fin)
            stock.fundamental = fund["score"]
            stock.fundamental_desc = fund["desc"]

            stock.policy_hot = policy_score
            stock.policy_desc = policy_desc
            stock.risk_control = 8

            stock.reasons = [
                "大盘环境: " + market_desc,
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
                candidates.append(stock)

        if candidates:
            lines.append("共 " + str(len(candidates)) + " 只股票进入观察池")
            lines.append("")
            for c in candidates:
                lines.append(c.to_report())
                lines.append("")
                lines.append("---")
                lines.append("")
                ObsidianSync.save_stock_analysis(c.code, c.name, c.to_report())
        else:
            lines.append("⚠️ 当前无股票满足入池条件（总分>=70）")
            lines.append("建议：等待更好的市场环境，或放宽部分条件重新筛选")

    except Exception as e:
        lines.append("❌ 选股过程出错: " + str(e))

    lines.append("")
    lines.append("> ⚠️ 仅用于学习研究，不构成投资建议")
    return "\n".join(lines)
