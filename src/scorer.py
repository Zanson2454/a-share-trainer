"""
选股评分模型 — 五维100分制
大盘环境(20) + 政策/热点(20) + 基本面(25) + 技术面(25) + 风控(10)
总分 >= 70 进入观察池
"""
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


# 行业PE参考区间（基于A股历史分位数）
INDUSTRY_PE_RANGES: dict[str, tuple[float, float, str]] = {
    # 行业关键词 → (低估阈值, 高估阈值, 行业名)
    "银行": (4, 10, "银行"),
    "保险": (8, 20, "保险"),
    "券商": (10, 30, "券商"),
    "地产": (5, 15, "地产"),
    "钢铁": (6, 20, "钢铁"),
    "煤炭": (6, 15, "煤炭"),
    "有色": (15, 40, "有色"),
    "化工": (12, 35, "化工"),
    "电力": (10, 25, "电力"),
    "建筑": (6, 20, "建筑"),
    "白酒": (20, 50, "白酒"),
    "消费": (20, 50, "消费"),
    "食品": (20, 45, "食品饮料"),
    "家电": (12, 30, "家电"),
    "医药": (25, 60, "医药"),
    "医疗": (25, 60, "医疗器械"),
    "新能源": (15, 50, "新能源"),
    "光伏": (15, 50, "光伏"),
    "电池": (20, 55, "电池"),
    "汽车": (10, 35, "汽车"),
    "半导体": (30, 80, "半导体"),
    "芯片": (30, 80, "芯片"),
    "科技": (25, 70, "科技"),
    "AI": (30, 80, "AI"),
    "军工": (30, 70, "军工"),
    "传媒": (15, 40, "传媒"),
}


def _match_industry_pe_range(industry: str) -> tuple[float, float] | None:
    """根据行业名称模糊匹配PE参考区间，返回 (低估阈值, 高估阈值)"""
    if not industry:
        return None
    for kw, (lo, hi, _) in INDUSTRY_PE_RANGES.items():
        if kw in industry:
            return (lo, hi)
    return None


@dataclass
class StockScore:
    """个股评分卡"""
    code: str
    name: str = ""
    industry: str = ""

    # 五维得分
    market_env: float = 0     # 大盘环境 0-20
    policy_hot: float = 0     # 政策/热点匹配 0-20
    fundamental: float = 0    # 基本面质量 0-25
    technical: float = 0      # 技术面形态 0-25
    risk_control: float = 0   # 风险控制清晰度 0-10

    # 详情
    reasons: list[str] = field(default_factory=list)
    technical_desc: str = ""
    fundamental_desc: str = ""
    policy_desc: str = ""
    risk_points: list[str] = field(default_factory=list)
    counter_conditions: list[str] = field(default_factory=list)
    confirm_questions: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.market_env + self.policy_hot + self.fundamental + self.technical + self.risk_control

    @property
    def in_pool(self) -> bool:
        """是否进入观察池"""
        return self.total >= 70

    def to_report(self) -> str:
        """生成评分报告"""
        lines = [
            f"## {self.name}（{self.code}）",
            f"- 所属行业: {self.industry}",
            f"- 综合评分: {self.total}/100 {'✅ 入池' if self.in_pool else '❌ 不入池'}",
            "",
            "| 维度 | 得分 | 满分 |",
            "|------|------|------|",
            f"| 大盘环境 | {self.market_env} | 20 |",
            f"| 政策/热点 | {self.policy_hot} | 20 |",
            f"| 基本面质量 | {self.fundamental} | 25 |",
            f"| 技术面形态 | {self.technical} | 25 |",
            f"| 风险控制 | {self.risk_control} | 10 |",
            "",
            "### 入选原因",
        ]
        for r in self.reasons:
            lines.append(f"- {r}")

        lines += [
            "",
            f"### 技术形态: {self.technical_desc}",
            "",
            f"### 基本面摘要: {self.fundamental_desc}",
            "",
            f"### 政策/热点关联: {self.policy_desc}",
            "",
            "### 反证条件",
        ]
        for c in self.counter_conditions:
            lines.append(f"- {c}")

        lines += ["", "### 风险点"]
        for r in self.risk_points:
            lines.append(f"- {r}")

        lines += ["", "### 需人工确认"]
        for q in self.confirm_questions:
            lines.append(f"- [ ] {q}")

        lines += ["", "> ⚠️ 仅用于学习研究，不构成投资建议"]
        return "\n".join(lines)


class MarketEnvScorer:
    """大盘环境评分器（0-20分）"""

    @staticmethod
    def score(index_change: float, volume_ratio: float, trend: str) -> float:
        """
        :param index_change: 指数涨跌幅
        :param volume_ratio: 成交量相对20日均量比值
        :param trend: 趋势 '进攻'/'震荡'/'防守'
        """
        score = 10.0
        # 趋势得分
        if trend == "进攻":
            score += 5
        elif trend == "防守":
            score -= 3
        # 涨跌幅得分
        if index_change > 1:
            score += 3
        elif index_change < -1:
            score -= 3
        # 量能得分
        if volume_ratio > 1.2:
            score += 2
        return max(0, min(20, score))

    @staticmethod
    def classify_market(data: dict) -> str:
        """
        分类大盘环境
        :return: '进攻' / '震荡' / '防守'
        """
        # 基于20日均线判断
        if data.get("price_above_ma20", True):
            return "进攻"
        elif data.get("price_above_ma60", True):
            return "震荡"
        else:
            return "防守"


