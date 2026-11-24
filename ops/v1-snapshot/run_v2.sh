#!/usr/bin/env bash
# بناء قاعدة haraj2_v2 من نسخة v1 (٢٤ نوفمبر ٢٠٢٦) بجانب haraj2_v1 — لا محو.
set -euo pipefail
cd /srv/haraj/backend
DUMP=/home/ubuntu/v1dump/v1_20261124.sql.gz
PY=.venv/bin/python
OLD_URL=$(grep -E '^DATABASE_URL=' .env | cut -d= -f2-)
NEW_URL=$(printf '%s' "$OLD_URL" | sed -E 's#/haraj2_v1$#/haraj2_v2#')
[ "$NEW_URL" != "$OLD_URL" ] || { echo "تعذّر اشتقاق رابط القاعدة الجديدة"; exit 1; }

step() { echo; echo "=== $(date +%T) $*"; }

step "تصدير حسابات الموظّفين من haraj2_v1"
$PY manage.py shell -c "exec(open('/home/ubuntu/v1dump/staff_export.py').read())"

step "إنشاء haraj2_v2"
sudo -n -u postgres createdb -O haraj haraj2_v2

export DATABASE_URL="$NEW_URL"
step "الهجرات"
$PY manage.py migrate --noinput | tail -3
step "migrate_v1"
$PY manage.py migrate_v1 --dump "$DUMP"
step "backfill_v1_fields"
$PY manage.py backfill_v1_fields --path "$DUMP"
step "backfill_awards"
$PY manage.py backfill_awards --dump "$DUMP"
step "build_refund_requests"
$PY manage.py build_refund_requests --dump "$DUMP"
step "الموظّفون"
$PY manage.py shell -c "exec(open('/home/ubuntu/v1dump/staff_import.py').read())"
step "verify_ledger"
$PY manage.py verify_ledger || true
step "تمّ"
