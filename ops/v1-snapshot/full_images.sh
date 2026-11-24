#!/usr/bin/env bash
# بقيّةُ صور v1 كلُّها إلى خادم التيست، ثم إلصاقُها. v1 يُقرأ فقط.
set -uo pipefail
D=/home/ubuntu/v1dump
UP=/home/ubuntu/v1_uploads
V1=hara@148.72.244.103
V1_UPLOADS=/home/hara/public_html/application/admin/includes/add_imags/uploads
cd /srv/haraj/backend

echo "=== $(date +%T) صور vehicle_images لبقيّة المركبات"
$D/pull_blobs.sh "av.auction_id<>1030"
du -sh /home/ubuntu/v1_blobs

echo "=== $(date +%T) ملفّات car_images الناقصة"
.venv/bin/python - <<'EOF'
import json, os
have = set(os.listdir("/home/ubuntu/v1_uploads"))
partial = open("/home/ubuntu/v1dump/last_partial.txt").read().strip()
have.discard(partial)
names = sorted({n for v in json.load(open("/home/ubuntu/v1dump/manifest.json")).values() for n in v} - have)
open("/home/ubuntu/v1dump/missing_files.txt", "w").write("\n".join(names) + "\n")
print("missing", len(names))
EOF
ssh -o BatchMode=yes -o ServerAliveInterval=30 $V1 "tar -cf - --ignore-failed-read -C $V1_UPLOADS -T -" \
  < $D/missing_files.txt | tar -xf - -C $UP
ls $UP | wc -l; du -sh $UP

echo "=== $(date +%T) إلصاق صور vehicle_images"
.venv/bin/python manage.py import_v1_images --manifest /home/ubuntu/v1_blobs/manifest.json \
  --source-dir /home/ubuntu/v1_blobs --vehicles 100000 --per-vehicle 30 | tail -3
echo "=== $(date +%T) إلصاق صور car_images (ما لا صورةَ له بعد)"
.venv/bin/python manage.py import_v1_images --manifest $D/manifest.json \
  --source-dir $UP --vehicles 100000 --per-vehicle 30 | tail -3
echo "=== $(date +%T) تمّ"
