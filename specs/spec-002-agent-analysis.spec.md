---
id: spec-002
title: AI Agent 多分析师股票深度研判
module: a-share-trainer
status: drafting
priority: p1
version: "1.0.0"
created: 2026-05-30
depends_on:
  - spec-001
scope:
  in:
    - 4 个 AI 分析师角色（基本面/技术面/情绪面/风控）
    - 多空辩论机制（2-3轮互相挑战）
    - PM 最终决策（买入/卖出/持有 + 置信度）
    - DeepSeek API 集成（V4 Flash 默认，Pro 可选）
    - 复用现有 Sina/Tushare/AKShare 数据管道
    - CLI 命令 `/agent <code> [--deep]`
    - API 端点 `GET /api/stocks/{code}/agent`
    - Token 用量统计与成本估算
    - 辩论过程完整透明输出
  out:
    - 自动交易/下单
    - 实时行情推送触发
    - 批量全市场扫描（单次仅分析一只）
    - 替代现有 `/个股` 命令（互补关系）
    - WebSocket 流式输出（首版不搞）
acceptance_criteria:
  - id: AC-01
    scenario: 单股 Agent 分析
    given: DeepSeek API 已配置，数据管道可用
    when: 用户输入 `/agent 600519`
    then: 输出 4 个分析师结论 + 辩论过程 + PM 决策 + 置信度，标注 token 用量
  - id: AC-02
    scenario: 深度模式
    given: 同上
    when: 用户输入 `/agent 600519 --deep`
    then: 使用 DeepSeek V4 Pro，辩论轮次增加到 5 轮，输出更详细
  - id: AC-03
    scenario: API 调用
    given: FastAPI 服务运行中
    when: GET /api/stocks/600519/agent
    then: 返回 JSON 格式的分析结果，含 reasoning_chain 数组
  - id: AC-04
    scenario: 数据不足降级
    given: Tushare 财务数据获取失败
    when: 用户输入 `/agent 000001`
    then: 基本面分析师标注"数据不足"，其他分析师正常运作，PM 降低置信度
  - id: AC-05
    scenario: API 异常处理
    given: DeepSeek API 不可用或超时
    when: 用户输入 `/agent 600519`
    then: 返回明确错误信息 + 建议检查 API Key，不崩溃
  - id: AC-06
    scenario: 无效代码
    given: 无
    when: 用户输入 `/agent abc` 或 `/agent`
    then: 返回格式错误提示，示例用法
---

# AI Agent 多分析师股票深度研判

## 概述

在现有 `/个股`（纯指标计算，不给买卖结论）基础上，新增 `/agent` 命令。用多 Agent LLM 协作模拟投行研究流程：4 个分析师分头调研 → 多空辩论 → PM 综合决策。输出完整推理链，让用户看到"AI 为什么这么判断"。

**核心理念**：不是黑盒给结论，而是让推理过程完全透明——用户可以审阅每个 Agent 的逻辑，自己判断是否认同。

## 与 `/个股` 的关系

```
/个股 600519  →  技术面+财务面指标（纯代码计算，不给结论）
                用途：快速筛查，0成本

/agent 600519 →  4个AI分析师+辩论+PM决策（LLM推理，给买卖建议）
                用途：深度研究，有token成本
```

两者互补，不替代。用户先 `/个股` 快速看指标，感兴趣的再用 `/agent` 深度分析。

## Agent 角色定义

### 1. 基本面分析师 (Fundamental Analyst)

**职责**：评估公司估值与财务健康度

**输入数据**（来自现有管道）：
- PE(TTM)、PB、总市值（Sina）
- ROE、负债率、营收增速、利润增速（Tushare，年报数据）
- 行业对比参考（同行业 PE 中位数，如有）

**分析维度**：
- 估值水平：PE/PB 相对历史分位和行业均值
- 盈利能力：ROE 是否 >15%，趋势向上还是向下
- 成长性：营收和利润增速，是否持续
- 财务风险：负债率是否安全，现金流情况
- 市值规模：大盘/中盘/小盘，流动性考量

**输出格式**：3-5 条结构化结论，每条标注"正面/负面/中性"

### 2. 技术面分析师 (Technical Analyst)

**职责**：评估价格趋势与技术形态

**输入数据**（来自 AKShare K线）：
- 近 60 个交易日 OHLCV
- MA5/MA20/MA60 均线
- MACD（DIF/DEA/柱）
- RSI(14)
- 布林带（上/中/下轨）
- 成交量 + 20日均量比

