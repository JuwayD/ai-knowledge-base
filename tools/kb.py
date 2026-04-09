#!/usr/bin/env python3
"""
kb.py - AI Knowledge Base CLI Tool
知识库数据管理工具，处理所有文件 IO、日期计算、数据查询等程序化操作。
LLM 只负责对话、评分、出题等需要智能的工作。

用法:
  python kb.py <command> [options]

命令:
  init                        初始化知识库
  today-reviews               列出今日到期复习条目
  today-reminds               列出今日待提醒备忘
  status                      备忘录状态总览
  stats                       知识库统计信息
  get <id>                    获取条目详情

  add-knowledge <title>       创建知识条目
    --tags "a,b,c"            标签
    --mastery <n>             掌握度 1-5
    --score <n>               初始追问评分 1-5
    --content <text|stdin>    知识文档内容

  add-memo <content>          创建备忘条目
    --type <idea|todo|flash>  类型
    --priority <high|mid|low> 优先级(idea)
    --deadline <YYYY-MM-DD>   截止日期(todo)

  review-done <id>            记录复习结果
    --score <n>               复习评分 0-5
    --question <text>         题目
    --answer <text>           用户回答摘要
    --note <text>             评估备注

  memo-done <id>              标记备忘完成
  memo-archive <id>           归档备忘
  update-remind <id>          更新提醒日期
    --date <YYYY-MM-DD>       新提醒日期
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

KB_DIR = Path(os.environ.get("KB_HOME", Path.home() / ".ai-knowledge-base"))
INDEX_FILE = KB_DIR / "index.md"
KNOWLEDGE_DIR = KB_DIR / "knowledge"
MEMOS_DIR = KB_DIR / "memos"
DAILY_DIR = KB_DIR / "daily"
REVIEWS_DIR = KB_DIR / "reviews"
PLANS_DIR = KB_DIR / "plans"

INTERVALS = [1, 3, 7, 14, 30]
PERMANENT_ROUND = len(INTERVALS) + 1


def ensure_dirs():
    for d in [KB_DIR, KNOWLEDGE_DIR, MEMOS_DIR, DAILY_DIR, REVIEWS_DIR, PLANS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def today_dt():
    return datetime.now().strftime("%Y%m%d")


def slugify(text, max_len=40):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:max_len]


def next_id(entries, prefix, date_str=None):
    date_part = date_str or today_dt()
    max_seq = 0
    for e in entries:
        m = re.match(rf"{prefix}-(\d{{8}})-(\d{{3}})", e.get("id", ""))
        if m and m.group(1) == date_part:
            seq = int(m.group(2))
            if seq > max_seq:
                max_seq = seq
    return f"{prefix}-{date_part}-{max_seq + 1:03d}"


def parse_index():
    if not INDEX_FILE.exists():
        return {"knowledge": [], "memos": [], "review_plan": []}

    content = INDEX_FILE.read_text(encoding="utf-8")
    knowledge = []
    memos = []
    review_plan = []

    section = None
    current_k = None
    current_m = None
    current_r_date = None

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped == "## 知识条目":
            section = "knowledge"
            continue
        elif stripped == "## 备忘条目":
            section = "memos"
            current_k = None
            continue
        elif stripped == "## 复习计划":
            section = "review"
            current_m = None
            continue

        if section == "knowledge":
            m = re.match(r"###\s+(K-\d{8}-\d{3})\s*\|\s*(.+)", stripped)
            if m:
                current_k = {
                    "id": m.group(1),
                    "title": m.group(2).strip(),
                    "file": "",
                    "tags": [],
                    "mastery": 0,
                    "created": "",
                    "next_review": "",
                    "round": 0,
                    "review_history": [],
                    "topic": "",
                    "parent": "",
                    "depends_on": "",
                    "related_to": [],
                }
                knowledge.append(current_k)
                continue

            if current_k and stripped.startswith("- "):
                kv_match = re.match(r"-\s+(\w[\w\u4e00-\u9fff]*)\s*:\s*(.+)", stripped)
                if kv_match:
                    key = kv_match.group(1)
                    val = kv_match.group(2).strip()
                    if key == "文件":
                        current_k["file"] = val
                    elif key == "标签":
                        current_k["tags"] = [t.strip() for t in val.split(",")]
                    elif key == "掌握度":
                        mastery_match = re.match(r"(\d)", val)
                        current_k["mastery"] = (
                            int(mastery_match.group(1)) if mastery_match else 0
                        )
                    elif key == "创建":
                        current_k["created"] = val
                    elif key == "下次复习":
                        current_k["next_review"] = val
                    elif key == "复习轮次":
                        current_k["round"] = int(val)
                    elif key == "主题":
                        current_k["topic"] = val
                    elif key == "父级":
                        current_k["parent"] = val if val != "-" else ""
                    elif key == "依赖":
                        current_k["depends_on"] = val if val != "-" else ""
                    elif key == "关联":
                        current_k["related_to"] = [
                            x.strip() for x in val.split(",") if x.strip() and x != "-"
                        ]
                elif "review_history" in (current_k or {}):
                    hist_match = re.match(
                        r"-\s+\[(.+?):\s*(.+?)(?:,\s*追问评分\s*)?(\d+)/5\]?\s*$",
                        stripped,
                    )
                    if hist_match:
                        current_k["review_history"].append(
                            {
                                "date": hist_match.group(1).strip(),
                                "info": hist_match.group(2).strip(),
                            }
                        )

        elif section == "memos":
            m = re.match(r"###\s+(M-\d{8}-\d{3})\s*\|\s*(.+)", stripped)
            if m:
                current_m = {
                    "id": m.group(1),
                    "summary": m.group(2).strip(),
                    "type": "",
                    "status": "pending",
                    "created": "",
                    "next_remind": "",
                    "deadline": "",
                }
                memos.append(current_m)
                continue

            if current_m and stripped.startswith("- "):
                kv_match = re.match(r"-\s+(\w[\w\u4e00-\u9fff]*)\s*:\s*(.+)", stripped)
                if kv_match:
                    key = kv_match.group(1)
                    val = kv_match.group(2).strip()
                    if key == "类型":
                        current_m["type"] = val
                    elif key == "状态":
                        current_m["status"] = val
                    elif key == "创建":
                        current_m["created"] = val
                    elif key == "下次提醒":
                        current_m["next_remind"] = val
                    elif key == "截止日期":
                        current_m["deadline"] = val

        elif section == "review":
            date_match = re.match(r"###\s+(\d{4}-\d{2}-\d{2})\s+到期", stripped)
            if date_match:
                current_r_date = date_match.group(1)
                review_plan.append({"date": current_r_date, "items": []})
                continue

            item_match = re.match(
                r"-\s+\[.\]\s+(K-\d{8}-\d{3})\s+(.+?)\s*\(第(\d+)轮", stripped
            )
            if item_match and current_r_date:
                for rp in review_plan:
                    if rp["date"] == current_r_date:
                        rp["items"].append(
                            {
                                "id": item_match.group(1),
                                "title": item_match.group(2).strip(),
                                "round": int(item_match.group(3)),
                            }
                        )

    return {"knowledge": knowledge, "memos": memos, "review_plan": review_plan}


def write_index(data):
    lines = [
        "# AI Knowledge Base Index",
        "",
        "> 本文件由 kb.py 自动维护，请勿手动修改格式",
        "",
        "---",
        "",
    ]

    lines.append("## 知识条目")
    lines.append("")
    for k in data["knowledge"]:
        lines.append(f"### {k['id']} | {k['title']}")
        lines.append(f"- 文件: {k['file']}")
        lines.append(f"- 标签: {', '.join(k['tags'])}")
        lines.append(f"- 掌握度: {k['mastery']}/5")
        lines.append(f"- 创建: {k['created']}")
        lines.append(f"- 下次复习: {k['next_review']}")
        lines.append(f"- 复习轮次: {k['round']}")
        lines.append(f"- 主题: {k.get('topic') or '-'}")
        lines.append(f"- 父级: {k.get('parent') or '-'}")
        lines.append(f"- 依赖: {k.get('depends_on') or '-'}")
        lines.append(f"- 关联: {', '.join(k.get('related_to', [])) or '-'}")
        lines.append("- 复习历史:")
        for h in k.get("review_history", []):
            lines.append(f"  - [{h['date']}: {h['info']}]")
        lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 备忘条目")
    lines.append("")
    for m in data["memos"]:
        lines.append(f"### {m['id']} | {m['summary']}")
        lines.append(f"- 类型: {m['type']}")
        lines.append(f"- 状态: {m['status']}")
        lines.append(f"- 创建: {m['created']}")
        lines.append(f"- 下次提醒: {m['next_remind']}")
        lines.append(f"- 截止日期: {m['deadline']}")
        lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 复习计划")
    lines.append("")
    for rp in sorted(data["review_plan"], key=lambda x: x["date"]):
        lines.append(f"### {rp['date']} 到期")
        lines.append("")
        for item in rp["items"]:
            lines.append(f"- [ ] {item['id']} {item['title']} (第{item['round']}轮)")
        lines.append("")

    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compute_next_review(round_num, score):
    if score >= 4:
        idx = min(round_num, len(INTERVALS) - 1)
    elif score == 3:
        idx = min(round_num - 1, len(INTERVALS) - 1)
        idx = max(idx, 0)
    elif score == 2:
        idx = max(round_num - 2, 0)
    else:
        return 1, 1

    interval = INTERVALS[idx]
    new_round = idx + 2
    return new_round, interval


def compute_memo_remind(memo_type, created_str, priority="mid", deadline=""):
    created = datetime.strptime(created_str, "%Y-%m-%d")
    if memo_type == "idea":
        days_map = {"high": 2, "mid": 3, "low": 5}
        return (created + timedelta(days=days_map.get(priority, 3))).strftime(
            "%Y-%m-%d"
        )
    elif memo_type == "todo":
        if deadline:
            dl = datetime.strptime(deadline, "%Y-%m-%d")
            remind = min(created + timedelta(days=3), dl - timedelta(days=1))
            return remind.strftime("%Y-%m-%d")
        return (created + timedelta(days=3)).strftime("%Y-%m-%d")
    else:
        return (created + timedelta(days=7)).strftime("%Y-%m-%d")


# === COMMANDS ===


def cmd_init(args):
    ensure_dirs()
    if not INDEX_FILE.exists():
        write_index({"knowledge": [], "memos": [], "review_plan": []})
    print(json.dumps({"status": "ok", "path": str(KB_DIR)}, ensure_ascii=False))


def cmd_today_reviews(args):
    data = parse_index()
    today = today_str()
    due = []
    for rp in data["review_plan"]:
        if rp["date"] <= today:
            for item in rp["items"]:
                k_entry = next(
                    (k for k in data["knowledge"] if k["id"] == item["id"]), None
                )
                if k_entry:
                    due.append(
                        {
                            "id": item["id"],
                            "title": item["title"],
                            "round": item["round"],
                            "file": k_entry["file"],
                            "mastery": k_entry["mastery"],
                            "next_review": rp["date"],
                        }
                    )
    print(
        json.dumps(
            {"date": today, "due_count": len(due), "items": due},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_today_reminds(args):
    data = parse_index()
    today = today_str()
    reminds = []
    for m in data["memos"]:
        if m["status"] in ("done", "archived"):
            continue
        if m["next_remind"] and m["next_remind"] <= today:
            reminds.append(m)
    print(
        json.dumps(
            {"date": today, "remind_count": len(reminds), "items": reminds},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_status(args):
    data = parse_index()
    active_memos = [m for m in data["memos"] if m["status"] not in ("done", "archived")]
    done_memos = [m for m in data["memos"] if m["status"] == "done"]
    archived_memos = [m for m in data["memos"] if m["status"] == "archived"]
    total_k = len(data["knowledge"])
    permanent_k = sum(1 for k in data["knowledge"] if k["round"] >= PERMANENT_ROUND)

    result = {
        "knowledge": {
            "total": total_k,
            "permanent": permanent_k,
            "active": total_k - permanent_k,
        },
        "memos": {
            "active": len(active_memos),
            "done": len(done_memos),
            "archived": len(archived_memos),
            "by_type": {
                "idea": [m for m in active_memos if m["type"] == "idea"],
                "todo": [m for m in active_memos if m["type"] == "todo"],
                "flash": [m for m in active_memos if m["type"] == "闪念"],
            },
        },
        "today_reviews": 0,
        "today_reminds": 0,
    }

    today = today_str()
    for rp in data["review_plan"]:
        if rp["date"] <= today:
            result["today_reviews"] += len(rp["items"])
    result["today_reminds"] = (
        len(reminds)
        if (
            reminds := [
                m
                for m in data["memos"]
                if m["status"] not in ("done", "archived")
                and m["next_remind"]
                and m["next_remind"] <= today
            ]
        )
        else 0
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_get(args):
    data = parse_index()
    entry_id = args.id

    for k in data["knowledge"]:
        if k["id"] == entry_id:
            file_path = KNOWLEDGE_DIR / k["file"].replace("knowledge/", "")
            content = (
                file_path.read_text(encoding="utf-8")
                if file_path.exists()
                else "(文件不存在)"
            )
            print(
                json.dumps(
                    {
                        "type": "knowledge",
                        "id": k["id"],
                        "title": k["title"],
                        "tags": k["tags"],
                        "mastery": k["mastery"],
                        "created": k["created"],
                        "next_review": k["next_review"],
                        "round": k["round"],
                        "file": str(file_path),
                        "content": content,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

    for m in data["memos"]:
        if m["id"] == entry_id:
            slug = slugify(m["summary"])
            pattern = f"*{m['id'].split('-')[1]}*{slug[:20]}*"
            matches = list(MEMOS_DIR.glob(pattern))
            content = (
                matches[0].read_text(encoding="utf-8") if matches else "(文件不存在)"
            )
            print(
                json.dumps(
                    {
                        "type": "memo",
                        **m,
                        "content": content,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

    print(json.dumps({"error": f"未找到条目: {entry_id}"}, ensure_ascii=False))


def cmd_add_knowledge(args):
    data = parse_index()
    entry_id = next_id(data["knowledge"], "K")
    date_str = today_str()
    date_compact = today_dt()
    slug = slugify(args.title)

    seq = int(entry_id.split("-")[-1])
    filename = f"{date_compact}_{seq:03d}_{slug}.md"
    filepath = KNOWLEDGE_DIR / filename

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    mastery = int(args.mastery) if args.mastery else 3
    score = int(args.score) if args.score else 3

    next_review = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    content = args.content
    if content is None:
        if not sys.stdin.isatty():
            raw = sys.stdin.buffer.read()
            content = raw.decode("utf-8", errors="replace")
        else:
            content = f"# {args.title}\n\n> 待补充详细内容\n"

    filepath.write_text(content, encoding="utf-8")

    k_entry = {
        "id": entry_id,
        "title": args.title,
        "file": f"knowledge/{filename}",
        "tags": tags,
        "mastery": mastery,
        "created": date_str,
        "next_review": next_review,
        "round": 1,
        "review_history": [
            {
                "date": date_str,
                "info": f"初始录入，追问评分 {score}/5",
            }
        ],
        "topic": args.topic if hasattr(args, "topic") and args.topic else "",
        "parent": args.parent if hasattr(args, "parent") and args.parent else "",
        "depends_on": "",
        "related_to": [],
    }
    data["knowledge"].append(k_entry)

    rp_date = next_review
    found = False
    for rp in data["review_plan"]:
        if rp["date"] == rp_date:
            rp["items"].append(
                {
                    "id": entry_id,
                    "title": args.title,
                    "round": 2,
                }
            )
            found = True
            break
    if not found:
        data["review_plan"].append(
            {
                "date": rp_date,
                "items": [
                    {
                        "id": entry_id,
                        "title": args.title,
                        "round": 2,
                    }
                ],
            }
        )

    write_index(data)

    result = {
        "status": "ok",
        "id": entry_id,
        "title": args.title,
        "file": str(filepath),
        "next_review": next_review,
        "mastery": mastery,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_list_titles(args):
    data = parse_index()
    tag_filter = args.tag if hasattr(args, "tag") and args.tag else None

    items = []
    for k in data["knowledge"]:
        if tag_filter and tag_filter not in k["tags"]:
            continue
        items.append(
            {
                "id": k["id"],
                "title": k["title"],
                "tags": k["tags"],
                "topic": k.get("topic", ""),
            }
        )

    print(
        json.dumps({"count": len(items), "items": items}, ensure_ascii=False, indent=2)
    )


def cmd_related_candidates(args):
    data = parse_index()
    entry_id = args.id
    target = next((k for k in data["knowledge"] if k["id"] == entry_id), None)
    if not target:
        print(json.dumps({"error": f"未找到: {entry_id}"}, ensure_ascii=False))
        return

    target_tags = set(target["tags"])
    candidates = []
    for k in data["knowledge"]:
        if k["id"] == entry_id:
            continue
        overlap = len(target_tags & set(k["tags"]))
        if overlap > 0:
            candidates.append(
                {
                    "id": k["id"],
                    "title": k["title"],
                    "tags": k["tags"],
                    "overlap_count": overlap,
                    "topic": k.get("topic", ""),
                }
            )

    candidates.sort(key=lambda x: x["overlap_count"], reverse=True)
    candidates = candidates[:5]

    print(
        json.dumps(
            {"target": entry_id, "candidates": candidates},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_set_relation(args):
    data = parse_index()
    entry_id = args.id
    target = next((k for k in data["knowledge"] if k["id"] == entry_id), None)
    if not target:
        print(json.dumps({"error": f"未找到: {entry_id}"}, ensure_ascii=False))
        return

    changes = {}
    if args.topic:
        target["topic"] = args.topic
        changes["topic"] = args.topic
    if args.parent:
        target["parent"] = args.parent
        changes["parent"] = args.parent
    if args.depends:
        target["depends_on"] = args.depends
        changes["depends_on"] = args.depends
    if args.related:
        related_ids = [x.strip() for x in args.related.split(",")]
        target["related_to"] = related_ids
        changes["related_to"] = related_ids

    write_index(data)
    print(
        json.dumps(
            {"status": "ok", "id": entry_id, "changes": changes},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_merge_knowledge(args):
    data = parse_index()
    primary_id = args.primary
    secondary_id = args.secondary

    primary = next((k for k in data["knowledge"] if k["id"] == primary_id), None)
    secondary = next((k for k in data["knowledge"] if k["id"] == secondary_id), None)

    if not primary or not secondary:
        print(json.dumps({"error": "条目未找到"}, ensure_ascii=False))
        return

    p_path = KNOWLEDGE_DIR / primary["file"].replace("knowledge/", "")
    s_path = KNOWLEDGE_DIR / secondary["file"].replace("knowledge/", "")

    merged_tags = list(set(primary["tags"] + secondary["tags"]))
    primary["tags"] = merged_tags

    merged_related = list(
        set(
            primary.get("related_to", [])
            + secondary.get("related_to", [])
            + [secondary_id]
        )
    )
    merged_related = [r for r in merged_related if r != primary_id]
    primary["related_to"] = merged_related

    primary["review_history"].extend(secondary["review_history"])

    primary["mastery"] = min(primary["mastery"], secondary["mastery"])

    for rp in data["review_plan"]:
        rp["items"] = [i for i in rp["items"] if i["id"] != secondary_id]
    data["review_plan"] = [rp for rp in data["review_plan"] if rp["items"]]

    write_index(data)

    print(
        json.dumps(
            {
                "status": "ok",
                "primary": primary_id,
                "merged_from": secondary_id,
                "message": "结构已合并。请手动将 secondary 文件内容合并到 primary 文件中，然后删除 secondary 文件。",
                "primary_file": str(p_path),
                "secondary_file": str(s_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_auto_topic(args):
    data = parse_index()

    check_id = args.check if hasattr(args, "check") and args.check else None

    topic_groups = {}
    for k in data["knowledge"]:
        t = k.get("topic", "")
        if t:
            topic_groups.setdefault(t, []).append(k)

    if check_id:
        target = next((k for k in data["knowledge"] if k["id"] == check_id), None)
        if target and target.get("topic"):
            group = topic_groups.get(target["topic"], [])
            needs_reorg = len(group) >= 2
            print(
                json.dumps(
                    {
                        "needs_reorg": needs_reorg,
                        "topic": target["topic"],
                        "count_in_topic": len(group),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(json.dumps({"needs_reorg": False}, ensure_ascii=False))
        return

    results = []
    for topic, entries in topic_groups.items():
        if len(entries) < 2:
            continue

        topic_dir = KNOWLEDGE_DIR / slugify(topic, max_len=30)
        topic_dir.mkdir(parents=True, exist_ok=True)

        for k in entries:
            old_path = KNOWLEDGE_DIR / k["file"].replace("knowledge/", "")
            if old_path.exists() and old_path.parent != topic_dir:
                new_path = topic_dir / old_path.name
                old_path.rename(new_path)
                k["file"] = f"knowledge/{slugify(topic, max_len=30)}/{old_path.name}"
                results.append({"id": k["id"], "moved_to": str(new_path)})

        topic_file = topic_dir / "_topic.md"
        if not topic_file.exists():
            topic_content = f"# 主题: {topic}\n\n> 自动生成\n\n## 包含知识\n\n"
            for k in entries:
                topic_content += f"- {k['id']} | {k['title']}\n"
            topic_file.write_text(topic_content, encoding="utf-8")

    write_index(data)
    print(
        json.dumps(
            {"status": "ok", "reorganized": results}, ensure_ascii=False, indent=2
        )
    )


def cmd_create_plan(args):
    ensure_dirs()
    date_str = today_str()
    date_compact = today_dt()
    slug = slugify(args.topic)

    existing = list(PLANS_DIR.glob(f"{date_compact}_*.md"))
    seq = len(existing) + 1
    plan_id = f"P-{date_compact}-{seq:03d}"

    filename = f"{date_compact}_{slug}.md"
    filepath = PLANS_DIR / filename

    plan_content = f"""# 学习计划: {args.topic}

