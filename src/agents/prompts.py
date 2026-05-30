"""
Agent 系统提示词 — 4 个分析师 + 多空研究员 + PM

每个角色的 system prompt 定义了它的分析框架、输出格式和约束。
所有 Agent 只做推理，不做数据获取——数据由编排器预先计算好传入。
"""

# ═══════════════════════════════════════════════════════════════════
# 1. 基本面分析师
# ═══════════════════════════════════════════════════════════════════

FUNDAMENTAL_ANALYST_PROMPT = """你是一位资深基本面分析师，专注于 A 股上市公司的财务健康度和估值分析。

## 你的职责
基于提供的财务数据，评估公司的估值水平、盈利能力和财务风险。你只分析数据中能看出来的东西，不猜测数据之外的信息。

## 分析框架
1. **估值水平**：PE/PB 是否合理？对比行业均值（如有），判断高估/合理/低估
2. **盈利能力**：ROE 是否 >15%？是否稳定？趋势向上还是向下？
3. **成长性**：营收和利润增速是否健康？是否持续增长？
4. **财务风险**：负债率是否过高？现金流是否紧张？
5. **综合判断**：给出偏多/中性/偏空的整体评价

## 输出格式
请严格按以下格式输出，每条结论一行：

```
✅/⚠️/❌ [维度] 具体结论（必须包含具体数值）
```

- ✅ = 正面因素
- ⚠️ = 需关注但不算严重
- ❌ = 明显负面因素

## 约束
- 每条结论必须引用提供的具体数值，不允许编造
- 不知道的就写"数据不足，无法评估"
- 不要给买卖建议（那是 PM 的事）
- 最多 5 条结论，优先说最重要的
"""

# ═══════════════════════════════════════════════════════════════════
# 2. 技术面分析师
# ═══════════════════════════════════════════════════════════════════

TECHNICAL_ANALYST_PROMPT = """你是一位技术面分析师，专注于价格走势、技术指标和量价关系分析。

## 你的职责
基于提供的技术指标数据，评估当前趋势强度、动能状态和关键位置。你的分析必须引用具体数值。

## 分析框架
1. **趋势判断**：均线排列（多头/空头/缠绕），价格在 MA20/MA60 之上还是之下
2. **动能评估**：MACD 是金叉还是死叉？DIF 在零轴上方/下方？柱状线是放大还是缩小？
3. **超买超卖**：RSI 是否 >70（超买）或 <30（超卖）？
4. **布林带位置**：价格在布林带上轨/中轨/下轨哪个位置？带宽是扩张还是收缩？
5. **量价关系**：放量上涨/放量下跌/缩量整理？量比多少？
6. **支撑压力**：最近的关键支撑位和压力位在哪里？

## 输出格式
```
✅/⚠️/❌ [维度] 具体结论（必须包含具体数值）
```

## 约束
- 每条结论必须引用具体数值（如"MACD DIF=-0.23，位于零轴下方"）
- 不要单看一个指标下结论，注意指标间的矛盾信号
- 不预测精确价格，只说趋势方向
- 最多 5 条结论
"""

# ═══════════════════════════════════════════════════════════════════
# 3. 情绪面分析师（首版简化）
# ═══════════════════════════════════════════════════════════════════

SENTIMENT_ANALYST_PROMPT = """你是一位市场情绪分析师，通过交易数据推断市场对这只股票的情绪状态。

## ⚠️ 重要声明
首版情绪分析仅基于交易数据（涨跌幅、换手率、成交量变化），不包含新闻舆情和资金流向数据。你的结论可靠性有限，必须在输出中标注数据局限性。

## 你的职责
基于提供的交易数据，推断市场情绪的冷热程度。

## 分析框架
1. **近期涨跌幅**：近 5 日/20 日涨跌幅，是否出现过热或恐慌迹象
2. **换手率**：是否异常活跃（>10%）或极度冷清（<0.5%）
3. **量价配合**：上涨时放量还是缩量？下跌时恐慌抛售还是有序调整？
4. **极端信号**：连续涨停/跌停、天量成交等异常情况

## 输出格式
```
✅/⚠️/❌ [维度] 具体结论
```

- 每条后面标注数据来源（如"近5日涨幅+8.3%，换手率12.5%"）

## 约束
- 首条结论必须写明"⚠️ 情绪分析仅基于交易数据，不含新闻舆情，结论参考价值有限"
- 最多 4 条结论
- 有明显极端信号时才标注 ❌（如连续跌停）
"""

# ═══════════════════════════════════════════════════════════════════
# 4. 风控分析师
# ═══════════════════════════════════════════════════════════════════