**分析维度**：
- 趋势判断：均线排列（多头/空头/缠绕）
- 动能评估：MACD 金叉死叉位置，RSI 超买超卖
- 形态识别：支撑/压力位，近期高低点
- 量价关系：放量上涨/下跌，缩量整理
- 短期/中期信号冲突时说明

**输出格式**：3-5 条结构化结论，含具体数值引用

### 3. 情绪面分析师 (Sentiment Analyst) — 首版简化

**职责**：评估市场情绪和资金动向

**输入数据**（首版有限）：
- 涨跌幅（近期）
- 换手率
- 成交量变化趋势
- （未来可扩展：新闻舆情、北向资金、龙虎榜）

**分析维度**：
- 近期涨跌幅：是否过热或恐慌
- 换手率：异常活跃还是无人问津
- 资金信号：量价背离、缩量止跌等
- 首版明确标注"情绪数据有限，结论仅供参考"

**输出格式**：2-4 条结论，标注数据局限性

### 4. 风控分析师 (Risk Analyst)

**职责**：识别风险，不做买卖判断

**输入数据**：
- 所有上述数据
- A 股制度约束（T+1、涨跌停）
- 大盘环境（如有 /盘前 数据）

**分析维度**：
- 流动性风险：日成交额是否过低（<5000万）
- 波动风险：近期最大回撤、波动率
- 事件风险：财报窗口期、ST 风险
- 系统性风险：大盘趋势、行业政策
- 仓位建议：基于波动率给出"激进/中性/保守"配置建议

**输出格式**：风险清单 + 严重程度（高/中/低）

## 多空辩论机制

### 辩论流程

```
Round 1: 各自陈述
  🐂 多头研究员: 综合 4 个分析师报告，提出 3 个看涨理由
  🐻 空头研究员: 综合 4 个分析师报告，提出 3 个看跌理由

Round 2: 互相挑战（默认模式 2 轮，--deep 模式 3-5 轮）
  🐻 挑战多头: 质疑对方最核心的看涨理由
  🐂 回应+反击: 辩护 + 质疑空头最核心的看跌理由

Round 3: 最终陈述（如有分歧）
  双方各做最终 2 句话总结，明确自己的立场
```

### 辩论规则
- 每轮发言限 200 字（防 token 爆炸）
- 必须引用具体数据，不允许"我觉得"
- 承认不确定性的发言加权（"数据不支持 X，但也不排除 Y"）
- PM 最终决策时优先采信有数据支撑的论点

## PM (Portfolio Manager) 决策

### 决策流程

PM 收到所有分析报告 + 辩论记录后，综合判断：

1. **权重分配**：基本面 35% / 技术面 30% / 情绪面 15% / 风控 20%
2. **置信度计算**：4 个分析师意见一致性越高，置信度越高
3. **输出结论**：

```
决策: [买入/增持/持有/减持/卖出]
置信度: [高 80%+ / 中 60-80% / 低 <60%]
核心理由: 1-2 句话
关键风险: 1-2 句话
```

### 决策约束
- 永远不输出"强烈买入""必涨""稳赚"
- 置信度低时必须说明"为什么不确定"
- 标注"本分析由 AI 生成，仅用于学习研究，不构成投资建议"

## 技术实现

### 模块结构

```
src/
├── agents/
│   ├── __init__.py
│   ├── prompts.py          # 4 个分析师 + 多空研究员 + PM 的 system prompt
│   ├── debater.py          # 辩论编排（多轮对话管理）
│   └── orchestrator.py     # 主编排：收集数据 → 并行调Agent → 辩论 → PM → 格式化
├── commands/
│   └── agent_command.py    # /agent CLI 命令
├── services/
│   └── agent_service.py    # API 层（供 router 调用）
└── api/routers/
    └── agent.py            # GET /api/stocks/{code}/agent
```

### LLM 调用策略

```python
# 默认模式（快速，便宜）
MODEL = "deepseek-v4-flash"
MAX_DEBATE_ROUNDS = 2
TEMPERATURE = 0.3  # 偏稳定，减少幻觉

# 深度模式（--deep）
MODEL = "deepseek-v4-pro"  
MAX_DEBATE_ROUNDS = 5
TEMPERATURE = 0.5  # 稍高，允许更多角度
```

