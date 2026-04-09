# AI Knowledge Base — 使用与介绍指南

> 版本: 2.0 | 更新: 2026-04-06

---

## 一、项目简介

AI Knowledge Base 是一个面向 AI Agent（如 opencode）的个人知识管理系统。核心理念：

- **kb.py** 负责所有文件 IO、日期计算、数据查询等程序化操作
- **AI** 负责对话、评分、出题等需要智能的工作
- **Skills** 定义 AI 的行为流程（苏格拉底追问、间隔复习、学习计划等）

### 目录结构

```
~/.ai-knowledge-base/
├── kb.py              # 核心 CLI 工具（Python 3.9+）
├── index.md           # 索引文件（自动维护，勿手动改格式）
├── knowledge/         # 知识文档
│   └── <topic>/       # 按主题自动归组的子目录
│       ├── _topic.md  # 主题索引（自动生成）
│       └── *.md       # 知识文档
├── memos/             # 备忘文档
├── plans/             # 学习计划
├── reviews/           # 复习记录
├── daily/             # 日记（预留）
└── GUIDE.md           # 本文件
```

---

## 二、核心概念

### 2.1 知识条目（Knowledge）

每条知识对应 `knowledge/` 下的一个 Markdown 文件，在 `index.md` 中登记：

| 字段 | 说明 | 示例 |
|------|------|------|
| id | 唯一标识 | K-20260406-001 |
| title | 标题 | Agent Harness |
| tags | 标签（逗号分隔） | ai-agent, llm |
| mastery | 掌握度 1-5 | 4 |
| topic | 所属主题 | ai-agent |
| parent | 父级知识 ID | K-XXXXXXXX-XXX |
| depends_on | 前置依赖 | K-XXXXXXXX-XXX |
| related_to | 关联知识 | K-XXXXXXXX-XXX |
| round | 复习轮次 | 2 |
| next_review | 下次复习日期 | 2026-04-07 |

### 2.2 备忘条目（Memo）

三种类型：

| 类型 | 用途 | 提醒策略 |
|------|------|---------|
| idea | 灵感/想法 | 首次 3 天后，间隔递增 |
| todo | 待办事项 | 根据截止日期倒推 |
| flash | 闪念/临时记录 | 首次 1 天后，快速提醒 |

### 2.3 知识关系

四种关系类型：

```
parent（父子）：React 基础 → React Hooks
  └─ 主题范围更大，新知识是其子集

depends_on（依赖）：Context Engineering → 上下文隔离
  └─ 理解新知识必须先理解它

related_to（关联）：Agent Harness ↔ Context Engineering
  └─ 标签有交集、内容有交叉但不构成依赖

topic（主题）：同主题的条目自动归入同一目录
```

### 2.4 复习间隔（艾宾浩斯遗忘曲线）

```
录入 → 1天 → 3天 → 7天 → 14天 → 30天 → 永久记忆
        轮1    轮2    轮3    轮4    轮5    轮6+
```

评分调整：
- 5/4 分：按计划推进
- 3 分：维持当前间隔
- 2 分：间隔缩短一级
- 1/0 分：重置为轮次 1

---

## 三、命令参考

### 3.1 基础查询

```powershell
# 知识库状态总览
python ~/.ai-knowledge-base/kb.py status

# 统计信息
python ~/.ai-knowledge-base/kb.py stats

# 获取条目详情（含完整文档内容）
python ~/.ai-knowledge-base/kb.py get K-20260406-001

# 今日到期复习
python ~/.ai-knowledge-base/kb.py today-reviews

# 今日待提醒备忘
python ~/.ai-knowledge-base/kb.py today-reminds
```

### 3.2 知识管理

```powershell
# 录入知识（交互式内容）
python ~/.ai-knowledge-base/kb.py add-knowledge "标题" `
  --tags "tag1,tag2" --mastery 3 --score 4 `
  --topic "ai-agent" --parent "K-XXXXXX-XXX"

# 管道传入内容
echo "文档内容" | python ~/.ai-knowledge-base/kb.py add-knowledge "标题" `
  --tags "tag1" --mastery 3 --score 4

