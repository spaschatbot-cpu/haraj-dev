#!/usr/bin/env python
"""Fail if a console link is written as a path instead of resolved by name.

The rule (spec 009 §"قواعد الصلاحيات" 5, T804): every link respects `APP_BASE`,
and nothing writes a console path by hand.

Why it matters here more than in most projects: v1 had four panels — `admin`,
`admin2`, `admin3`, `admin_v2` — and the console moved between prefixes three
times. Every move broke every hard-coded `href="/admin2/vehicles"`, and they
broke *silently*: a 404 on a link nobody clicked that week is a page that has
quietly stopped existing. `{% url %}` and `reverse()` follow the prefix; a
string does not.

Two rules:

1. **In templates**, an `href` or `action` must be `{% url ... %}`, a fragment
   (`#`), a full external URL, or a template variable. A literal that starts
   with `/` is a hand-written path.
2. **In python**, no string literal starts with the console prefix. `reverse()`
   and `redirect("console:home")` take names, and a `"/console/..."` literal is
   the same bug written in a different language.

`settings/base.py` is exempt: it is where `APP_BASE` is defined. Test
directories are skipped — a test asserting that a response redirects to a known
path is checking the router, not routing around it.

Run:  python ops/checks/console_urls_are_named.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ بعد
# ثالث مرة — وهذا أسوأ من حارسٍ لا يعمل، لأنه يُطفأ عن قناعة.
#
# و`hasattr` ليست حذراً زائداً: `tests/test_no_float_check.py` يستورد هذا
# الملف، وpytest يكون قد استبدل `sys.stdout` بكائن التقاطٍ بلا `reconfigure`.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
TEMPLATES = BACKEND / "templates"

SKIP_PARTS = {"__pycache__", "migrations", "tests", ".venv", "node_modules"}

#: The file that is allowed to know what the prefix is.
SETTINGS = BACKEND / "config" / "settings" / "base.py"

#: `href="..."` / `action="..."`, capturing what is inside the quotes.
LINK = re.compile(r"""\b(?:href|action)\s*=\s*["']([^"']*)["']""")

#: Anything a link may legitimately be: a tag, a fragment, an external URL, a
#: variable, a mailto/tel. Everything else that starts with `/` is a path.
ALLOWED_LINK = re.compile(r"""^(\{%|\{\{|#|https?://|mailto:|tel:|$)""")

#: A console **path**, which is what this rule is about — not every string that
#: happens to contain the word.
#:
#: The leading slash is required, and that is the whole distinction: `"console"`
#: is an app label, `"console/home.html"` is a template, `"console:home"` is a
#: url name — and all three are correct. `"/console/vehicles"` is a link somebody
#: typed, and it is the only one that breaks when `APP_BASE` changes.
CONSOLE_PATH = re.compile(r"^/(console|admin|admin2|admin3|admin_v2)(/|$)")


def template_violations(root: Path | None = None) -> list[str]:
    root = TEMPLATES if root is None else root
    found: list[str] = []
    if not root.exists():
        return found

    for path in sorted(root.rglob("*.html")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for target in LINK.findall(line):
                if ALLOWED_LINK.match(target.strip()):
                    continue
                found.append(
                    f"{path}:{number}: رابط مكتوب بيده «{target}» — استعمل {{% url %}}"
                )

    return found


class PathHunter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and CONSOLE_PATH.match(node.value):
            self.hits.append(
                (node.lineno, f"مسار لوحة مكتوب بيده «{node.value}» — استعمل reverse")
            )
        self.generic_visit(node)


def python_violations(roots: list[Path] | None = None) -> list[str]:
    roots = [BACKEND / "apps", BACKEND / "config"] if roots is None else roots
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in paths:
            if SKIP_PARTS & set(path.parts) or path == SETTINGS:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            hunter = PathHunter()
            hunter.visit(tree)
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def violations(*, templates: Path | None = None, python: list[Path] | None = None):
    return template_violations(templates) + python_violations(python)


def main() -> int:
    found = violations()
    if found:
        print("كل رابط في اللوحة يُشتقّ من اسمه لا يُكتب بيده:\n")
        for item in found:
            print(f"  {item}")
        print(
            f"\n{len(found)} مخالفة. لوحات v1 انتقلت بين بادئات ثلاث مرات، "
            "وكل رابط مكتوب بيده انكسر بصمت في كل مرة."
        )
        return 1

    print("لا رابط لوحة مكتوب بيده.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
