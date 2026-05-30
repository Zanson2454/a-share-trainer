"""自然语言选股服务 — 动态从全市场筛选"""

import re
import concurrent.futures
from datetime import datetime, timedelta
from ..data.akshare_client import AKShareClient
from ..scorer import StockScore, FundamentalScorer, MarketEnvScorer, TechnicalScorer

_RECENT_DAYS = 180
_STOCK_TIMEOUT = 8
_MAX_CANDIDATES = 8

# 行业关键词 → 名称匹配模式（用于在全市场股票名称中筛选）
INDUSTRY_NAME_PATTERNS: dict[str, list[str]] = {
    "白酒": ["茅台", "五粮", "老窖", "汾酒", "洋河", "古井", "酒鬼", "水井坊", "舍得", "今世缘", "口子窖", "迎驾", "金种子"],
    "消费": ["食品", "饮料", "乳", "肉", "调味", "榨菜", "酵母", "面包", "零食", "百货", "超市", "电器", "家居", "家纺", "服装"],
    "新能源": ["新能源", "锂", "风电", "光伏", "阳光", "隆基", "通威", "晶澳", "天合", "明阳", "金风", "亿纬", "国轩", "欣旺达", "储能"],
    "电池": ["电池", "锂", "亿纬", "国轩", "欣旺达", "德赛", "冠宇", "珠海冠宇"],
    "光伏": ["光伏", "阳光", "隆基", "通威", "晶澳", "天合", "晶科", "福斯特", "大全", "锦浪", "固德威"],
    "医药": ["药", "医", "生物", "恒瑞", "复星", "片仔癀", "云南白药", "同仁堂", "天坛", "华兰", "康泰", "智飞", "沃森", "长春高新"],
    "医疗": ["医疗", "器械", "迈瑞", "联影", "微创", "心脉", "健帆"],
    "半导体": ["半导体", "微电子", "集成", "中芯", "华虹", "北方华创", "中微", "韦尔", "兆易", "紫光", "长电", "通富"],
    "芯片": ["芯片", "中芯", "华虹", "韦尔", "兆易", "紫光", "卓胜", "汇顶", "圣邦", "北京君正"],
    "银行": ["银行", "工商", "建设", "农业", "中国银行", "招商", "兴业", "浦发", "民生", "中信", "光大", "平安", "交通"],
    "保险": ["保险", "平安", "人寿", "太保", "新华", "人保", "太平"],
    "券商": ["证券", "中信", "华泰", "海通", "国泰", "招商", "广发", "申万", "东方", "光大", "方正"],
    "科技": ["科技", "软件", "网络", "数据", "云", "信息", "通信", "计算机", "电子", "光电", "海康", "大华", "科大讯飞", "用友"],
    "AI": ["智能", "AI", "机器", "自动化", "机器人", "科大讯飞", "商汤", "云从", "旷视", "寒武纪", "海光"],
    "汽车": ["汽车", "比亚迪", "长城", "吉利", "长安", "广汽", "上汽", "赛力斯", "蔚来", "理想", "小鹏"],
    "家电": ["电器", "家电", "美的", "格力", "海尔", "老板", "苏泊尔", "九阳", "小熊", "科沃斯"],
    "地产": ["地产", "万科", "保利", "招商蛇口", "金地", "绿地", "华润", "龙湖", "碧桂园"],
    "军工": ["航空", "航天", "兵器", "船舶", "军工", "中航", "沈飞", "航发", "中国卫星", "北斗"],
    "有色": ["有色", "矿业", "铜", "铝", "金", "稀土", "紫金", "洛阳钼", "北方稀土", "中国铝业"],
    "煤炭": ["煤", "神华", "中煤", "兖矿", "陕西煤", "潞安"],
    "电力": ["电力", "发电", "长江电力", "华能", "华电", "国电", "核电", "三峡"],
    "化工": ["化工", "化学", "万华", "恒力", "荣盛", "龙盛", "华鲁"],
    "钢铁": ["钢铁", "宝钢", "鞍钢", "首钢", "河钢", "马钢"],
}