# 轻量列表（只返回 ID+标题+标签+主题）
python ~/.ai-knowledge-base/kb.py list-titles
python ~/.ai-knowledge-base/kb.py list-titles --tag ai-agent

# 查找关联候选（基于标签交集）
python ~/.ai-knowledge-base/kb.py related-candidates K-20260406-001

# 设置关系
python ~/.ai-knowledge-base/kb.py set-relation K-20260406-001 `
  --topic ai-agent --parent K-XXXXXX-XXX `
  --depends K-XXXXXX-XXX --related K-XXXXXX-XXX

# 合并两条知识
python ~/.ai-knowledge-base/kb.py merge-knowledge K-XXXXXXXX-001 K-XXXXXXXX-002

# 按主题整理目录
python ~/.ai-knowledge-base/kb.py auto-topic              # 执行整理
python ~/.ai-knowledge-base/kb.py auto-topic --check K-001 # 检查是否需要整理
```

### 3.3 复习管理

```powershell
# 记录复习结果
python ~/.ai-knowledge-base/kb.py review-done K-20260406-001 `
  --score 4 `
  --question "题目内容" `
  --answer "用户回答摘要" `
  --note "评估备注"
```

### 3.4 备忘管理

```powershell
# 创建备忘
python ~/.ai-knowledge-base/kb.py add-memo "内容描述" `
  --type idea --priority mid --deadline "2026-04-13"

# 标记完成
python ~/.ai-knowledge-base/kb.py memo-done M-20260406-001

# 归档
python ~/.ai-knowledge-base/kb.py memo-archive M-20260406-001

# 更新提醒日期
python ~/.ai-knowledge-base/kb.py update-remind M-20260406-001 --date "2026-04-15"
```

### 3.5 学习计划

```powershell
# 创建学习计划
python ~/.ai-knowledge-base/kb.py create-plan "主题" `
  --days 15 --goal "目标描述" `
  --outline "Day 1: ...\nDay 2: ..."

# 查看所有计划状态
python ~/.ai-knowledge-base/kb.py plan-status

# 获取今日学习内容
python ~/.ai-knowledge-base/kb.py today-lesson

# 标记当天完成（plan_file 从 today-lesson 返回值获取）
python ~/.ai-knowledge-base/kb.py lesson-done "plans/文件路径.md" `
  --day 3 --score 4 `
  --knowledge-id K-YYYYMMDD-NNN --note "备注"

# 更新计划（调整大纲或记录调整说明）
python ~/.ai-knowledge-base/kb.py update-plan "plans/文件路径.md" `
  --outline "新大纲内容" `
  --adjustment "调整说明"
```

---

## 四、Skills 使用指南

Skills 定义了 AI 的行为流程，存放在 `~/.config/opencode/skills/` 下。

### 4.1 knowledge-learn — 知识学习

**触发方式：** 用户输入一段知识碎片（如 "今天学了 XXX"）

**流程：**

```
用户输入 → AI 复述确认 → 1 个基础问题评估 → 自适应追问(1-6 问)
    → 关系推断（检查已有知识的标签交集，确认关联类型）
    → 生成 Markdown 文档 → kb.py add-knowledge 录入
```

**追问策略（自适应深度）：**

| 初始评分 | 追问深度 | 层级 |
|---------|---------|------|
| 5 分 | 1-2 问 | L3 关联类比 |
| 3-4 分 | 3-4 问 | L1+L2 |
| 1-2 分 | 5-6 问 | L1+L2+L3 完整三轮 |

### 4.2 knowledge-review — 间隔复习

**触发方式：** 用户说"复习"或有到期复习

**流程：**

```
today-reviews → 展示复习清单 → 逐条出题
    → 主题聚合检查（同 topic 多条到期时组合出题）
    → 按轮次选择题型 → 用户回答 → AI 评分
    → review-done 记录 → 输出复习报告
```

