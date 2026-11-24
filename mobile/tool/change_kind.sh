#!/usr/bin/env bash
# أيُّ طريقٍ تسلكه دفعةٌ إلى main: ترقيعٌ داخليّ أم إصدارٌ جديد؟
#
#   bash mobile/tool/change_kind.sh <before-sha> <after-sha>
#   ⟵ يطبع سطرين لـ$GITHUB_OUTPUT:  patch=true|false  و release=true|false
#
# **لماذا** (المالك، ٢٤ نوفمبر ٢٠٢٦): «عايز التحديثات تنزل من جوّه على طول…
# مش لازم كل شوية أرفع update أو آخد نسخة جديدة أثبتها». فالدفعةُ التي تمسّ
# كودَ دارت وحده تصل الأجهزةَ ترقيعاً من Shorebird، والإصدارُ الكامل يبقى لما
# لا يحمله الترقيع: الأصليّ (android/ ios/) والمكتبات (pubspec).
#
# ويُقرأ من السيرين كليهما (mobile-release وmobile-patch) لأن خطأً في القسمة
# يُرسل الدفعةَ في الطريقين أو في لا طريق: ترقيعٌ فيه فرقٌ أصليٌّ يرفضه Shorebird،
# وإصدارٌ لكلّ تعديل نصٍّ يعيد المالكَ إلى التثبيت اليدويّ الذي اشتكى منه.
#
# **وبلا Shorebird** (لا SHOREBIRD_TOKEN أو لا shorebird.yaml) فكلُّ دفعةٍ
# إصدار — كما كان قبل هذا الملفّ — كي لا يتوقّف TestFlight على حسابٍ لم يُنشأ.

set -euo pipefail

before=${1:-}
after=${2:-HEAD}

shorebird=false
if [[ -n ${SHOREBIRD_TOKEN:-} && -f mobile/shorebird.yaml ]]; then
  shorebird=true
fi

# أوّلُ دفعةٍ لفرعٍ جديد يأتي before صفراً — فالمقارنةُ بالأب المباشر.
if [[ -z $before || $before =~ ^0+$ ]] || ! git cat-file -e "$before^{commit}" 2>/dev/null; then
  before="$after~1"
fi

changed=$(git diff --name-only "$before" "$after" -- mobile .github/workflows/mobile-release.yml)

native=$(grep -E '^mobile/(android|ios)/|^mobile/pubspec\.(yaml|lock)$|^\.github/workflows/mobile-release\.yml$' <<<"$changed" || true)
dart=$(grep -E '^mobile/(lib|assets)/' <<<"$changed" || true)

if [[ $shorebird != true ]]; then
  echo "patch=false"
  [[ -n $changed ]] && echo "release=true" || echo "release=false"
elif [[ -n $native ]]; then
  # فرقٌ أصليّ: إصدارٌ يحمل الدفعةَ كلَّها، والترقيعُ يُترك — Shorebird يرفضه.
  echo "patch=false"
  echo "release=true"
elif [[ -n $dart ]]; then
  echo "patch=true"
  echo "release=false"
else
  echo "patch=false"
  echo "release=false"
fi