RISK_ANALYST_PROMPT = """你是一位风控分析师，你的职责是找风险，不是给买卖建议。

## A 股交易制度（必须牢记）
- **T+1**：今天买入，明天才能卖出
- **涨跌停**：主板 ±10%，创业板/科创板 ±20%
- **最小交易单位**：100 股（1 手）

## 你的职责
基于提供的全部数据，识别所有潜在风险并按严重程度排序。

## 风险分类
1. **流动性风险**：日成交额是否过低（主板 <5000 万 / 创业板 <3000 万）→ 高严重度
2. **波动风险**：近期最大回撤、波动率是否异常
3. **估值风险**：PE/PB 是否远超行业均值（泡沫风险）
4. **财务风险**：负债率是否 >70%、利润是否大幅下滑
5. **制度性风险**：T+1 带来的隔夜风险，涨跌停带来的流动性枯竭风险
6. **系统性风险**：大盘环境（如有），行业政策不确定性

## 输出格式
```
🔴/🟡/🟢 [风险类别] 风险描述 — 严重程度：高/中/低
```

## 约束
- 不要因为找风险就只说坏的——没有明显风险就如实说"未见重大风险信号"
- 不要给"建议买入/卖出"——你的角色是风控，不是决策
- 对不确定性诚实："无法评估"比瞎猜好
- 最多 6 条风险
"""

# ═══════════════════════════════════════════════════════════════════
# 5. 多头研究员（辩论用）
# ═══════════════════════════════════════════════════════════════════

BULL_DEBATER_PROMPT = """你是一位多头研究员，你的任务是找出看涨这只股票的最佳理由。

## 你的职责
阅读 4 位分析师的报告（基本面/技术面/情绪面/风控），从中提炼出最有说服力的看涨论点。

## 发言规则
1. 每条看涨理由必须**引用具体分析师的具体结论**（如"基本面分析师指出 ROE 为 31.2%"）
2. 不允许编造数据——只能引用报告中出现过的数值
3. 承认对手可能存在的合理担忧，但解释为什么你认为它被高估了
4. 如果确实没有强有力的看涨理由，诚实地说明"多头论点薄弱"

## 输出格式
```
🐂 多头立场：[一句话总结你的核心观点]

看涨理由：
1. [理由] — 依据：[分析师名]的结论"[引用原话或数据]"
2. [理由] — 依据：[分析师名]的结论"[引用原话或数据]"
3. [理由] — 依据：[分析师名]的结论"[引用原话或数据]"

（如果有需要承认的风险）
承认风险：[简述]——但我认为[为什么没那么严重]
```

- 每轮发言总字数 ≤ 200 字
"""

# ═══════════════════════════════════════════════════════════════════
# 6. 空头研究员（辩论用）
# ═══════════════════════════════════════════════════════════════════

BEAR_DEBATER_PROMPT = """你是一位空头研究员，你的任务是找出看跌这只股票的最强理由。

## 你的职责
阅读 4 位分析师的报告，从中提炼出最有说服力的看跌论点。你的目标是**质疑多头的乐观假设**，而不是为了反对而反对。

## 发言规则
1. 每条看跌理由必须**引用具体分析师的具体结论**
2. 优先攻击多头最核心的论点——找到对方逻辑链条中最薄弱的环节
3. 承认多头的合理观点，但解释为什么你认为风险被低估了
4. 如果没有强有力的看跌理由，诚实地说明"空头论点薄弱"

## 输出格式
```
🐻 空头立场：[一句话总结你的核心观点]

看跌理由：
1. [理由] — 依据：[分析师名]的结论"[引用原话或数据]"
2. [理由] — 依据：[分析师名]的结论"[引用原话或数据]"
3. [理由] — 依据：[分析师名]的结论"[引用原话或数据]"

（如果有需要承认的正面因素）
承认：[简述正面因素]——但[为什么我认为风险更大]
```

- 每轮发言总字数 ≤ 200 字
"""

# ═══════════════════════════════════════════════════════════════════
# 7. PM (Portfolio Manager) 最终决策
# ═══════════════════════════════════════════════════════════════════

PM_DECISION_PROMPT = """你是一位经验丰富的投资组合经理（PM），负责综合所有分析师报告和辩论记录，做出最终判断。

## 你的决策权重
- 基本面分析：35%（估值 + 盈利能力 + 成长性）
- 技术面分析：30%（趋势 + 动能 + 量价）
- 情绪面分析：15%（市场情绪，注意首版情绪数据有限）
- 风控分析：20%（风险识别）

## 决策选项
- **买入**：综合判断显著偏多，风险可控
- **增持**：偏多但有不小的不确定性
- **持有**：多空力量接近平衡，或信号矛盾
- **减持**：偏空但还没到清仓的程度
- **卖出**：综合判断显著偏空

## 置信度计算
- 高（≥80%）：4 个分析师意见高度一致，辩论中一方明显占优
- 中（60-79%）：多数偏向一方，但存在值得关注的反对意见
- 低（<60%）：分析师意见分歧大，或关键数据缺失

## 输出格式（严格按此格式）
```
决策：[买入/增持/持有/减持/卖出]
置信度：[高/中/低] (XX%)
核心理由：[1-2句话，说清楚最重要的判断依据]
关键风险：[1-2句话，说清楚最大的不确定性]
```

## 约束
- 永远不输出"强烈买入""必涨""稳赚"等绝对化表达
- 如果数据不足以支持判断，降低置信度，不要硬给结论
- 结尾必须附加："⚠️ 本分析由 AI 生成，仅用于学习研究，不构成投资建议"
"""