> 计划ID: {plan_id}
> 状态: in_progress | 创建: {date_str} | 目标: {args.goal or "掌握核心概念"}
> 总天数: {args.days or 15} | 当前进度: Day 0

---

## 课程大纲（粗略）

{args.outline or "_(待 AI 根据每日掌握情况动态生成)_"}

---

## 每日计划

_(每天学习完成后由 lesson-done 更新)_

---

## 调整记录

_(动态调整时记录)_
"""
    filepath.write_text(plan_content, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "plan_id": plan_id,
                "file": str(filepath),
                "topic": args.topic,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_plan_status(args):
    ensure_dirs()
    plans = []
    for f in sorted(PLANS_DIR.glob("*.md")):
        if f.name.startswith("_"):
            continue
        content = f.read_text(encoding="utf-8")
        plan_id = ""
        status = ""
        topic = ""
        progress = ""
        for line in content.split("\n"):
            if line.startswith("> 计划ID:"):
                plan_id = line.split(":", 1)[1].strip()
            elif "状态:" in line:
                m = re.search(r"状态:\s*(\w+)", line)
                if m:
                    status = m.group(1)
            elif "当前进度:" in line:
                m = re.search(r"当前进度:\s*Day\s*(\d+)", line)
                if m:
                    progress = f"Day {m.group(1)}"
        title_match = re.match(r"# 学习计划:\s*(.+)", content)
        topic = title_match.group(1).strip() if title_match else f.name

        plans.append(
            {
                "plan_id": plan_id,
                "file": str(f),
                "topic": topic,
                "status": status,
                "progress": progress,
            }
        )

    print(
        json.dumps({"count": len(plans), "plans": plans}, ensure_ascii=False, indent=2)
    )


def cmd_today_lesson(args):
    ensure_dirs()
    data = parse_index()
    today = today_str()

    lessons = []
    for f in sorted(PLANS_DIR.glob("*.md")):
        if f.name.startswith("_"):
            continue
        content = f.read_text(encoding="utf-8")

        if "in_progress" not in content:
            continue

        m = re.search(r"当前进度:\s*Day\s*(\d+)", content)
        current_day = int(m.group(1)) if m else 0
        next_day = current_day + 1

        m = re.search(r"总天数:\s*(\d+)", content)
        total_days = int(m.group(1)) if m else 15

        title_match = re.match(r"# 学习计划:\s*(.+)", content)
        topic = title_match.group(1).strip() if title_match else f.name

        plan_id_match = re.search(r"计划ID:\s*(P-\d{8}-\d{3})", content)
        plan_id = plan_id_match.group(1) if plan_id_match else ""

        if current_day >= total_days:
            status_msg = "已完成全部课时"
        else:
            status_msg = f"今天学习 Day {next_day}"

        related_knowledge = [
            {
                "id": k["id"],
                "title": k["title"],
                "mastery": k["mastery"],
                "next_review": k["next_review"],
            }
            for k in data["knowledge"]
            if k.get("topic", "") == slugify(topic, max_len=30)
            or any(t in k["tags"] for t in [slugify(topic)])
        ]

        lessons.append(
            {
                "plan_id": plan_id,
                "topic": topic,
                "current_day": current_day,
                "next_day": next_day,
                "total_days": total_days,
                "status": status_msg,
                "file": str(f),
                "related_knowledge": related_knowledge,
            }
        )

    print(json.dumps({"date": today, "lessons": lessons}, ensure_ascii=False, indent=2))


def cmd_lesson_done(args):
    ensure_dirs()
    plan_file = args.plan_file
    day = args.day
    score = int(args.score)
    knowledge_id = args.knowledge_id or ""
    note = args.note or ""
    today = today_str()

    filepath = Path(plan_file)
    if not filepath.exists():
        print(json.dumps({"error": f"计划文件不存在: {plan_file}"}, ensure_ascii=False))
        return

    content = filepath.read_text(encoding="utf-8")

    old_day_match = re.search(r"当前进度:\s*Day\s*\d+", content)
    if old_day_match:
        content = content.replace(old_day_match.group(), f"当前进度: Day {day}")

    day_record = f"\n### Day {day} - {today}\n- 状态: 完成完成\n- 评分: {score}/5"
    if knowledge_id:
        day_record += f"\n- 知识条目: {knowledge_id}"
    if note:
        day_record += f"\n- 备注: {note}"

    if "## 调整记录" in content:
        content = content.replace("## 调整记录", day_record + "\n\n---\n\n## 调整记录")
    else:
        content += day_record + "\n"

    filepath.write_text(content, encoding="utf-8")

    if score >= 4:
        strategy = "按计划推进下一天"
    elif score == 3:
        strategy = "插入巩固练习，然后继续"
    else:
        strategy = "重学今天内容"

    print(
        json.dumps(
            {"status": "ok", "day": day, "score": score, "next_strategy": strategy},
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_update_plan(args):
    plan_file = args.plan_file
    filepath = Path(plan_file)

    if not filepath.exists():
        print(json.dumps({"error": f"计划文件不存在: {plan_file}"}, ensure_ascii=False))
        return

    content = filepath.read_text(encoding="utf-8")
    today = today_str()

    if args.outline:
        old_outline = re.search(r"## 课程大纲.*?---", content, re.DOTALL)
        if old_outline:
            content = content.replace(
                old_outline.group(),
                f"## 课程大纲（粗略）\n\n{args.outline}\n\n---",
            )

    if args.adjustment:
        adj_section = f"\n### {today} 调整\n{args.adjustment}\n"
        content = content.rstrip() + "\n" + adj_section + "\n"

    filepath.write_text(content, encoding="utf-8")

    print(
        json.dumps(
            {"status": "ok", "file": str(filepath)}, ensure_ascii=False, indent=2
        )
    )


def cmd_add_memo(args):
    data = parse_index()
    entry_id = next_id(data["memos"], "M")
    date_str = today_str()
    date_compact = today_dt()

    memo_type = args.type or "idea"
    priority = args.priority or "mid"
    deadline = args.deadline or "-"

    summary = f"{memo_type}: {args.content[:60]}"
    slug = slugify(args.content)
    seq = int(entry_id.split("-")[-1])
    filename = f"{date_compact}_{seq:03d}_{memo_type}_{slug[:20]}.md"
    filepath = MEMOS_DIR / filename

    next_remind = compute_memo_remind(memo_type, date_str, priority, deadline)

    type_emoji = {"idea": "💡", "todo": "✅", "flash": "💭", "闪念": "💭"}
    priority_emoji = {"high": "🔴", "mid": "🟡", "low": "🟢"}

    doc_content = f"""# {args.content}

