#!/usr/bin/env bash
# يسحب صور vehicle_images من v1 — **قراءةٌ فقط** (select تبثّ إلى المخرج).
# $1: شرطُ المركبات، مثل: av.auction_id=1030
set -euo pipefail
WHERE="$1"
QUERY="select vi.id, vi.vehicle_id, vi.sort_order, vi.is_primary, coalesce(vi.image_mime,''), replace(to_base64(vi.image_blob), char(10), '') from vehicle_images vi join auction_vehicles av on av.id=vi.vehicle_id where ${WHERE} and vi.image_blob is not null"
ssh -o BatchMode=yes -o ServerAliveInterval=30 hara@148.72.244.103 \
  "mysql -N -B --quick hara_clone_v1 -e \"${QUERY}\"" \
  | python3 /home/ubuntu/v1dump/blob_sink.py