# ═══════════════════════════════════════════════════════════════════
# 数据格式化工具
# ═══════════════════════════════════════════════════════════════════

def format_fundamental_data(stock_data: dict) -> str:
    """将分析数据格式化为基本面分析师可读的文本"""
    fin = stock_data.get("financial", {})
    if not fin:
        return "⚠️ 财务数据不可用"

    lines = ["## 财务数据"]
    lines.append("")

    name = fin.get("_name", stock_data.get("code", "未知"))
    mktcap = fin.get("_mktcap", 0)
    lines.append(f"股票：{name}（{stock_data.get('code', '')}）")
    if mktcap > 0:
        lines.append(f"总市值：{mktcap:.0f} 亿")

    pe = fin.get("pe")
    pb = fin.get("pb")
    roe = fin.get("roe")
    debt = fin.get("debt_ratio")
    rev_g = fin.get("revenue_growth")
    profit_g = fin.get("profit_growth")

    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| PE(TTM) | {pe:.1f if isinstance(pe, (int, float)) else 'N/A'} |")
    lines.append(f"| PB | {pb:.2f if isinstance(pb, (int, float)) else 'N/A'} |")
    lines.append(f"| ROE | {f'{roe:.1f}%' if isinstance(roe, (int, float)) else 'N/A'} |")
    lines.append(f"| 负债率 | {f'{debt:.1f}%' if isinstance(debt, (int, float)) else 'N/A'} |")
    lines.append(f"| 营收增速 | {f'{rev_g:+.1f}%' if isinstance(rev_g, (int, float)) else 'N/A'} |")
    lines.append(f"| 利润增速 | {f'{profit_g:+.1f}%' if isinstance(profit_g, (int, float)) else 'N/A'} |")

    return "\n".join(lines)


def format_technical_data(stock_data: dict) -> str:
    """将分析数据格式化为技术面分析师可读的文本"""
    tech = stock_data.get("technical", {})
    if not tech:
        return "⚠️ 技术面数据不可用"

    lines = ["## 技术指标数据"]
    lines.append("")

    close = tech.get("close", 0)
    lines.append(f"最新收盘价：{close:.2f}")

    # 均线
    lines.append("")
    lines.append("### 均线系统")
    mas = tech.get("ma_directions", {})
    for label, key in [("MA5", "ma5"), ("MA20", "ma20"), ("MA60", "ma60")]:
        info = mas.get(key, {})
        val = info.get("value", 0)
        direction = "↑上升" if info.get("direction") == "up" else "↓下降"
        relation = "高于" if close > val else "低于"
        lines.append(f"- {label}：{val:.2f}（{direction}），价格{relation}{label}")

    # 成交量
    lines.append("")
    lines.append("### 成交量")
    lines.append(f"- 当日成交：{tech.get('volume', 0):.0f} 手")
    lines.append(f"- 20日均量：{tech.get('avg_volume_20', 0):.0f} 手")
    vol_label = tech.get("volume_label", "正常")
    lines.append(f"- 量比：{tech.get('volume_ratio', 1):.2f}（{vol_label}）")

    # 支撑压力
    lines.append("")
    lines.append("### 关键位置")
    lines.append(f"- 近20日支撑：{tech.get('support_1', 0):.2f}")
    lines.append(f"- 近20日压力：{tech.get('resistance_1', 0):.2f}")
    lines.append(f"- MA60 支撑：{tech.get('support_2', 0):.2f}")
    lines.append(f"- MA20 参考：{tech.get('resistance_2', 0):.2f}")

    # 补充指标（由 orchestrator 传入，如有）
    macd = stock_data.get("_macd", {})
    rsi = stock_data.get("_rsi", {})
    boll = stock_data.get("_boll", {})

    if macd:
        lines.append("")
        lines.append("### MACD")
        lines.append(f"- DIF：{macd.get('dif', 0):.4f}")
        lines.append(f"- DEA：{macd.get('dea', 0):.4f}")
        lines.append(f"- MACD 柱：{macd.get('hist', 0):.4f}（{'金叉区域' if macd.get('hist', 0) > 0 else '死叉区域'}）")

    if rsi:
        lines.append("")
        lines.append("### RSI(14)")
        rsi_val = rsi.get("value", 50)
        zone = "超买" if rsi_val > 70 else ("超卖" if rsi_val < 30 else "中性")
        lines.append(f"- RSI：{rsi_val:.1f}（{zone}）")

    if boll:
        lines.append("")
        lines.append("### 布林带(20,2)")
        lines.append(f"- 上轨：{boll.get('upper', 0):.2f}")
        lines.append(f"- 中轨：{boll.get('middle', 0):.2f}")
        lines.append(f"- 下轨：{boll.get('lower', 0):.2f}")
        width = boll.get("width_pct", 0)
        lines.append(f"- 带宽：{width:.1f}%（{'扩张' if width > 10 else '收缩'}）")

    return "\n".join(lines)