> 类型: {memo_type} | 状态: pending
> 创建: {date_str} | 下次提醒: {next_remind}

---

## 原始内容

{args.content}

## 补充信息

- 优先级: {priority_emoji.get(priority, priority)} {priority} ({"idea" if memo_type == "idea" else "todo"})
- 截止日期: {deadline}
- 标签: {", ".join(slugify(args.content).split("-")[:3])}

## 后续发展

_(等待展开)_

---

## 状态变更记录

| 日期 | 变更 | 备注 |
|------|------|------|
| {date_str} | 创建 | 初始录入 |
"""
    filepath.write_text(doc_content, encoding="utf-8")

    m_entry = {
        "id": entry_id,
        "summary": summary,
        "type": memo_type,
        "status": "pending",
        "created": date_str,
        "next_remind": next_remind,
        "deadline": deadline,
    }
    data["memos"].append(m_entry)
    write_index(data)

    result = {
        "status": "ok",
        "id": entry_id,
        "type": memo_type,
        "summary": summary,
        "next_remind": next_remind,
        "file": str(filepath),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_review_done(args):
    data = parse_index()
    entry_id = args.id
    score = int(args.score)
    question = args.question or ""
    answer = args.answer or ""
    note = args.note or ""
    today = today_str()

    k_entry = None
    for k in data["knowledge"]:
        if k["id"] == entry_id:
            k_entry = k
            break

    if not k_entry:
        print(json.dumps({"error": f"未找到知识条目: {entry_id}"}, ensure_ascii=False))
        return

    current_round = k_entry["round"]
    new_round, interval = compute_next_review(current_round, score)
    next_review_date = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")

    if new_round >= PERMANENT_ROUND:
        next_review_date = "永久"
        k_entry["mastery"] = 5

    k_entry["round"] = new_round
    k_entry["next_review"] = next_review_date
    if 0 < score <= 5:
        k_entry["mastery"] = min(score, 5)
    k_entry["review_history"].append(
        {
            "date": today,
            "info": note or f"第{current_round}轮复习，评分 {score}/5",
        }
    )

    for rp in data["review_plan"]:
        rp["items"] = [i for i in rp["items"] if i["id"] != entry_id]
    data["review_plan"] = [rp for rp in data["review_plan"] if rp["items"]]

    if next_review_date != "永久":
        found = False
        for rp in data["review_plan"]:
            if rp["date"] == next_review_date:
                rp["items"].append(
                    {
                        "id": entry_id,
                        "title": k_entry["title"],
                        "round": new_round,
                    }
                )
                found = True
                break
        if not found:
            data["review_plan"].append(
                {
                    "date": next_review_date,
                    "items": [
                        {
                            "id": entry_id,
                            "title": k_entry["title"],
                            "round": new_round,
                        }
                    ],
                }
            )

    write_index(data)

    review_month = today[:7]
    review_file = REVIEWS_DIR / f"{review_month}.md"
    if review_file.exists():
        review_content = review_file.read_text(encoding="utf-8")
    else:
        review_content = f"# 复习记录 - {review_month}\n\n"

    review_content += f"""