# 风格 → 市值/PE筛选条件
STYLE_FILTERS: dict[str, dict] = {
    "蓝筹": {"min_mktcap": 500, "max_pe": 30},
    "白马": {"min_mktcap": 200, "max_pe": 50},
    "成长": {"min_mktcap": 100, "max_pe": 100},
    "龙头": {"min_mktcap": 1000, "max_pe": 200},
}

# 技术面关键词
TECHNICAL_KEYWORDS = {
    "突破": "关注突破关键阻力位的股票",
    "金叉": "均线金叉信号明显",
    "放量": "成交量放大，资金进场迹象",
    "多头": "均线多头排列",
    "上升趋势": "处于上升趋势通道",
    "底部": "处于底部区域或有反弹迹象",
    "强势": "相对大盘表现强势",
}

# 财务面关键词 → (sina_field, range, label)
FUNDAMENTAL_KEYWORDS = {
    "高ROE": ("roe", (15, 100), "ROE > 15%"),
    "高增长": ("profit_growth", (20, 1000), "利润增速 > 20%"),
    "低PE": ("pe", (0, 30), "PE < 30"),
    "低估值": ("pe", (0, 20), "PE < 20"),
    "低负债": ("debt_ratio", (0, 50), "资产负债率 < 50%"),
    "高毛利": ("roe", (10, 100), "ROE > 10%"),
    "高分红": ("dividend", (2, 20), "股息率 > 2%"),
}


def parse_query(query: str) -> dict:
    """解析自然语言查询，返回筛选意图（不再包含硬编码股票代码）"""
    q = query.strip()
    result = {
        "raw": q,
        "name_keywords": [],
        "industry_name": "",
        "style_name": "",
        "style_filter": {},
        "fundamental_filters": [],
        "technical_notes": [],
        "explanation": [],
    }

    # 行业匹配 → 收集名称关键词
    for keyword, patterns in INDUSTRY_NAME_PATTERNS.items():
        if keyword in q:
            result["name_keywords"].extend(patterns)
            if not result["industry_name"]:
                result["industry_name"] = keyword
            result["explanation"].append(f"行业「{keyword}」→ 按名称匹配{len(patterns)}个关键词")

    # 风格匹配 → 市值/PE筛选条件
    for keyword, filter_cfg in STYLE_FILTERS.items():
        if keyword in q:
            result["style_filter"] = filter_cfg
            if not result["style_name"]:
                result["style_name"] = keyword
            result["explanation"].append(
                f"风格「{keyword}」→ 市值>{filter_cfg['min_mktcap']}亿 PE<{filter_cfg['max_pe']}"
            )

    # 技术面匹配
    for keyword, desc in TECHNICAL_KEYWORDS.items():
        if keyword in q:
            result["technical_notes"].append(desc)
            result["explanation"].append(f"技术面: {desc}")

    # 财务面匹配
    for keyword, (field, rng, desc) in FUNDAMENTAL_KEYWORDS.items():
        if keyword in q:
            result["fundamental_filters"].append({"field": field, "range": rng, "label": desc})
            result["explanation"].append(f"财务条件: {desc}")

    return result


def _get_full_stock_list():
    """获取全市场股票列表（原始数据，无过滤），返回 DataFrame 或 None"""
    import pandas as pd
    fetcher = AKShareClient._load_sina_fetcher()
    if fetcher is not None:
        try:
            df = fetcher.get_stock_list()
            if df is not None and not df.empty:
                # 排除ST和退市
                df = df[~df["name"].str.contains("ST|退市|N |C ", na=False)]
                return df
        except Exception as e:
            print(f"[Sina] 获取全市场列表失败: {e}")

    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            code_col = "code" if "code" in df.columns else "代码"
            name_col = "name" if "name" in df.columns else "名称"
            df = df.rename(columns={code_col: "code", name_col: "name"})
            df = df[~df["name"].str.contains("ST|退市|N |C ", na=False)]
            # AKShare只返回代码和名称，没有PE/PB/市值
            df["pe"] = 0.0
            df["pb"] = 0.0
            df["mktcap"] = 0.0
            return df
    except Exception as e:
        print(f"[AKShare] 获取股票列表失败: {e}")

    return None


