"""
Agent 编排器 — 协调 4 个分析师 → 多空辩论 → PM 决策的完整流程

核心流程：
1. 数据准备：复用 analysis_service 获取技术面+基本面数据
2. 补充指标：计算 MACD/RSI/布林带/涨跌幅/换手率
3. 并行分析：4 个分析师同时调用 DeepSeek
4. 多空辩论：2-5 轮互相挑战
5. PM 决策：综合所有信息做出最终判断
"""

import time
import os
from typing import Optional
from openai import OpenAI
import numpy as np
import pandas as pd

from .prompts import (
    FUNDAMENTAL_ANALYST_PROMPT,
    TECHNICAL_ANALYST_PROMPT,
    SENTIMENT_ANALYST_PROMPT,
    RISK_ANALYST_PROMPT,
    BULL_DEBATER_PROMPT,
    BEAR_DEBATER_PROMPT,
    PM_DECISION_PROMPT,
    format_fundamental_data,
    format_technical_data,
    format_sentiment_data,
    format_risk_data,
    format_debate_report,
)
from ..services.analysis_service import analyze_stock
from ..data.akshare_client import AKShareClient


class AgentOrchestrator:
    """Agent 分析主编排器"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
    ):
        """
        初始化编排器

        :param api_key: DeepSeek API Key（默认从环境变量 DEEPSEEK_API_KEY 读取）
        :param base_url: API 地址（默认 https://api.deepseek.com/v1）
        :param model: 模型名（默认 deepseek-v4-flash）
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
        )
        self.model = model or os.getenv("AGENT_DEFAULT_MODEL", "deepseek-v4-flash")

        if not self.api_key:
            raise ValueError(
                "❌ 未配置 DeepSeek API Key。请设置环境变量 DEEPSEEK_API_KEY"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.total_tokens = 0  # 累计 token 用量

    # ═══════════════════════════════════════════════════════════════
    # 对外接口
    # ═══════════════════════════════════════════════════════════════

    def analyze(self, code: str, deep: bool = False) -> dict:
        """
        执行完整的 Agent 分析流程

        :param code: 6 位股票代码
        :param deep: 是否深度模式（更多辩论轮次 + Pro 模型）
        :return: 结构化分析结果
        """
        if deep:
            self.model = os.getenv("AGENT_DEEP_MODEL", "deepseek-v4-pro")
            max_debate_rounds = 5
            temperature = 0.5
        else:
            max_debate_rounds = 2
            temperature = 0.3

        self.total_tokens = 0
        start_time = time.time()

        # 1. 获取股票数据
        stock_data = self._gather_data(code)
        if stock_data is None:
            return {"error": f"无法获取 {code} 的数据"}

        # 2. 并行调用 4 个分析师
        analyst_results = self._run_analysts(stock_data, temperature)

        # 3. 多空辩论
        debate_transcript = self._run_debate(
            analyst_results, max_debate_rounds, temperature
        )

        # 4. PM 决策
        pm_result = self._run_pm(analyst_results, debate_transcript, temperature)

        elapsed = time.time() - start_time
        cost_rmb = self._estimate_cost()

        return {
            "code": code,
            "name": stock_data.get("name", code),
            "model": self.model,
            "decision": pm_result.get("decision", "无法判断"),
            "confidence": pm_result.get("confidence", 0),
            "confidence_level": pm_result.get("confidence_level", "低"),
            "core_reason": pm_result.get("core_reason", ""),
            "key_risk": pm_result.get("key_risk", ""),
            "analyst_reports": analyst_results,
            "debate": debate_transcript,
            "token_usage": {
                "total": self.total_tokens,
                "estimated_cost_rmb": round(cost_rmb, 4),
            },
            "elapsed_seconds": round(elapsed, 1),
            "disclaimer": "⚠️ 本分析由 AI 生成，仅用于学习研究，不构成投资建议",
        }

    # ═══════════════════════════════════════════════════════════════
    # 步骤 1：数据收集
    # ═══════════════════════════════════════════════════════════════

    def _gather_data(self, code: str) -> Optional[dict]:
        """收集股票数据 + 计算补充指标"""
        # 复用现有分析服务
        stock_data = analyze_stock(code)
        if stock_data is None:
            return None

        # 获取名称
        fin = stock_data.get("financial", {})
        name = fin.get("_name", code)
        stock_data["name"] = name

        # 获取原始 K 线计算补充指标
        kline = AKShareClient.get_daily_kline(code)
        if kline is not None and len(kline) >= 30:
            self._compute_extra_indicators(stock_data, kline)

        return stock_data

    def _compute_extra_indicators(self, stock_data: dict, kline: pd.DataFrame):
        """计算 MACD、RSI、布林带、涨跌幅、换手率等补充指标"""
        close = kline["close"].values.astype(float)
        high = kline["high"].values.astype(float)
        low = kline["low"].values.astype(float)
        volume = kline["volume"].values.astype(float)

        # MACD (12, 26, 9)
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = 2 * (dif - dea)

        stock_data["_macd"] = {
            "dif": round(float(dif.iloc[-1]), 4),
            "dea": round(float(dea.iloc[-1]), 4),
            "hist": round(float(hist.iloc[-1]), 4),
        }

        # RSI(14)
        delta = pd.Series(close).diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        stock_data["_rsi"] = {"value": round(float(rsi.iloc[-1]), 1)}

        # 布林带 (20, 2)
        ma20 = pd.Series(close).rolling(20).mean()
        std20 = pd.Series(close).rolling(20).std()
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        width_pct = ((upper - lower) / ma20 * 100).iloc[-1]

        stock_data["_boll"] = {
            "upper": round(float(upper.iloc[-1]), 2),
            "middle": round(float(ma20.iloc[-1]), 2),
            "lower": round(float(lower.iloc[-1]), 2),
            "width_pct": round(float(width_pct), 1),
        }

        # 涨跌幅
        latest_close = close[-1]
        stock_data["_pct_changes"] = {}
        for days, label in [(5, "近5日"), (20, "近20日")]:
            if len(close) > days:
                pct = (latest_close / close[-days - 1] - 1) * 100
                stock_data["_pct_changes"][label] = round(pct, 2)

        # 换手率（如果 K 线数据中有，没有则为 None）
        if "turnover" in kline.columns:
            stock_data["_turnover"] = round(float(kline["turnover"].iloc[-1]), 2)

    # ═══════════════════════════════════════════════════════════════
    # 步骤 2：并行调用分析师
    # ═══════════════════════════════════════════════════════════════

    def _run_analysts(self, stock_data: dict, temperature: float) -> dict:
        """并行调用 4 个分析师，返回各自的输出"""
        analysts = [
            ("fundamental", "基本面分析师", FUNDAMENTAL_ANALYST_PROMPT,
             format_fundamental_data(stock_data)),
            ("technical", "技术面分析师", TECHNICAL_ANALYST_PROMPT,
             format_technical_data(stock_data)),
            ("sentiment", "情绪面分析师", SENTIMENT_ANALYST_PROMPT,
             format_sentiment_data(stock_data)),
            ("risk", "风控分析师", RISK_ANALYST_PROMPT,
             format_risk_data(stock_data)),
        ]

        results = {}
        for key, name, system_prompt, data_text in analysts:
            results[key] = self._call_llm(
                system_prompt=system_prompt,
                user_message=f"请分析以下数据：\n\n{data_text}",
                temperature=temperature,
                label=name,
            )

        return results

    # ═══════════════════════════════════════════════════════════════
    # 步骤 3：多空辩论
    # ═══════════════════════════════════════════════════════════════

    def _run_debate(
        self, analyst_results: dict, max_rounds: int, temperature: float
    ) -> list[dict]:
        """执行多空辩论流程"""
        transcript = []
        debate_report = format_debate_report(analyst_results)

        # Round 1：各自陈述
        bull_msg = (
            f"请阅读以下分析师报告，提出你的看涨理由：\n\n{debate_report}"
        )
        bear_msg = (
            f"请阅读以下分析师报告，提出你的看跌理由：\n\n{debate_report}"
        )

        bull_statement = self._call_llm(
            system_prompt=BULL_DEBATER_PROMPT,
            user_message=bull_msg,
            temperature=temperature,
            label="多头研究员(R1)",
        )
        bear_statement = self._call_llm(
            system_prompt=BEAR_DEBATER_PROMPT,
            user_message=bear_msg,
            temperature=temperature,
            label="空头研究员(R1)",
        )

        transcript.append({
            "round": 1,
            "type": "opening",
            "bull": bull_statement,
            "bear": bear_statement,
        })

        # Round 2+：互相挑战
        for r in range(2, max_rounds + 1):
            # 空头挑战多头
            challenge_msg = (
                f"分析报告：\n\n{debate_report}\n\n"
                f"多头上一轮发言：\n{bull_statement}\n\n"
                f"空头上一轮发言：\n{bear_statement}\n\n"
                f"请针对多头最核心的看涨理由提出质疑。"
            )
            bear_challenge = self._call_llm(
                system_prompt=BEAR_DEBATER_PROMPT,
                user_message=challenge_msg,
                temperature=temperature,
                label=f"空头研究员(R{r})",
            )

            # 多头回应
            response_msg = (
                f"分析报告：\n\n{debate_report}\n\n"
                f"你上一轮发言：\n{bull_statement}\n\n"
                f"空头质疑：\n{bear_challenge}\n\n"
                f"请回应空头的质疑，同时质疑空头最核心的看跌理由。"
            )
            bull_response = self._call_llm(
                system_prompt=BULL_DEBATER_PROMPT,
                user_message=response_msg,
                temperature=temperature,
                label=f"多头研究员(R{r})",
            )

            transcript.append({
                "round": r,
                "type": "debate",
                "bear": bear_challenge,
                "bull": bull_response,
            })

            # 更新发言记录供下一轮使用
            bull_statement = bull_response
            bear_statement = bear_challenge

        return transcript

    # ═══════════════════════════════════════════════════════════════
    # 步骤 4：PM 决策
    # ═══════════════════════════════════════════════════════════════

    def _run_pm(
        self, analyst_results: dict, debate_transcript: list[dict], temperature: float
    ) -> dict:
        """调用 PM 做出最终决策"""
        # 格式化辩论记录
        debate_text_parts = []
        for entry in debate_transcript:
            r = entry["round"]
            debate_text_parts.append(f"## 第 {r} 轮")
            debate_text_parts.append(f"🐂 多头：{entry['bull'][:300]}")
            debate_text_parts.append(f"🐻 空头：{entry['bear'][:300]}")
            debate_text_parts.append("")

        debate_text = "\n".join(debate_text_parts)
        analyst_text = format_debate_report(analyst_results)

        pm_msg = (
            f"请综合以下分析师报告和辩论记录，做出最终决策。\n\n"
            f"{analyst_text}\n\n"
            f"## 辩论记录\n\n{debate_text}"
        )

        pm_output = self._call_llm(
            system_prompt=PM_DECISION_PROMPT,
            user_message=pm_msg,
            temperature=temperature,
            label="PM 决策",
        )

        return self._parse_pm_output(pm_output)

    def _parse_pm_output(self, text: str) -> dict:
        """解析 PM 输出为结构化字典"""
        result = {
            "decision": "无法判断",
            "confidence": 0,
            "confidence_level": "低",
            "core_reason": "",
            "key_risk": "",
            "raw": text,
        }

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("决策："):
                decision = line.replace("决策：", "").strip()
                result["decision"] = decision
            elif line.startswith("置信度："):
                conf_text = line.replace("置信度：", "").strip()
                # 解析 "中 (72%)" 格式
                if "(" in conf_text and ")" in conf_text:
                    level = conf_text.split("(")[0].strip()
                    pct_str = conf_text.split("(")[1].split("%")[0].strip()
                    try:
                        result["confidence"] = int(pct_str) / 100
                    except ValueError:
                        result["confidence"] = 0.5
                    result["confidence_level"] = level
            elif line.startswith("核心理由："):
                result["core_reason"] = line.replace("核心理由：", "").strip()
            elif line.startswith("关键风险："):
                result["key_risk"] = line.replace("关键风险：", "").strip()

        return result

    # ═══════════════════════════════════════════════════════════════
    # LLM 调用封装
    # ═══════════════════════════════════════════════════════════════

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        label: str = "",
    ) -> str:
        """调用 DeepSeek API，返回文本内容"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=1024,
            )

            # 统计 token
            usage = response.usage
            if usage:
                self.total_tokens += usage.total_tokens

            content = response.choices[0].message.content
            return content.strip() if content else "（无输出）"

        except Exception as e:
            prefix = f"[{label}] " if label else ""
            return f"❌ {prefix}调用失败：{str(e)}"

    # ═══════════════════════════════════════════════════════════════
    # 成本估算
    # ═══════════════════════════════════════════════════════════════

    def _estimate_cost(self) -> float:
        """
        估算 API 成本（人民币）
        DeepSeek V4 Flash：¥1/百万 token（输入），¥4/百万 token（输出）
        DeepSeek V4 Pro：¥2/百万 token（输入），¥8/百万 token（输出）
        简化处理：按均价 ¥0.0025/千 token 估算
        """
        # 简化：大部分是输入 token，按低价估算
        rate_per_1k = 0.001  # ¥0.001/千 token（约 Flash 输入价）
        if "pro" in self.model.lower():
            rate_per_1k = 0.002
        return self.total_tokens / 1000 * rate_per_1k