## {today} 复习记录

### {entry_id} | {k_entry["title"]}
- 轮次: {current_round}
- 题型: {["概念复述", "填空/补全", "场景判断", "跨知识点", "教新人"][min(current_round - 1, 4)]}
- 题目: {question}
- 用户回答: {answer}
- 评分: {score}/5
- 下次复习: {next_review_date} (间隔{interval}天)
- 备注: {note}

"""
    review_file.write_text(review_content, encoding="utf-8")

    file_path = KNOWLEDGE_DIR / k_entry["file"].replace("knowledge/", "")
    if file_path.exists():
        doc = file_path.read_text(encoding="utf-8")
        table_line = f"| {today} | {current_round} | {['概念复述', '填空/补全', '场景判断', '跨知识点', '教新人'][min(current_round - 1, 4)]} | {score}/5 | {note} |"
        if "## 复习记录" in doc:
            doc = doc.rstrip() + "\n" + table_line + "\n"
        else:
            doc += f"\n## 复习记录\n\n| 日期 | 轮次 | 题型 | 得分 | 备注 |\n|------|------|------|------|------|\n{table_line}\n"
        file_path.write_text(doc, encoding="utf-8")

    result = {
        "status": "ok",
        "id": entry_id,
        "score": score,
        "new_round": new_round,
        "interval_days": interval,
        "next_review": next_review_date,
        "permanent": next_review_date == "永久",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_memo_done(args):
    data = parse_index()
    entry_id = args.id
    today = today_str()

    for m in data["memos"]:
        if m["id"] == entry_id:
            m["status"] = "done"
            m["next_remind"] = "-"
            break
    else:
        print(json.dumps({"error": f"未找到备忘条目: {entry_id}"}, ensure_ascii=False))
        return

    write_index(data)
    print(
        json.dumps(
            {"status": "ok", "id": entry_id, "new_status": "done", "date": today},
            ensure_ascii=False,
        )
    )


def cmd_memo_archive(args):
    data = parse_index()
    entry_id = args.id

    for m in data["memos"]:
        if m["id"] == entry_id:
            m["status"] = "archived"
            m["next_remind"] = "-"
            break
    else:
        print(json.dumps({"error": f"未找到备忘条目: {entry_id}"}, ensure_ascii=False))
        return

    write_index(data)
    print(
        json.dumps(
            {"status": "ok", "id": entry_id, "new_status": "archived"},
            ensure_ascii=False,
        )
    )


def cmd_update_remind(args):
    data = parse_index()
    entry_id = args.id
    new_date = args.date

    for m in data["memos"]:
        if m["id"] == entry_id:
            m["next_remind"] = new_date
            break
    else:
        print(json.dumps({"error": f"未找到备忘条目: {entry_id}"}, ensure_ascii=False))
        return

    write_index(data)
    print(
        json.dumps(
            {"status": "ok", "id": entry_id, "next_remind": new_date},
            ensure_ascii=False,
        )
    )


def cmd_stats(args):
    data = parse_index()
    today = datetime.now()

    k_entries = data["knowledge"]
    m_entries = data["memos"]

    mastery_dist = {}
    for k in k_entries:
        m = k["mastery"]
        mastery_dist[m] = mastery_dist.get(m, 0) + 1

    due_soon = 0
    for rp in data["review_plan"]:
        for item in rp["items"]:
            try:
                rd = datetime.strptime(rp["date"], "%Y-%m-%d")
                if rd <= today + timedelta(days=7):
                    due_soon += 1
            except ValueError:
                pass

    result = {
        "knowledge": {
            "total": len(k_entries),
            "mastery_distribution": mastery_dist,
            "due_within_7_days": due_soon,
            "permanent": sum(1 for k in k_entries if k["round"] >= PERMANENT_ROUND),
        },
        "memos": {
            "total": len(m_entries),
            "active": sum(1 for m in m_entries if m["status"] == "pending"),
            "done": sum(1 for m in m_entries if m["status"] == "done"),
            "archived": sum(1 for m in m_entries if m["status"] == "archived"),
            "overdue_todos": sum(
                1
                for m in m_entries
                if m["type"] == "todo"
                and m["status"] == "pending"
                and m["deadline"] != "-"
                and m["deadline"] < today_str()
            ),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="AI Knowledge Base CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init")

    sub.add_parser("today-reviews")
    sub.add_parser("today-reminds")
    sub.add_parser("status")
    sub.add_parser("stats")

    get_p = sub.add_parser("get")
    get_p.add_argument("id")

    addk = sub.add_parser("add-knowledge")
    addk.add_argument("title")
    addk.add_argument("--tags", default="")
    addk.add_argument("--mastery", default="3")
    addk.add_argument("--score", default="3")
    addk.add_argument("--content", default=None)
    addk.add_argument("--topic", default="")
    addk.add_argument("--parent", default="")

    addm = sub.add_parser("add-memo")
    addm.add_argument("content")
    addm.add_argument("--type", default="idea", choices=["idea", "todo", "flash"])
    addm.add_argument("--priority", default="mid", choices=["high", "mid", "low"])
    addm.add_argument("--deadline", default="")

    rdone = sub.add_parser("review-done")
    rdone.add_argument("id")
    rdone.add_argument("--score", required=True)
    rdone.add_argument("--question", default="")
    rdone.add_argument("--answer", default="")
    rdone.add_argument("--note", default="")

    mdone = sub.add_parser("memo-done")
    mdone.add_argument("id")

    march = sub.add_parser("memo-archive")
    march.add_argument("id")

    urem = sub.add_parser("update-remind")
    urem.add_argument("id")
    urem.add_argument("--date", required=True)

    lt = sub.add_parser("list-titles")
    lt.add_argument("--tag", default="")

    rc = sub.add_parser("related-candidates")
    rc.add_argument("id")

    sr = sub.add_parser("set-relation")
    sr.add_argument("id")
    sr.add_argument("--topic", default="")
    sr.add_argument("--parent", default="")
    sr.add_argument("--depends", default="")
    sr.add_argument("--related", default="")

    mk = sub.add_parser("merge-knowledge")
    mk.add_argument("primary")
    mk.add_argument("secondary")

    at = sub.add_parser("auto-topic")
    at.add_argument("--check", default="")

    cp = sub.add_parser("create-plan")
    cp.add_argument("topic")
    cp.add_argument("--days", default="15")
    cp.add_argument("--goal", default="")
    cp.add_argument("--outline", default="")

    sub.add_parser("plan-status")

    sub.add_parser("today-lesson")

    ld = sub.add_parser("lesson-done")
    ld.add_argument("plan_file")
    ld.add_argument("--day", required=True)
    ld.add_argument("--score", required=True)
    ld.add_argument("--knowledge-id", default="")
    ld.add_argument("--note", default="")

    up = sub.add_parser("update-plan")
    up.add_argument("plan_file")
    up.add_argument("--outline", default="")
    up.add_argument("--adjustment", default="")

    args = parser.parse_args()

    ensure_dirs()

    commands = {
        "init": cmd_init,
        "today-reviews": cmd_today_reviews,
        "today-reminds": cmd_today_reminds,
        "status": cmd_status,
        "stats": cmd_stats,
        "get": cmd_get,
        "list-titles": cmd_list_titles,
        "related-candidates": cmd_related_candidates,
        "set-relation": cmd_set_relation,
        "merge-knowledge": cmd_merge_knowledge,
        "auto-topic": cmd_auto_topic,
        "create-plan": cmd_create_plan,
        "plan-status": cmd_plan_status,
        "today-lesson": cmd_today_lesson,
        "lesson-done": cmd_lesson_done,
        "update-plan": cmd_update_plan,
        "add-knowledge": cmd_add_knowledge,
        "add-memo": cmd_add_memo,
        "review-done": cmd_review_done,
        "memo-done": cmd_memo_done,
        "memo-archive": cmd_memo_archive,
        "update-remind": cmd_update_remind,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