def _filter_stock_pool(intent: dict) -> tuple[list[dict], str]:
    """从全市场动态筛选候选股"""
    import pandas as pd
    pool = _get_full_stock_list()
    if pool is None or pool.empty:
        return [], "全市场数据获取失败"

    total_count = len(pool)

    # 名称关键词筛选（最先执行，缩小范围）
    name_kws = intent.get("name_keywords", [])
    if name_kws:
        pattern = "|".join(re.escape(kw) for kw in name_kws)
        mask = pool["name"].str.contains(pattern, case=False, na=False)
        pool = pool[mask]

    # 风格筛选（市值+PE）—— 只在有Sina数据时执行
    sf = intent.get("style_filter", {})
    if sf:
        min_cap = sf.get("min_mktcap", 0)
        max_pe = sf.get("max_pe", 500)
        has_mktcap = (pool["mktcap"] > 0).any()
        has_pe = (pool["pe"] > 0).any()
        if has_mktcap:
            pool = pool[pool["mktcap"] >= min_cap]
        if has_pe:
            pool = pool[(pool["pe"] > 0) & (pool["pe"] <= max_pe)]

    # PE范围筛选（来自财务关键词）
    for ff in intent.get("fundamental_filters", []):
        if ff["field"] == "pe" and (pool["pe"] > 0).any():
            lo, hi = ff["range"]
            pool = pool[(pool["pe"] >= lo) & (pool["pe"] <= hi)]

    # 如果没有匹配且没有任何筛选条件，返回提示
    if pool.empty and not name_kws and not sf:
        pool = pool.head(0)  # keep empty but valid

    # 排序：优先按市值，没有市值则按名称
    if (pool["mktcap"] > 0).any():
        pool = pool.sort_values("mktcap", ascending=False)
    if len(pool) > _MAX_CANDIDATES * 3:
        pool = pool.head(_MAX_CANDIDATES * 3)

    candidates = []
    for _, row in pool.iterrows():
        candidates.append({
            "code": str(row["code"]),
            "name": str(row.get("name", "")),
            "pe": float(row.get("pe", 0)) if row.get("pe") and row["pe"] > 0 else None,
            "pb": float(row.get("pb", 0)) if row.get("pb") and row["pb"] > 0 else None,
            "mktcap": float(row.get("mktcap", 0)),
            "change_pct": float(row.get("changepercent", 0)),
        })

    source = f"全市场{total_count}只动态筛选"
    if name_kws:
        source += f"（行业: {intent.get('industry_name', '')}）"
    if sf:
        source += f"（风格: {intent.get('style_name', '')}）"

    return candidates, source


def _score_market_env() -> tuple[float, str]:
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
                     policy_score: float, policy_desc: str,
                     raw_query: str, fundamental_filters: list[dict],
                     technical_notes: list[str]) -> dict | None:
    """对单只股票评分，出错时返回 None"""
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=_RECENT_DAYS * 2)).strftime("%Y%m%d")
        kline = AKShareClient.get_daily_kline(code, start_date, end_date)
        if kline is None or kline.empty:
            return None

        kline["ma5"] = kline["close"].rolling(5).mean()
        kline["ma20"] = kline["close"].rolling(20).mean()
        kline["ma60"] = kline["close"].rolling(60).mean()

        tech = TechnicalScorer.score(kline)

        fin = AKShareClient.get_financial_data(code)
        fund = FundamentalScorer.score(fin)

        stock = StockScore(code=code)
        stock.name = fin.get("_name", "") or ""
        stock.technical = tech["score"]
        stock.technical_desc = tech["desc"]
        stock.fundamental = fund["score"]
        stock.fundamental_desc = fund["desc"]
        stock.market_env = market_score
        stock.policy_hot = policy_score
        stock.policy_desc = policy_desc
        stock.risk_control = 8

        for ff in fundamental_filters:
            field_val = fin.get(ff["field"])
            if field_val is not None and not (ff["range"][0] <= field_val <= ff["range"][1]):
                return None

        tech_bonus = 0
        for note in technical_notes:
            if "金叉" in note and "金叉" in stock.technical_desc:
                tech_bonus += 3
            if "多头" in note and "多头" in stock.technical_desc:
                tech_bonus += 3
            if "放量" in note and "放量" in stock.technical_desc:
                tech_bonus += 3
        stock.technical = min(25, stock.technical + tech_bonus)

        stock.reasons = [
            f"查询意图: {raw_query}",
            "大盘环境: " + market_trend,
            "技术面: " + stock.technical_desc,
            "基本面: " + stock.fundamental_desc,
        ]
        stock.risk_points = ["市场系统性风险", "个股流动性风险"]
        stock.counter_conditions = ["大盘转防守时重新评估", "跌破60日线时重新评估"]
        stock.confirm_questions = [
            "该股票最近是否有大股东减持公告？",
            "同行业是否有更好的标的？",
            f"该股是否符合「{raw_query}」的所有条件？",
        ]

        return {
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
            "in_pool": stock.total >= 70,
            "technical_desc": stock.technical_desc,
            "fundamental_desc": stock.fundamental_desc,
            "policy_desc": stock.policy_desc,
            "reasons": stock.reasons,
            "risk_points": stock.risk_points,
            "counter_conditions": stock.counter_conditions,
            "confirm_questions": stock.confirm_questions,
        }
    except Exception:
        return None