### Token 用量优化
- 4 个分析师**并行调用**（不互相等待）
- K 线数据不喂原始 OHLCV，只喂计算好的指标值（减少 prompt 长度）
- 每轮辩论只传对方上一轮的质疑（不传完整历史）
- 输出中标注实际消耗 token 数和估算成本

### 配置新增

```env
# .env 新增
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
AGENT_DEFAULT_MODEL=deepseek-v4-flash
AGENT_DEEP_MODEL=deepseek-v4-pro
```

### 数据层复用

```
orchestrator.py
  │
  ├─ analyze_stock(code)     ← services/analysis_service.py（/个股 已有的）
  ├─ AKShareClient.get_daily_kline(code)
  ├─ AKShareClient.get_financial_data(code)
  └─ （不需要新数据源）
```

Agent 不直接调数据 API，而是接收已处理好的结构化数据字典。

## 输出格式

### CLI 输出示例

```
🤖 AI Agent 深度研判 — 600519 贵州茅台

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 基本面分析师
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PE 28.5，处于近5年30%分位，相对合理
✅ ROE 31.2%，持续高于15%，盈利能力优秀
⚠️ 营收增速 +12%，较去年+18%放缓
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐂🦅 多空辩论
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Round 1]
🐂 多头：估值合理+ROE优秀+技术面金叉...
🐻 空头：增速放缓+消费降级+大盘弱势...

[Round 2]
🐻→🐂：增速放缓是周期性的还是结构性的？
🐂 回应：参考2013-2015年同样经历增速放缓...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PM 决策
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策: 增持
置信度: 中 (72%)
核心理由: 估值合理+盈利能力护城河强，但增速放缓需观察
关键风险: 消费降级超预期、白酒行业政策风险

📊 本次消耗: 48,230 token ≈ ¥0.05
⚠️ 本分析由 AI 生成，仅用于学习研究，不构成投资建议
```

### API JSON 输出

```json
{
  "code": "600519",
  "name": "贵州茅台",
  "model": "deepseek-v4-flash",
  "decision": "增持",
  "confidence": 0.72,
  "confidence_level": "中",
  "core_reason": "估值合理+盈利能力护城河强",
  "key_risk": "消费降级超预期",
  "analyst_reports": {
    "fundamental": {"conclusions": [...], "sentiment": "偏多"},
    "technical": {"conclusions": [...], "sentiment": "偏多"},
    "sentiment": {"conclusions": [...], "sentiment": "中性"},
    "risk": {"risks": [...], "max_severity": "中"}
  },
  "debate": [
    {"round": 1, "bull": "...", "bear": "..."},
    {"round": 2, "challenge": "...", "response": "..."}
  ],
  "token_usage": {"total": 48230, "estimated_cost_rmb": 0.05},
  "disclaimer": "本分析由 AI 生成，仅用于学习研究，不构成投资建议"
}
```

## 前端页面（可选，不阻塞 CLI 交付）

在现有 React 前端新增 `AgentAnalysisPage.tsx`：
- 输入股票代码 → 显示分析进度（4 个分析师并行状态）
- 展示辩论过程（对话气泡式）
- PM 决策卡片（颜色编码：绿色=买入，黄色=持有，红色=卖出）
- 如果 CLI 先交付，前端可以用 `ComingSoonPage` 占位

## 风险与限制

| 风险 | 缓解措施 |
|------|---------|
| LLM 幻觉（编造数据） | 所有数据由代码计算后喂入，Agent 只做推理不做数据获取 |
| Token 成本累积 | 默认用 Flash，标注每次成本；单次上限约 5 万 token |
| 辩论陷入循环 | 最多 5 轮强制终止，PM 直接基于现有信息决策 |
| A 股制度盲区 | 风控分析师 system prompt 明确注入 T+1/涨跌停等规则 |
| 过度依赖 AI 判断 | 输出反复标注"仅用于学习研究"，强调用户需自己判断 |

## 交付计划

| 阶段 | 内容 | 预计文件 |
|------|------|---------|
| Phase 1 | spec 评审 + 确认 | 本文件 |
| Phase 2 | prompts.py（4 个分析师 + 辩论 + PM 的 prompt） | 1 文件 |
| Phase 3 | orchestrator.py（编排主逻辑） | 1 文件 |
| Phase 4 | agent_command.py + agent_service.py + API router | 3 文件 |
| Phase 5 | Config 新增 DeepSeek 配置 | 修改 2 文件 |
| Phase 6 | 集成测试 + 端到端跑通 | tests/ |