**出题方式按轮次：**

| 轮次 | 题型 | 目标 |
|------|------|------|
| 1 | 简答题：概念复述 | 验证基本记忆 |
| 2 | 填空题：代码补全 | 验证细节掌握 |
| 3 | 场景分析题 | 验证实际应用 |
| 4 | 跨知识点综合 | 验证知识整合 |
| 5 | 教学讲解题 | 费曼终极测试 |

**快速复习模式：** 用户说"快速"时，每条只问"还记得吗？"，回答 "记住了"=5 分、"模糊"=3 分、"忘了"=1 分。

### 4.3 knowledge-memo — 智能备忘

**触发方式：** 用户记录 idea / todo / 闪念

**功能：**
- 自动分类（idea/todo/flash）
- 定时提醒（根据类型和优先级计算）
- 状态追踪（pending → done → archived）

### 4.4 knowledge-plan — 学习计划

**触发方式：** 用户说"我想系统学习 XXX"、"帮我制定学习计划"、"今天该学什么"

**流程：**

```
需求确认（水平/目标/时间/截止日期）
    → 生成课程大纲（前 3 天详细，后续粗略）
    → create-plan 录入
    → 每日循环:
        today-lesson → AI 讲解 → 苏格拉底追问 → 评估
        → add-knowledge 录入 → lesson-done 记录
    → 动态调整:
        掌握度 >=4 → 按计划推进
        掌握度 ==3 → 插入巩固
        掌握度 <=2 → 重学
```

---

## 五、最佳实践

### 5.1 录入知识时

1. 标签使用英文小写，2-5 个，用逗号分隔
2. 设置 `--topic` 让同主题知识自动归组
3. 利用关系推断（步骤 3e）建立知识间的关联
4. mastery 诚实评估，不要高估

### 5.2 日常使用

```powershell
# 每天开始时查看状态
python ~/.ai-knowledge-base/kb.py status

# 有复习时先复习再学新
python ~/.ai-knowledge-base/kb.py today-reviews

# 有学习计划时查看今日任务
python ~/.ai-knowledge-base/kb.py today-lesson
```

### 5.3 PowerShell 编码注意

由于 Windows PowerShell 默认编码可能影响中文显示，建议在命令前设置：

```powershell
$env:PYTHONIOENCODING="utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

或在 PowerShell Profile 中永久设置。

---

## 六、设计哲学

1. **AI 只做智能工作** — 对话、评分、出题、内容生成
2. **kb.py 只做程序化工作** — 文件读写、日期计算、数据查询
3. **数据透明** — 所有数据存储为 Markdown/JSON，人类可读可编辑
4. **渐进增强** — 从碎片学习到系统学习，逐步引入功能
5. **费曼学习法** — 通过"教"来"学"，追问是最好的巩固方式

---

## 七、命令速查表

| 命令 | 用途 |
|------|------|
| `init` | 初始化知识库 |
| `status` | 状态总览 |
| `stats` | 统计信息 |
| `get <id>` | 获取条目详情 |
| `list-titles [--tag]` | 轻量知识列表 |
| `add-knowledge <title>` | 录入知识 |
| `related-candidates <id>` | 查找关联候选 |
| `set-relation <id>` | 设置知识关系 |
| `merge-knowledge <p> <s>` | 合并两条知识 |
| `auto-topic [--check]` | 按主题整理目录 |
| `today-reviews` | 今日到期复习 |
| `review-done <id>` | 记录复习结果 |
| `add-memo <content>` | 创建备忘 |
| `memo-done <id>` | 标记备忘完成 |
| `memo-archive <id>` | 归档备忘 |
| `update-remind <id>` | 更新提醒日期 |
| `create-plan <topic>` | 创建学习计划 |
| `plan-status` | 查看计划状态 |
| `today-lesson` | 今日学习内容 |
| `lesson-done <file>` | 标记课时完成 |
| `update-plan <file>` | 更新学习计划 |
