#!/usr/bin/env python
"""Fail if a file field picks its own storage path, or if anything but
`apps/core/uploads.py` decodes an uploaded image. T912.

Two rules, and both are about the same v1 incident — a webshell that lived for
months in the photographs directory:

1. **No `upload_to` string.** Django appends the uploader's own file name to a
   path template, so `upload_to="vehicles/%Y/%m/"` stores whatever they called
   it: `car.png.php`, `../../public/shell.php`, `x.png\\x00.php`. A callable
   from `apps.core.uploads` mints the whole name and never reads theirs. The
   difference is not a style preference; it is the traversal.

2. **One decoder.** `PIL` is a parser pointed at hostile bytes, and the checks
   that make it safe — format allowlist, dimensions read before the decode,
   re-encoding so a polyglot loses its payload — are worth writing once. A
   second `Image.open` somewhere else is a second set of them somebody has to
   remember, which is how the first one stopped being enough in v1.

Run:  python ops/checks/one_upload_gate.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
UPLOADS = BACKEND / "apps" / "core" / "uploads.py"

#: `apps/auctions/images.py` builds the thumbnail, and it reads a file this
#: project encoded a moment earlier rather than anything an uploader sent. It
#: is listed here — by name, with that reason — rather than left to a pattern,
#: so adding a second exemption is a deliberate edit somebody reviews.
IMAGE_DECODER_EXEMPT = {UPLOADS, BACKEND / "apps" / "auctions" / "images.py"}

# Tests are exempt from both rules: forging a hostile upload — a script named
# `.png`, a header declaring 40,000 pixels — is precisely what a test of this
# gate has to do.
SKIP_PARTS = {"__pycache__", "migrations", ".venv", "node_modules", "tests"}

FILE_FIELDS = {"FileField", "ImageField"}
IMAGE_MODULES = {"PIL"}


class UploadHunter(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.hits: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = _called_name(node.func)
        if name in FILE_FIELDS:
            self._check_upload_to(node)
        self.generic_visit(node)

    def _check_upload_to(self, node: ast.Call) -> None:
        for keyword in node.keywords:
            if keyword.arg != "upload_to":
                continue
            if isinstance(keyword.value, ast.Constant):
                self.hits.append(
                    (
                        node.lineno,
                        f"upload_to نصّي {keyword.value.value!r} — يبقي اسم الرافع",
                    )
                )
            return
        self.hits.append((node.lineno, "حقل ملف بلا upload_to من apps.core.uploads"))

    def visit_Import(self, node: ast.Import) -> None:
        if self.path not in IMAGE_DECODER_EXEMPT:
            for alias in node.names:
                if alias.name.split(".")[0] in IMAGE_MODULES:
                    self.hits.append((node.lineno, f"استيراد {alias.name}"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self.path not in IMAGE_DECODER_EXEMPT:
            root = (node.module or "").split(".")[0]
            if root in IMAGE_MODULES:
                self.hits.append((node.lineno, f"استيراد من {node.module}"))
        self.generic_visit(node)


def _called_name(func: ast.expr) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def violations(roots: list[Path]) -> list[str]:
    found: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts):
                continue
            hunter = UploadHunter(path)
            hunter.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")
    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config", BACKEND / "tests"])
    if found:
        print("مسار الرفع واحد — apps/core/uploads.py:\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة.")
        return 1

    print("بوابة رفع واحدة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