def screen_by_natural_language(query: str) -> dict:
    """自然语言选股入口 — 动态从全市场筛选"""
    intent = parse_query(query)

    result: dict = {
        "query": query,
        "parsed": {
            "industry": intent["industry_name"],
            "style": intent["style_name"],
            "technical_notes": intent["technical_notes"],
            "fundamental_filters": intent["fundamental_filters"],
            "explanation": intent["explanation"],
        },
        "market_score": 10.0,
        "market_trend": "震荡",
        "candidates": [],
        "pool_source": "",
        "total_in_pool": 0,
    }

    if not AKShareClient.check_available():
        result["error"] = "数据源不可用"
        return result

    try:
        # Step 1: 动态筛选候选池
        candidates, pool_source = _filter_stock_pool(intent)
        result["pool_source"] = pool_source

        if not candidates:
            result["error"] = "没有匹配的股票，请尝试更宽泛的条件"
            return result

        # Step 2: 大盘环境
        sectors = AKShareClient.get_hot_sectors()
        sector_names = [s.get("name", "") for s in sectors] if sectors else []
        policy_score = 15 if sectors else 5
        policy_desc = "热点板块: " + "、".join(sector_names[:3]) if sector_names else "板块/政策数据待人工确认"
        market_score, market_trend = _score_market_env()
        result["market_score"] = market_score
        result["market_trend"] = market_trend

        # Step 3: 并发K线评分（取前 N 只）
        codes = [c["code"] for c in candidates[:_MAX_CANDIDATES]]
        name_map = {c["code"]: c["name"] for c in candidates}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(codes))) as executor:
            futures = {
                executor.submit(
                    _score_one_stock, code,
                    market_score, market_trend,
                    policy_score, policy_desc,
                    intent["raw"], intent["fundamental_filters"], intent["technical_notes"],
                ): code for code in codes
            }
            for future in concurrent.futures.as_completed(futures):
                code = futures[future]
                try:
                    candidate = future.result(timeout=_STOCK_TIMEOUT)
                    if candidate is not None:
                        if not candidate["name"] and code in name_map:
                            candidate["name"] = name_map[code]
                        result["candidates"].append(candidate)
                except concurrent.futures.TimeoutError:
                    print(f"[NL筛选] {code} 超时，跳过")
                except Exception as e:
                    print(f"[NL筛选] {code} 异常: {e}")

        result["candidates"].sort(key=lambda c: c["total"], reverse=True)
        result["total_in_pool"] = sum(1 for c in result["candidates"] if c["in_pool"])

    except Exception as e:
        result["error"] = str(e)

    return result


EXAMPLE_QUERIES = [
    "高ROE低PE的白酒股",
    "放量突破的科技龙头",
    "低估值高分红的蓝筹股",
    "金叉多头的成长股",
    "底部放量的医药股",
    "低负债高增长的新能源",
]
