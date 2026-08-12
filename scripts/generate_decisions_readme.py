"""
scripts/generate_decisions_readme.py

يُعيد توليد جدول الفهرس في docs/decisions/README.md من titan.timeline._data.

titan.timeline._data هو مصدر الحقيقة الوحيد لبيانات القرارات. هذا السكربت
يُشغَّل يدوياً عند إضافة أو تعديل قرار — لا صيانة يدوية مزدوجة للجدول.

الاستخدام:
    python scripts/generate_decisions_readme.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from titan.timeline import entries  # noqa: E402

README_PATH = ROOT / "docs" / "decisions" / "README.md"
START_MARKER = "## Index"


def build_index_table() -> str:
    lines = ["## Index", "", "| # | Title | Status |", "|---|---|---|"]
    for e in entries():
        filename = Path(e.path).name
        lines.append(f"| [{e.number}]({filename}) | {e.title} | {e.status} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    content = README_PATH.read_text(encoding="utf-8")
    marker_index = content.find(START_MARKER)
    if marker_index == -1:
        raise SystemExit(f"'{START_MARKER}' not found in {README_PATH}")

    before = content[:marker_index]
    new_content = before + build_index_table()

    README_PATH.write_text(new_content, encoding="utf-8")
    print(f"Updated {README_PATH} with {len(entries())} entries.")


if __name__ == "__main__":
    main()
