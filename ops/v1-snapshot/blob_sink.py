"""يقرأ صفوفَ vehicle_images من المدخل (id, vehicle_id, sort, primary, mime, base64)
ويكتب كلَّ صورةٍ ملفّاً، ثم مانيفستاً بالترتيب: الأساسيّةُ أوّلاً ثم sort_order."""

import base64
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/ubuntu/v1_blobs")
ROOT.mkdir(exist_ok=True)
rows = defaultdict(list)
count = 0
for line in sys.stdin.buffer:
    parts = line.rstrip(b"\n").split(b"\t")
    if len(parts) != 6:
        continue
    pk, vid, order, primary, mime, data = parts
    ext = "png" if b"png" in mime else "jpg"
    name = f"{int(vid)}/{int(pk)}.{ext}"
    target = ROOT / name
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(base64.b64decode(data))
    rows[int(vid)].append((-int(primary), int(order), int(pk), name))
    count += 1

manifest_path = ROOT / "manifest.json"
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
for vid, items in rows.items():
    manifest[str(vid)] = [name for *_, name in sorted(items)]
manifest_path.write_text(json.dumps(manifest))
print("images", count, "vehicles", len(rows))
