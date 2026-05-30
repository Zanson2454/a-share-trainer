"""
A股训练系统 — 主 CLI 入口
路由 /help /学习 /盘前 /选股 /个股 /复盘 /策略 /回测 命令
"""
import sys
from src.commands import (
    help_command,
    learn_command,
    premarket_command,
    stock_select_command,
    stock_analysis_command,
    review_command,
    strategy_command,
    backtest_command,
    wencai_command,
    agent_command,
)
from src.config import Config
from src.messaging import MessageBus


# 命令路由表
COMMANDS = {
    "/help": help_command,
    "/帮助": help_command,
    "/学习": learn_command,
    "/盘前": premarket_command,
    "/选股": stock_select_command,
    "/个股": stock_analysis_command,
    "/复盘": review_command,
    "/策略": strategy_command,
    "/回测": backtest_command,
    "/问财": wencai_command,
    "/选股助手": wencai_command,
    "/agent": agent_command,
}


def route(user_input: str) -> str:
    """
    路由用户输入到对应命令
    :param user_input: 用户原始输入，如 '/个股 600519'
    :return: 命令输出文本
    """
    input_str = user_input.strip()

    if not input_str:
        return help_command.execute()

    # 解析命令和参数
    parts = input_str.split(maxsplit=1)
    cmd = parts[0]
    args_str = parts[1] if len(parts) > 1 else ""

    # 查找命令
    if cmd in COMMANDS:
        # 解析参数
        args = args_str.split() if args_str else []
        result = COMMANDS[cmd].execute(args)
    else:
        result = f"❌ 未知命令: {cmd}\n\n输入 `/帮助` 查看所有命令"

    return result


def main():
    """主入口 — 从命令行参数读取并路由"""
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        result = route(user_input)
        print(result)
        return 0
    else:
        # 交互模式
        print("📊 A股训练系统 v1.0")
        print("输入 /帮助 查看命令，输入 exit 退出")
        print("=" * 50)

        while True:
            try:
                user_input = input("\n> ").strip()
                if user_input.lower() in ("exit", "quit", "q"):
                    print("再见！")
                    break
                if user_input:
                    result = route(user_input)
                    print("\n" + result)
            except (KeyboardInterrupt, EOFError):
                print("\n再见！")
                break
    return 0


if __name__ == "__main__":
    # 验证配置
    missing = Config.validate()
    if missing:
        print(f"⚠️ 配置缺失: {missing}")

    # 显示消息渠道状态
    print(MessageBus.status())

    sys.exit(main())
