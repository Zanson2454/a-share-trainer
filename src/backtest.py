"""
回测引擎 — 基于历史K线数据验证策略表现
"""
import pandas as pd
import numpy as np
from typing import Callable, Optional
from dataclasses import dataclass, field


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    start_date: str
    end_date: str
    trade_count: int = 0
    win_count: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    annual_return: float = 0.0
    profit_loss_ratio: float = 0.0
    sharpe_ratio: float = 0.0
    max_consecutive_loss: int = 0
    total_return: float = 0.0
    benchmark_return: float = 0.0
    failure_periods: list[dict] = field(default_factory=list)
    overfit_risk: str = "低"
    data_issues: list[str] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    trades: list[dict] = field(default_factory=list)
    initial_capital: float = 100000
    commission: float = 0.0003

    def to_report(self) -> str:
        """生成回测报告 Markdown（含交易明细）"""
        lines = [
            "# 回测报告 — " + self.strategy_name,
            "",
            "## 基本信息",
            "- 回测区间: " + str(self.start_date) + " ~ " + str(self.end_date),
            "- 初始资金: " + str(self.initial_capital) + " 元",
            "- 手续费率: 3‱（万分之三）",
            "- 交易费用假设: 买卖各收万分之三，无印花税、过户费模拟",
            "",
            "## 核心指标",
            "| 指标 | 数值 | 评价 |",
            "|------|------|------|",
            "| 交易次数 | " + str(self.trade_count) + " | |",
            "| 胜率 | {:.1%} | |".format(self.win_rate),
            "| 最大回撤 | {:.1%} | |".format(self.max_drawdown),
            "| 年化收益率 | {:.1%} | |".format(self.annual_return),
            "| 盈亏比 | {:.2f} | |".format(self.profit_loss_ratio),
            "| 夏普比率 | {:.2f} | |".format(self.sharpe_ratio),
            "| 最大连续亏损 | " + str(self.max_consecutive_loss) + "次 | |",
            "| 累计收益率 | {:.1%} | |".format(self.total_return),
            "| 基准收益(沪深300) | {:.1%} | |".format(self.benchmark_return),
            "",
        ]

        # 交易明细（前10条）
        if self.trades:
            lines += [
                "## 交易明细（前10条）",
                "",
                "| 序号 | 日期 | 方向 | 价格 | 数量(股) | 金额 | 累计盈亏 | 原因 |",
                "|------|------|------|------|----------|------|----------|------|",
            ]
            buy_price = 0
            cumulative_pnl = 0.0
            trade_num = 0
            display_count = min(10, len(self.trades))
            for t in self.trades[:display_count]:
                trade_num += 1
                direction = "买入" if t.get("action") == "buy" else "卖出"
                price = t.get("price", 0)
                qty = t.get("quantity", 0)
                amount = price * qty
                if t.get("action") == "sell" and buy_price > 0:
                    pnl = (price - buy_price) * qty
                    cumulative_pnl += pnl
                    buy_price = 0
                else:
                    pnl = 0
                if t.get("action") == "buy":
                    buy_price = price
                pnl_str = "{:+.0f}".format(cumulative_pnl) if t.get("action") == "sell" else "-"
                lines.append(
                    "| {} | {} | {} | {:.2f} | {} | {:.0f} | {} | {} |".format(
                        trade_num, str(t.get("date", ""))[:10],
                        direction, price, qty, amount, pnl_str,
                        t.get("reason", "")
                    )
                )
            lines.append("")
            if len(self.trades) > 10:
                lines.append("> ⚠️ 仅展示前10条，完整数据共 {} 条交易记录".format(len(self.trades)))
                lines.append("")

        # 关键假设
        lines += [
            "## 关键假设与限制",
            "",
            "| 项目 | 状态 | 说明 |",
            "|------|------|------|",
            "| 未来函数检查 | ❌ 未实现 | 未做逐日数据隔离验证，策略函数可能访问了当日之后的数据 |",
            "| 停牌处理 | ❌ 未实现 | 假设所有交易日均可正常交易，未过滤停牌日 |",
            "| 涨跌停处理 | ❌ 未实现 | 假设所有信号均可成交，未模拟涨停买不进/跌停卖不出 |",
            "| 复权处理 | ⚠️ 依赖数据源 | 若输入数据为前复权则已处理，否则含分红拆股失真 |",
            "| 滑点模拟 | ❌ 未实现 | 以收盘价成交，未考虑买卖价差和冲击成本 |",
            "| 最大回撤计算 | ✅ 已实现 | 逐日权益峰值回撤法: (peak - equity) / peak |",
            "| 手续费 | ✅ 已实现 | 买卖各万分之三，逐笔扣除 |",
            "",
        ]

        # 策略失效阶段
        if self.failure_periods:
            lines += ["## 策略失效阶段", "| 时间段 | 表现 | 原因分析 |", "|--------|------|----------|"]
            for fp in self.failure_periods:
                lines.append("| {} | {} | {} |".format(
                    fp.get("period", ""), fp.get("performance", ""), fp.get("reason", "")
                ))
            lines.append("")

        # 过拟合风险
        lines += [
            "## 过拟合风险评估",
            "> " + self.overfit_risk,
            "",
        ]

        # 数据问题
        if self.data_issues:
            lines += ["## 数据问题"]
            for di in self.data_issues:
                lines.append("- " + str(di))
            lines.append("")

        lines += ["> ⚠️ 仅用于学习研究，不构成投资建议。回测结果不代表未来表现。"]
        return "\n".join(lines)


