"""خلفيّةُ مصادقةٍ للموظّفين: اسمُ دخولٍ وكلمةُ مرور، لا رقمُ جوّال. T918

قرارُ المالك بالحرف: «عايز تسجيل دخول الادمن يكون بيوزر و باس، مش بالرقم.
الرقم و الـOTP دا للمستخدمين». وسُئل عن عاملٍ ثانٍ فقال: لا.

**ولماذا خلفيّةٌ ولم يتغيّر `USERNAME_FIELD`.** تغييرُه من `phone` إلى
`username` يمسّ `createsuperuser` وكلَّ هجرةٍ قائمةٍ ومسارَ دخول العميل، وثمنُه
أكبرُ من مكسبه: المطلوب **من يُصادَق وبماذا**، وذلك ما تقرّره الخلفيّة. فيبقى
`phone` حقلَ الهويّة للنموذج، ويصير `username` بابَ اللوحة.

**ولماذا `ModelBackend` أباً لا صفٌّ من الصفر.** `ModelBackend` ليس
`authenticate` وحدها: فيه آلةُ الصلاحيات كلُّها — `has_perm` و`has_module_perms`
و`get_user_permissions` و`get_group_permissions` — ولوحةُ جانغو تسألها في كلّ
شاشة. وخلفيّةٌ بلا تلك الآلة تفتح الدخول ثم تُفرغ الصلاحيات، فتُقرأ «اللوحة
تعمل والشاشات فارغة» — عطلٌ لا يظهر في شاشة الدخول التي غُيّرت.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class StaffUsernameBackend(ModelBackend):
    """يُصادِق موظّفاً باسم دخولٍ وكلمةِ مرور. ولا يُصادِق عميلاً أبداً."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()

        # ‏`AuthenticationForm` ترسل الحقل باسم `username`، وناداةٌ أخرى قد
        # ترسله باسم حقل الهويّة (`phone`) لأن ذلك ما تفعله خلفيّةُ جانغو.
        # ولا يُقرأ `phone` هنا: من نادى بالجوّال يريد الجوّال، وابتلاعُه
        # هنا يُعيد البابَ الذي أُغلق.
        raw = username if username is not None else kwargs.get("username")
        name = str(raw or "").strip().lower()

        # ‏**الحارس الأول: الاسمُ الفارغ لا يُصادِق.** لو مرّ `username=""`
        # إلى الاستعلام لطابق كلَّ عميلٍ في القاعدة — ٤٦ ألفاً في `haraj2_t307`
        # — وأوّلُهم يصلح جواباً. فالردُّ قبل أيّ استعلام لا بعده.
        if not name or not password:
            # تجزئةٌ وهميّة هنا أيضاً: لولاها لكان الطلبُ الفارغ يعود أسرعَ
            # من غيره بفارقٍ يُقاس، فيُعرف من الزمن أنّ الرفض كان قبل القاعدة.
            User().set_password(password)
            return None

        try:
            # ‏**الحارس الثالث: `is_staff` في الاستعلام لا بعده.** لو صار
            # شرطاً يُفحص على الصفّ المُعاد، لكان عميلٌ ملأ أحدٌ له هذا الحقل
            # يوماً **قابلاً للمصادقة** ثم يُرفض — وبينهما نافذةٌ كاملةٌ
            # يعتمد فيها كلُّ من ينسى الفحص.
            person = User._default_manager.get(username=name, is_staff=True)
        except User.DoesNotExist:
            # ‏**الحارس الثاني: تجزئةٌ وهميّة.** هذا ما يفعله `ModelBackend`
            # حرفياً، وسببُه أن التجزئة أبطأُ ما في المسار: بدونها يُرَدّ
            # الاسمُ غيرُ الموجود في جزءٍ من مللي ثانية والموجودُ في مئاتها،
            # فيُعرَف من الزمن **أيُّ الأسماء موجود** وإن كانت الرسالة واحدة.
            User().set_password(password)
            return None

        # و`user_can_authenticate` لا تُستبدل بـ`is_active` مكتوبةً هنا:
        # الحسابُ المعطَّل بديلُ الحذف في هذه اللوحة (لا زرَّ حذفٍ للمشرفين
        # لأن حسابَ الموظّف طرفٌ في كلّ قيدٍ كتبه)، فبابُه يجب أن يُقفل في
        # الموضع الذي تقرأه جانغو نفسها.
        if person.check_password(password) and self.user_can_authenticate(person):
            return person
        return None


__all__ = ["StaffUsernameBackend"]
