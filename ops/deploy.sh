#!/usr/bin/env bash
# نشرٌ تلقائيّ: يسحب `main` إن تغيّر، ثم يُحدّث ويُعيد التشغيل.
#
# يُشغَّل من `haraj-deploy.timer` كلَّ دقيقتين على خادم `haraj.spas.sa`،
# ووحداتُه بجانبه في `ops/systemd/`.
#
# **ولماذا صار في المستودع (١٧ سبتمبر ٢٠٢٦):** كان ملفّاً على الخادم وحده
# (`/srv/haraj/ops-deploy.sh`) لا يراه أحدٌ في مراجعةٍ ولا يحفظه الجيت —
# وفيه سطرٌ واحدٌ أسقط الموقعَ يوماً كاملاً بلا أن يعرف أحدٌ أين يبحث
# (انظر `npm ci` أدناه). فما يُشغّل الإنتاج يُقرأ كما تُقرأ الشيفرة.
#
# لماذا سحبٌ بالسؤال لا خطّافُ ويب: الخطّاف يحتاج المفتاحَ الخاصّ في أسرار
# GitHub، وهو مفتاحُ الإنتاج نفسُه. والسؤالُ يبقي المفتاحَ على السيرفر وحده،
# وثمنُه تأخيرُ دقيقتين — وهو ثمنٌ مقبولٌ للوحةٍ داخليّة.
#
# والقفل (`flock`) في الوحدة لا هنا: دورتان متداخلتان تعنيان `git pull`
# أثناء `collectstatic`، أي ملفّاتٍ نصفُها من نسخةٍ ونصفُها من أخرى.
set -euo pipefail

# ---------------------------------------------------------------------------
# يَنسخ نفسَه ويُكمل من النسخة — **لازمٌ منذ صار الملفُّ داخل المستودع**.
# ---------------------------------------------------------------------------
# `bash` يقرأ السكربت على دفعاتٍ بإزاحةٍ في الملفّ، لا مرّةً واحدةً إلى
# الذاكرة. و`git merge --ff-only` أسفلَ هذا السطر يُعيد كتابة **هذا الملفّ
# نفسِه** إن حمل الالتزامُ تعديلاً عليه — فيُكمل `bash` القراءةَ من إزاحةٍ
# صارت تشير إلى نصٍّ آخر: نصفُ أمرٍ من نسخةٍ ونصفُه من أخرى.
#
# والنسخةُ تحذف نفسَها أوّلَ ما تبدأ: على لينكس يبقى الملفُّ المفتوحُ صالحاً
# بعد حذف اسمه، فلا يتراكم شيءٌ في `/tmp` ولو قُتل النشرُ في منتصفه.
if [ "${HARAJ_DEPLOY_COPY:-}" != "1" ]; then
  copy=$(mktemp /tmp/haraj-deploy.XXXXXX.sh)
  cat "$0" >"$copy"
  chmod +x "$copy"
  HARAJ_DEPLOY_COPY=1 exec bash "$copy" "$@"
fi
rm -f "$0"

cd /srv/haraj

git fetch --quiet origin main
local_sha=$(git rev-parse HEAD)
remote_sha=$(git rev-parse origin/main)
[ "$local_sha" = "$remote_sha" ] && exit 0

echo "نشر: $local_sha -> $remote_sha"
git merge --ff-only origin/main

cd /srv/haraj/backend
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart haraj-backend

# الموقعُ يُعاد بناؤه فقط إن مسّه التغيير — بناءُ Next.js دقائقُ لا ثوانٍ.
if git -C /srv/haraj diff --name-only "$local_sha" "$remote_sha" | grep -q '^web/'; then
  # ‏`npm ci` كاملاً لا `--omit=dev`: أدواتُ البناء كلُّها في
  # `devDependencies` — و`@tailwindcss/postcss` منها، تقرؤها `globals.css`
  # في كل بناء. وكان `--omit=dev` يثبّت ٤٥ حزمةً من ٤٩٢ فيسقط `next build`
  # بـ«Cannot find module»، ويترك `.next` نصفَ مكتوبٍ فيدور `haraj-web` على
  # «Could not find a production build» إلى الأبد. وقع في ١٦ سبتمبر ٢٠٢٦
  # وبقي الموقعُ ٥٠٢ حتى اليوم التالي — ٣٬٨٤٤ محاولةَ إقلاع.
  #
  # و`rm -rf .next` قبله: البناءُ الساقطُ يترك كاشَ Turbopack يُعيد الخطأ
  # نفسَه حتى بعد تصحيح الحزم — قِيس، فسقط البناءُ مرّتين بعد تثبيتٍ سليم.
  cd /srv/haraj/web && npm ci && rm -rf .next && npm run build
  sudo systemctl restart haraj-web
fi

echo "تمّ: $(git -C /srv/haraj rev-parse --short HEAD)"