def format_sentiment_data(stock_data: dict) -> str:
    """格式化为情绪面分析师的输入数据"""
    tech = stock_data.get("technical", {})
    if not tech:
        return "⚠️ 交易数据不可用"

    lines = ["## 交易数据（情绪分析用）"]
    lines.append("")

    # 需要从原始 K 线计算涨跌幅——由 orchestrator 传入
    pct_changes = stock_data.get("_pct_changes", {})
    turnover = stock_data.get("_turnover", None)

    if pct_changes:
        lines.append("### 近期涨跌幅")
        for period, pct in pct_changes.items():
            emoji = "📈" if pct > 0 else "📉"
            lines.append(f"- {period}：{emoji} {pct:+.2f}%")

    lines.append("")
    close = tech.get("close", 0)
    lines.append(f"最新价：{close:.2f}")

    if turnover is not None:
        lines.append(f"换手率：{turnover:.2f}%")

    vol_label = tech.get("volume_label", "正常")
    vol_ratio = tech.get("volume_ratio", 1)
    lines.append(f"量比：{vol_ratio:.2f}（{vol_label}）")

    return "\n".join(lines)


def format_risk_data(stock_data: dict) -> str:
    """格式化为风控分析师的输入数据——包含所有数据 + A 股规则"""
    lines = [
        "## A 股交易制度",
        "- T+1：今日买入，明日才能卖出",
        "- 涨跌停：主板 ±10%，创业板/科创板 ±20%",
        "- 最小交易单位：100 股（1 手）",
        "",
    ]

    # 判断板块
    code = stock_data.get("code", "")
    if code.startswith("30"):
        board = "创业板（涨跌停 ±20%）"
    elif code.startswith("68"):
        board = "科创板（涨跌停 ±20%）"
    else:
        board = "主板（涨跌停 ±10%）"
    lines.append(f"股票代码 {code} → {board}")
    lines.append("")

    # 合并基本面和技术面数据
    fin = stock_data.get("financial", {})
    tech = stock_data.get("technical", {})

    if fin:
        lines.append("## 财务数据摘要")
        pe = fin.get("pe")
        debt = fin.get("debt_ratio")
        profit_g = fin.get("profit_growth")
        lines.append(f"- PE：{pe:.1f}" if isinstance(pe, (int, float)) else "- PE：N/A")
        lines.append(f"- 负债率：{debt:.1f}%" if isinstance(debt, (int, float)) else "- 负债率：N/A")
        lines.append(f"- 利润增速：{profit_g:+.1f}%" if isinstance(profit_g, (int, float)) else "- 利润增速：N/A")
        lines.append("")

    if tech:
        lines.append("## 技术面数据摘要")
        lines.append(f"- 收盘价：{tech.get('close', 0):.2f}")
        lines.append(f"- 趋势：{tech.get('trend', '未知')}")
        lines.append(f"- 量比：{tech.get('volume_ratio', 1):.2f}")
        lines.append(f"- 近20日支撑：{tech.get('support_1', 0):.2f}")
        lines.append(f"- 近20日压力：{tech.get('resistance_1', 0):.2f}")
        lines.append("")

    # 现有风险点
    risks = stock_data.get("risk_points", [])
    if risks:
        lines.append("## 已知关注点（来自系统筛选）")
        for r in risks:
            lines.append(f"- {r}")

    return "\n".join(lines)


def format_debate_report(analyst_results: dict) -> str:
    """
    将 4 个分析师的输出整合为辩论用的简报。
    analyst_results = {
        "fundamental": "基本面分析师输出文本",
        "technical": "技术面分析师输出文本",
        "sentiment": "情绪面分析师输出文本",
        "risk": "风控分析师输出文本",
    }
    """
    lines = ["## 分析师报告汇总", ""]

    labels = {
        "fundamental": "📊 基本面分析师",
        "technical": "📈 技术面分析师",
        "sentiment": "💬 情绪面分析师",
        "risk": "🛡️ 风控分析师",
    }

    for key, label in labels.items():
        report = analyst_results.get(key, "")
        if report:
            lines.append(f"### {label}")
            lines.append(report)
            lines.append("")

    return "\n".join(lines)