class TechnicalScorer:
    """技术面评分器（0-25分），含趋势强度和放量位置判断"""

    @staticmethod
    def score(kline_df) -> dict:
        """
        :param kline_df: K线DataFrame (需含 close, ma5, ma20, ma60, volume)
        :return: {score, desc, signals}
        """
        if kline_df is None or kline_df.empty:
            return {"score": 0, "desc": "数据不足", "signals": []}

        score = 12.5
        signals = []
        last = kline_df.iloc[-1]

        # 趋势判断
        close = last.get("close", 0)
        ma5 = last.get("ma5", close)
        ma20 = last.get("ma20", close)
        ma60 = last.get("ma60", close)

        if close > ma5 > ma20:
            score += 5
            signals.append("多头排列")
        elif close < ma5 < ma20:
            score -= 3
            signals.append("空头排列")

        if close > ma60:
            score += 3
            signals.append("站上60日线")
        else:
            score -= 1

        # MA60 斜率（趋势强度）
        ma60_series = kline_df["ma60"].dropna()
        if len(ma60_series) >= 20:
            recent = ma60_series.tail(20)
            x = np.arange(len(recent))
            slope = np.polyfit(x, recent.values, 1)[0]
            avg_ma60 = recent.mean()
            if avg_ma60 > 0:
                slope_pct = slope / avg_ma60 * 100
                if slope_pct > 0.5:
                    score += 2
                    signals.append("MA60上行")
                elif slope_pct < -0.5:
                    score -= 2
                    signals.append("MA60下行")

        # 成交量 + 位置判断
        avg_vol = kline_df["volume"].tail(20).mean()
        vol = last.get("volume", 0)
        if vol > avg_vol * 1.5 and ma60 > 0:
            # 判断价格相对位置：高位还是低位
            price_vs_ma60 = close / ma60
            if price_vs_ma60 < 0.95:
                score += 3
                signals.append("低位放量")
            elif price_vs_ma60 < 1.05:
                score += 2
                signals.append("均线附近放量")
            elif price_vs_ma60 > 1.2:
                score -= 2
                signals.append("高位放量(谨慎)")
            else:
                score += 1
                signals.append("放量")

        return {
            "score": max(0, min(25, score)),
            "desc": "；".join(signals) if signals else "无明显信号",
            "signals": signals,
        }


class FundamentalScorer:
    """基本面评分器（0-25分），引入行业相对估值"""

    @staticmethod
    def score(financial: dict, industry: str = "") -> dict:
        """
        :param financial: {pe, pb, roe, revenue_growth, profit_growth, debt_ratio}
        :param industry: 所属行业，用于行业相对PE判断
        """
        score = 12.5
        desc_parts = []

        pe = financial.get("pe")
        pe_range = _match_industry_pe_range(industry) if industry else None

        if pe and pe > 0:
            if pe_range:
                lo, hi = pe_range
                if pe <= lo:
                    score += 4
                    desc_parts.append(f"PE={pe:.1f}(低于{industry}均值{lo})，低估")
                elif pe <= hi:
                    score += 2
                    desc_parts.append(f"PE={pe:.1f}({industry}区间{lo}-{hi})，合理")
                elif pe > hi * 2:
                    score -= 3
                    desc_parts.append(f"PE={pe:.1f}(远超{industry}高估线{hi})，偏高")
                else:
                    score -= 1
                    desc_parts.append(f"PE={pe:.1f}(高于{industry}区间上限{hi})")
            else:
                # 无行业参考，使用通用阈值
                if pe < 20:
                    score += 3
                    desc_parts.append(f"PE={pe:.1f}偏低")
                elif pe < 40:
                    score += 1
                    desc_parts.append(f"PE={pe:.1f}合理")
                elif pe > 100:
                    score -= 3
                    desc_parts.append(f"PE={pe:.1f}偏高")
        elif pe == 0:
            desc_parts.append("PE=0（可能亏损）")

        roe = financial.get("roe")
        if roe and roe > 15:
            score += 4
            desc_parts.append(f"ROE={roe:.1f}%优秀")
        elif roe and roe > 8:
            score += 2
            desc_parts.append(f"ROE={roe:.1f}%良好")

        profit_g = financial.get("profit_growth")
        if profit_g and profit_g > 20:
            score += 3
            desc_parts.append(f"利润增速{profit_g:.1f}%高增长")

        debt = financial.get("debt_ratio")
        if debt and debt < 50:
            score += 3
            desc_parts.append(f"负债率{debt:.1f}%低风险")
        elif debt and debt > 80:
            score -= 3
            desc_parts.append(f"负债率{debt:.1f}%高杠杆")

        return {
            "score": max(0, min(25, score)),
            "desc": "；".join(desc_parts) if desc_parts else "财务数据不足",
        }
