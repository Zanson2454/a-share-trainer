"""
/策略 — 策略库管理
"""
from datetime import datetime
from pathlib import Path
from ..config import Config
from ..obsidian_sync import ObsidianSync

STRATEGY_TEMPLATE = """---
name: "{name}"
version: "1.0"
created: "{date}"
status: "开发中"
---

# {name}

## 一、策略定义

| 属性 | 值 |
|------|-----|
| 适用市场环境 | （进攻/震荡/防守） |
| 持仓周期 | （短线/中线/长线） |
| 最大仓位 | % |
| 单只最大仓位 | % |

## 二、选股条件

1. 
2. 
3. 

## 三、买入观察条件

> 满足选股条件后，等待以下信号确认：

1. 
2. 

## 四、退出条件

### 止损
- 

### 止盈
- 

### 时间止损
- 持有超过 ___ 天未达预期，强制退出

## 五、仓位规则

| 信号强度 | 仓位 |
|----------|------|
| 强 | % |
| 中 | % |
| 弱 | % |

## 六、失效条件

> 出现以下情况，本策略暂停使用：

1. 
2. 

## 七、回测结果

（待回测）

## 八、复盘结论

（待复盘）

---

> ⚠️ 仅用于学习研究，不构成投资建议
"""


def _validate_strategy_name(name: str) -> str | None:
    """策略名只能是单个文件名，避免读写 05_策略 目录外的文件。"""
    safe_name = (name or "").strip()
    if not safe_name or safe_name in {".", ".."}:
        return None
    if Path(safe_name).name != safe_name:
        return None
    return safe_name


def execute(args: list = None) -> str:
    """执行 /策略 命令"""
    vault_path = Path(Config.OBSIDIAN_VAULT_PATH) / "05_策略"
    existing = []
    if vault_path.exists():
        existing = [f.stem for f in vault_path.iterdir() if f.suffix == ".md"]

    if not args or len(args) == 0:
        lines = ["## 📚 策略库", ""]
        if existing:
            lines.append("### 已有策略")
            lines.append("")
            for s in existing:
                lines.append("- **" + s + "**")
        else:
            lines.append("暂无策略。")
        lines.append("")
        lines.append("### 创建新策略")
        lines.append("")
        lines.append("使用模板创建：")
        lines.append("1. 复制 `templates/策略模板.md`")
        lines.append("2. 填写策略各项要素")
        lines.append("3. 保存到 `05_策略/` 目录")
        lines.append("")
        lines.append("策略必须包含：")
        lines.append("- 策略名称、适用市场环境、选股条件")
        lines.append("- 买入观察条件、退出条件、仓位规则")
        lines.append("- 失效条件、回测结果、复盘结论")
        lines.append("")
        lines.append("> ⚠️ 仅用于学习研究，不构成投资建议")
        return "\n".join(lines)

    # 查看指定策略
    strategy_name = _validate_strategy_name(args[0])
    if strategy_name is None:
        return "❌ 无效的策略名称。策略名称不能包含路径分隔符或上级目录引用。"

    filepath = vault_path / (strategy_name + ".md")
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    # 创建新策略
    today = datetime.now().strftime("%Y-%m-%d")
    template = STRATEGY_TEMPLATE.format(name=strategy_name, date=today)
    ObsidianSync.save_strategy(strategy_name, template)
    return "✅ 已创建策略「" + strategy_name + "」\n\n请编辑 `05_策略/" + strategy_name + ".md` 填写具体内容。\n\n" + template