class BacktestEngine:
    """策略回测引擎"""

    @staticmethod
    def run(
        kline_df: pd.DataFrame,
        strategy_fn: Callable,
        strategy_name: str,
        benchmark_df: Optional[pd.DataFrame] = None,
        initial_capital: float = 100000,
        commission: float = 0.0003,  # 万三手续费
    ) -> BacktestResult:
        """
        执行回测
        :param kline_df: K线数据 (需有 date, open, high, low, close, volume)
        :param strategy_fn: 策略函数，签名为 fn(df, position, cash) -> signal
               signal: {action: 'buy'/'sell'/'hold', quantity: int, reason: str}
        :param strategy_name: 策略名称
        :param benchmark_df: 基准K线（如沪深300）
        :param initial_capital: 初始资金
        :param commission: 手续费率
        """
        if kline_df is None or kline_df.empty:
            result = BacktestResult(
                strategy_name=strategy_name,
                start_date="",
                end_date="",
            )
            result.data_issues.append("K线数据为空")
            return result

        result = BacktestResult(
            strategy_name=strategy_name,
            start_date=str(kline_df.iloc[0]["date"]),
            end_date=str(kline_df.iloc[-1]["date"]),
        )

        cash = initial_capital
        shares = 0
        trades = []
        equity_curve = [initial_capital]
        peak = initial_capital
        max_dd = 0.0
        consecutive_loss = 0
        max_consec_loss = 0

        # 确保按日期排序
        df = kline_df.sort_values("date").reset_index(drop=True)

        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            price = current_bar["close"]

            # ── 逐日盯市：无论是否有信号，必须更新权益曲线 ──
            equity = cash + shares * price
            equity_curve.append(equity)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

            # 调用策略函数
            try:
                signal = strategy_fn(df.iloc[:i+1], shares, cash)
            except Exception as e:
                result.data_issues.append(f"策略执行错误 第{i}行: {e}")
                continue

            if signal is None:
                continue

            action = signal.get("action", "hold")
            qty = signal.get("quantity", 0)

            if action == "buy" and qty > 0:
                cost = qty * price * (1 + commission)
                if cost <= cash:
                    cash -= cost
                    shares += qty
                    trades.append({
                        "date": current_bar["date"],
                        "action": "buy",
                        "price": price,
                        "quantity": qty,
                        "reason": signal.get("reason", ""),
                    })
            elif action == "sell" and qty > 0 and shares >= qty:
                cash += qty * price * (1 - commission)
                shares -= qty
                trades.append({
                    "date": current_bar["date"],
                    "action": "sell",
                    "price": price,
                    "quantity": qty,
                    "reason": signal.get("reason", ""),
                })

        # 期末强制清仓（计入交易明细和统计）
        if shares > 0:
            last_price = df.iloc[-1]["close"]
            last_date = df.iloc[-1]["date"]
            cash += shares * last_price * (1 - commission)
            trades.append({
                "date": last_date,
                "action": "sell",
                "price": last_price,
                "quantity": shares,
                "reason": "期末强制清仓",
            })
            shares = 0

        # 计算指标
        result.equity_curve = equity_curve
        result.max_drawdown = max_dd

        # 交易统计
        buy_trades = [t for t in trades if t["action"] == "buy"]
        sell_trades = [t for t in trades if t["action"] == "sell"]
        result.trade_count = len(buy_trades)

        if len(trades) >= 2:
            # 配对买卖计算盈亏
            profits = []
            open_trade = None
            for t in trades:
                if t["action"] == "buy" and open_trade is None:
                    open_trade = t
                elif t["action"] == "sell" and open_trade is not None:
                    profit = (t["price"] - open_trade["price"]) / open_trade["price"]
                    profits.append(profit)
                    if profit > 0:
                        result.win_count += 1
                        consecutive_loss = 0
                    else:
                        consecutive_loss += 1
                        if consecutive_loss > max_consec_loss:
                            max_consec_loss = consecutive_loss
                    open_trade = None

            if profits:
                result.win_rate = result.win_count / len(profits) if profits else 0
                avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 0
                avg_loss = abs(np.mean([p for p in profits if p < 0])) if any(p < 0 for p in profits) else 1
                result.profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        result.max_consecutive_loss = max_consec_loss

        # 存入交易明细和费用参数
        result.trades = trades
        result.initial_capital = initial_capital
        result.commission = commission

        # 收益计算
        result.total_return = (cash - initial_capital) / initial_capital
        days = len(df)
        years = days / 252
        if years > 0 and result.total_return > -1:
            result.annual_return = (1 + result.total_return) ** (1 / years) - 1

        # 夏普比率
        if len(equity_curve) > 1:
            returns = np.diff(equity_curve) / equity_curve[:-1]
            if returns.std() > 0:
                result.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)

        # 基准收益
        if benchmark_df is not None and not benchmark_df.empty:
            bench_start = benchmark_df.iloc[0]["close"]
            bench_end = benchmark_df.iloc[-1]["close"]
            result.benchmark_return = (bench_end - bench_start) / bench_start
        else:
            result.data_issues.append("无基准数据（沪深300），无法对比基准收益")

        # 过拟合风险判断
        if result.trade_count < 10:
            result.overfit_risk = "高 — 交易次数太少（<10次），样本不足"
        elif result.win_rate > 0.8 and result.trade_count < 30:
            result.overfit_risk = "中高 — 高胜率但样本偏少，可能存在过拟合"
        elif result.max_drawdown > 0.5:
            result.overfit_risk = "中 — 最大回撤过大，策略可能在真实环境中表现更差"
        else:
            result.overfit_risk = "低 — 样本充足且指标稳定"

        return result
