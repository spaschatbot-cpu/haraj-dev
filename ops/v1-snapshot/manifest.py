"""car_images ⟶ {معرّف auction_vehicles: [ملفّات بالترتيب]} — من نسخة v1 لا من خادمها.

details.id = details.car_id = auction_vehicles.id في كلّ الصفوف (قِيس ٢٤ نوفمبر:
صفرُ اختلافٍ في ٨٬٨٠١)، فـcar_images.id_details هو معرّفُ المركبة مباشرةً.
ويكتب أيضاً قائمةَ أسماء ملفّات مركبات المزادات القادمة لتُجلب أوّلاً.
"""

import json
from collections import defaultdict

from apps.migration.dumpfile import read_table

from pathlib import Path
DUMP = Path("/home/ubuntu/v1dump/v1_20261124.sql.gz")

images = defaultdict(list)
for row in sorted(read_table(DUMP, "car_images"), key=lambda r: int(r["id"])):
    images[int(row["id_details"])].append(row["image"])

upcoming = {
    str(row["id"]) for row in read_table(DUMP, "auctions")
    if str(row.get("status")) in {"soon", "upcoming"}
}
first = [
    int(row["id"]) for row in read_table(DUMP, "auction_vehicles")
    if str(row.get("auction_id")) in upcoming
]

with open("/home/ubuntu/v1dump/manifest.json", "w", encoding="utf-8") as out:
    json.dump(images, out)
names = [n for vid in first for n in images.get(vid, [])]
with open("/home/ubuntu/v1dump/first_files.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(names) + "\n")
print("vehicles with images", len(images), "files", sum(map(len, images.values())))
print("upcoming auctions", sorted(upcoming), "vehicles", len(first), "files", len(names))
