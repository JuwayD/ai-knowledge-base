---
name: knowledge-memo
description: 智能备忘录技能 - 自动分类 idea/todo/闪念，定时提醒，追踪完成状态
license: MIT
compatibility: codex
metadata:
  category: productivity
  requires: none
---

# 备忘录技能（Knowledge Memo）

## 功能说明

用户随时记录 idea、待办事项、闪念碎片，AI 自动分类并建立追踪计划。配合外部定时 Agent 实现每日提醒。

## CLI 工具

所有文件 IO 操作通过 `kb.py` 完成，AI 只负责分类判断和对话。

```powershell
# 工具位置
.\plugins\ai-knowledge-base\scripts\kb.py

# 创建备忘
python .\plugins\ai-knowledge-base\scripts\kb.py add-memo "内容" `r
  --type idea|todo|flash `r
  --priority high|mid|low `r
  --deadline YYYY-MM-DD

# 查看所有状态
python .\plugins\ai-knowledge-base\scripts\kb.py status

# 查看今日提醒
python .\plugins\ai-knowledge-base\scripts\kb.py today-reminds

# 标记完成
python .\plugins\ai-knowledge-base\scripts\kb.py memo-done M-YYYYMMDD-NNN

# 归档
python .\plugins\ai-knowledge-base\scripts\kb.py memo-archive M-YYYYMMDD-NNN

# 更新提醒日期
python .\plugins\ai-knowledge-base\scripts\kb.py update-remind M-YYYYMMDD-NNN --date YYYY-MM-DD

# 获取详情
python .\plugins\ai-knowledge-base\scripts\kb.py get M-YYYYMMDD-NNN
```

## 三种备忘类型

### Idea（创意想法）
- 包含"做个""能不能""如果""也许""想法"等词
- 提醒计划：3天后→7天后→14天后→30天归档
- 追问优先级（高/中/低）

### Todo（待办事项）
- 包含时间要求、动作动词、"要""需要""记得"
- 提醒计划：截止前3天→前1天→当天→超期每天
- 需确认截止日期

### 闪念（Flash Thought）
- 个人感悟、联想、比喻、直觉
- 不追问，直接记录
- 纳入遗忘曲线复习（由 knowledge-review 管理）

## 工作流程

```
用户输入备忘内容
       │
       ▼
┌──────────────────────────┐
│ 1. AI 判断类型            │
│    idea / todo / 闪念     │
│    （模糊时询问用户）     │
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 2. AI 补充信息            │
│    idea → 优先级          │
│    todo → 截止日期        │
│    闪念 → 不追问          │
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 3. 调用 kb.py add-memo   │
│    自动创建文件+索引+计划 │
└──────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 4. 展示确认摘要           │
└──────────────────────────┘
```

## 详细步骤

### 步骤 1: 分类判断

AI 根据用户输入判断类型：

| 特征 | 类型 |
|------|------|
| "做个""能不能""如果""也许""想法" | idea |
| 时间要求、动作动词、"要""需要""记得" | todo |
| 个人感悟、联想、比喻、直觉 | 闪念(flash) |
| 模糊不清 | 询问用户选择 |

示例：
```
用户: "能不能做一个 CLI 工具自动从 git log 生成 changelog"
AI:  这是个不错的 idea！你觉得优先级如何？
     🔴 高 - 近期想做
     🟡 中 - 有空再做
     🟢 低 - 灵感记录，不一定做
```

### 步骤 2: 补充信息

- **Idea →** 询问优先级（高/中/低）
- **Todo →** 确认截止日期
- **闪念 →** 不追问，直接记录

### 步骤 3: 调用 kb.py 录入

```powershell
python .\plugins\ai-knowledge-base\scripts\kb.py add-memo "备忘内容" --type idea --priority mid
```

`kb.py` 会自动处理：
- ID 生成（M-YYYYMMDD-NNN）
- 备忘文档创建
- index.md 更新
- 提醒日期计算

### 步骤 4: 展示确认

```
📌 备忘已录入！
━━━━━━━━━━━━━━━━━━━━━
类型: 💡 Idea
标题: CLI 工具自动生成 changelog
优先级: 🟡 中
下次提醒: 2026-04-08 (3天后)
━━━━━━━━━━━━━━━━━━━━━
```

## 额外命令

### memo status — 查看所有备忘状态

```powershell
python .\plugins\ai-knowledge-base\scripts\kb.py status
```

AI 读取返回的 JSON，格式化展示：

```
📋 备忘录状态总览
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Idea (2条)
  🟢 M-001 CLI自动生成changelog [pending] 下次: 4月8日
  🔴 M-003 知识系统独立CLI [pending] 下次: 4月12日

✅ Todo (1条)
  ⚠️ M-004 周五交报告 [pending] 截止: 4月7日 (还剩2天!)

💭 闪念 (1条)
  M-005 架构像细胞 [pending]

📊 活跃: 4 | 已完成: 1 | 已归档: 0
```

### memo remind — 今日提醒

```powershell
python .\plugins\ai-knowledge-base\scripts\kb.py today-reminds
```

供外部定时 Agent 调用。AI 格式化输出：

```
🔔 今日提醒 - 2026-04-05
━━━━━━━━━━━━━━━━━━━━━━

💡 [M-001] CLI自动生成changelog
  → 已记录3天，要展开这个 idea 吗？

⚠️ [M-004] 周五交报告
  → 截止还剩2天，进度如何？
```

### memo done <ID> — 标记完成

```powershell
python .\plugins\ai-knowledge-base\scripts\kb.py memo-done M-YYYYMMDD-NNN
```

### memo archive <ID> — 归档

```powershell
python .\plugins\ai-knowledge-base\scripts\kb.py memo-archive M-YYYYMMDD-NNN
```

### memo expand <ID> — 展开一个 idea

将 idea 细化为可执行计划（AI 引导对话）：

```
🚀 展开 Idea: CLI自动生成changelog
━━━━━━━━━━━━━━━━━━━━━━
1. 目标用户是谁？
2. 核心功能是什么？
3. 技术选型？
4. MVP 需要多长时间？

请逐个回答，或直接描述你的想法：
```

展开后可以：
- 拆分为多个 todo（调用 `add-memo --type todo`）
- 如果涉及新技术，引导用 `knowledge-digest` 学习

### 用户在提醒时的回复处理

| 用户回复 | 操作 |
|---------|------|
| "展开了/开始做" | 进入 expand 流程 |
| "先放放" | `update-remind --date [7天后]` |
| "放弃了" | `memo-archive` |
| "完成了" | `memo-done` |

## 与其他技能的联动

### → knowledge-digest
idea 展开涉及新知识时：
```
这个 idea 涉及 [技术X]，要现在录入相关知识吗？
```

### → knowledge-review
闪念自动进入复习队列。

### 外部定时 Agent
每天执行 `kb.py today-reminds`，获取今日待提醒内容推送。

## 边界情况

### 输入模糊
无法判断类型时，让用户选择：
```
请选择类型：
1. 💡 Idea
2. ✅ Todo
3. 💭 闪念
```

### 超期 Todo
`today-reminds` 会返回所有到期提醒（包括超期的），AI 在展示时高亮超期条目。


