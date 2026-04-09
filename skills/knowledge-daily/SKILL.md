---
name: knowledge-daily
description: 知识库每日巡检技能 - 汇总今天到期复习与备忘提醒，给出简明的中文处理建议。
license: MIT
compatibility: codex
metadata:
  category: productivity
  requires: knowledge-review, knowledge-memo
---

# 知识库每日巡检技能（Knowledge Daily）

## 用途

这个技能用于每天固定时间检查知识库里两类待处理事项：

- 今日到期复习
- 今日待提醒备忘

它不负责写入知识库，而是负责汇总、提醒、排序和给出下一步建议。

## 优先通过 Codex 自动化调用

这个技能最适合被 Codex 自动化按日触发，而不是由操作系统静默跑完。

原因：

- 需要 AI 解读结果
- 需要 AI 决定优先级
- 需要 AI 用中文输出今天的处理建议

自动化回合里先执行插件内脚本：

从当前仓库根目录运行：

```powershell
python .\plugins\ai-knowledge-base\scripts\daily_check.py
```

如果需要 JSON 输出：

```powershell
python .\plugins\ai-knowledge-base\scripts\daily_check.py --json
```

## 工作要求

1. 在 Codex 自动化回合里先执行 `daily_check.py` 获取今日巡检结果。
2. 如果复习和提醒都为空，直接用中文简明说明“今天没有待处理知识库事项”。
3. 如果存在事项，按下面顺序输出：
   - 复习
   - 备忘
   - 建议动作
4. 建议动作要尽量具体，明确下一步应进入 `knowledge-review` 还是 `knowledge-memo`。
5. 不要编造不存在的条目，不要省略 ID。

## 输出格式

推荐输出结构：

```text
今日知识库巡检

复习
- [K-...] 标题

备忘
- [M-...] 摘要

建议动作
- 先处理...
```

## 触发方式

用户说以下内容时触发：

- “看看今天知识库有什么要处理的”
- “今天有哪些复习和提醒”
- “跑一下知识库每日巡检”
- “检查今天的知识库任务”
