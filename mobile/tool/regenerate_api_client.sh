#!/usr/bin/env bash
# إعادة توليد عميل الـAPI من مخطط OpenAPI (T702).
#
# نفس السكربت يُشغَّل محلياً وفي CI. في CI يليه `git diff --exit-code`، فأي
# اختلاف بين المولَّد المرفوع والمولَّد من المخطط يُسقط البناء — وهذا هو معيار
# القبول: «تغيير في المخطط ينعكس بإعادة التوليد؛ وCI يفشل عند الاختلاف».
#
# الترتيب مهم: التوليد يكتب النماذج، ثم build_runner يكتب ملفات .g.dart،
# ثم dart format يوحّد الشكل — بلا الخطوة الثالثة يفشل فحص الفرق على تنسيق
# لا على محتوى.

set -euo pipefail

cd "$(dirname "$0")/.."

flutter pub get

# يُمحى المجلد قبل التوليد: swagger_parser يكتب ولا يحذف، فنموذجٌ حُذف من
# المخطط يبقى ملفاً يتيماً يُصرَّف ويُستورَد — ولا تلتقطه بوابة `git diff` في
# CI لأنه لم يتغيّر. المجلد كله مولَّد، فمحوه لا يفقد شيئاً.
rm -rf lib/data/api/generated

dart run swagger_parser
dart run build_runner build
dart format lib/data/api/generated
