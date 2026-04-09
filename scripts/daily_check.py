from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_kb(*args: str) -> dict:
    script = Path(__file__).resolve().with_name("kb.py")
    cmd = [sys.executable, str(script), *args]
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Knowledge Base daily check")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parsed = parser.parse_args()

    reviews = run_kb("today-reviews")
    reminds = run_kb("today-reminds")

    result = {
        "date": reviews.get("date") or reminds.get("date"),
        "review_count": int(reviews.get("due_count", 0)),
        "remind_count": int(reminds.get("remind_count", 0)),
        "reviews": reviews.get("items", []),
        "reminds": reminds.get("items", []),
    }

    if parsed.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("AI Knowledge Base Daily Check")
    print(f"Date: {result['date']}")
    print()

    if result["review_count"] == 0 and result["remind_count"] == 0:
        print("No due reviews or memo reminders today.")
        return 0

    print(f"Due reviews: {result['review_count']}")
    for item in result["reviews"]:
        title = item.get("title") or "(untitled)"
        round_text = f"Round {item['round']}" if item.get("round") else "Round n/a"
        print(f"- [{item.get('id')}] {title} ({round_text})")

    print()
    print(f"Memo reminders: {result['remind_count']}")
    for item in result["reminds"]:
        summary = item.get("summary") or "(no summary)"
        kind = item.get("type") or "unknown"
        status = item.get("status") or "pending"
        print(f"- [{item.get('id')}] {summary} | type: {kind} | status: {status}")

    print()
    print("Suggested next actions:")
    if result["review_count"] > 0:
        print("- Start with knowledge-review for today's due items.")
    if result["remind_count"] > 0:
        print("- Then handle memo reminders in knowledge-memo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
