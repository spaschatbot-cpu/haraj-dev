#!/usr/bin/env bash
# بناء إصدار للمتجرين (T717).
#
#   bash tool/build_release.sh android staging
#   bash tool/build_release.sh ios prod
#
# **لماذا سكربت لا سطر أوامر في وثيقة:** اسم البيئة يدخل البناء من مكانين —
# `--flavor` الذي يقرّر معرّف الحزمة واسمها ومفتاح Firebase، و`HARAJ_ENV` الذي
# يقرّر ما يراه التطبيق عن نفسه (اللافتة، وختم كل رسالة — المادة ٥-٦). كتابتهما
# بيد تجعل «حزمة تجريب تظنّ نفسها إنتاجاً» بُعد سهو واحد، وهي بالضبط الحالة التي
# أوصلت رسالة اختبار إلى عميل حقيقي في v1. هنا يُشتقّ الثاني من الأول.
#
# الأسرار كلها من البيئة، ولا شيء منها في المستودع (المادة ٥-٣):
#   HARAJ_API_BASE_URL      عنوان الخادم لهذه البيئة
#   HARAJ_KEYSTORE_PATH     مفتاح التوقيع (أندرويد، مطلوب لـprod)
#   HARAJ_KEYSTORE_PASSWORD · HARAJ_KEY_ALIAS · HARAJ_KEY_PASSWORD
#   BUILD_NUMBER            رقم البناء المتزايد؛ رقم الإصدار من pubspec.yaml

set -euo pipefail

cd "$(dirname "$0")/.."

platform=${1:-}
flavor=${2:-}

usage() {
  echo "الاستعمال: bash tool/build_release.sh <android|ios> <dev|staging|prod>" >&2
  exit 2
}

case "$platform" in android | ios) ;; *) usage ;; esac

# اسم البيئة داخل التطبيق مشتقّ من الـflavor لا مكتوباً بجواره.
case "$flavor" in
  dev) app_env=development ;;
  staging) app_env=staging ;;
  prod) app_env=production ;;
  *) usage ;;
esac

if [[ -z ${HARAJ_API_BASE_URL:-} ]]; then
  echo "HARAJ_API_BASE_URL غير مضبوط — لا عنوان افتراضي في بناء إصدار." >&2
  exit 2
fi

# رقم بناء ثابت 0 يجعل كل رفعة تصطدم بسابقتها في المتجر.
build_number=${BUILD_NUMBER:-}
if [[ -z $build_number ]]; then
  echo "BUILD_NUMBER غير مضبوط — رقم بناء متزايد شرط قبول المتجر." >&2
  exit 2
fi

defines=(
  --dart-define=HARAJ_ENV="$app_env"
  --dart-define=HARAJ_API_BASE_URL="$HARAJ_API_BASE_URL"
)

flutter pub get

if [[ $platform == android ]]; then
  # appbundle لا apk: المتجر يطلب AAB، والـAPK للاختبار اليدوي وحده.
  flutter build appbundle \
    --flavor "$flavor" \
    --build-number "$build_number" \
    "${defines[@]}"
else
  # التوقيع على iOS من Xcode/fastlane بشهادة الفريق، لا من هنا: مفتاح توقيع
  # يمرّ عبر سكربت في المستودع مفتاحٌ في المستودع بخطوة واحدة.
  flutter build ipa \
    --build-number "$build_number" \
    "${defines[@]}"
fi
