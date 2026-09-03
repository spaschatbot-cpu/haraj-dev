/// أسباب رفض المزايدة **كما يعدّدها الخادم**، ومعها جملته لكلٍّ منها.
///
/// مصدرها الوحيد `backend/apps/bidding/models.py::RefusalReason`، والجُمل من
/// `backend/apps/bidding/eligibility.py` حيث تُكتب فعلاً. لا يُضاف هنا رمز من
/// عندنا: قائمةٌ نكتبها نحن تمرّ في كل اختبار نكتبه نحن، وتفترق عن الخادم
/// بصمت — وهو بالضبط ما حدث حين حملت هذه القائمة أربعة رموز مخترَعة
/// (`insufficient_deposit`، `auction_not_open`، `account_suspended`،
/// `bid_below_minimum`) وغابت عنها خمسة حقيقية.
///
/// يحرسها `test/architecture/refusal_codes_match_the_server_test.dart`: يقرأ
/// التعداد من ملف الخلفية ويفشل عند أول فرق في الاتجاهين.
///
/// الجُمل هنا ليست تعريفاً لشيء — لا شيء في التطبيق يقرؤها. وجودها ليقول
/// الاختبار «ما وصل من الخادم هو ما ظهر»، أياً كان.
const Map<String, String> serverRefusalReasons = <String, String>{
  'auction_ended': 'انتهى وقت هذا المزاد.',
  'auction_not_live': 'المزاد غير مفتوح للمزايدة الآن.',
  'vehicle_not_biddable': 'المركبة «مُباعة» ولا تقبل مزايدة.',
  'own_vehicle': 'لا يمكنك المزايدة على مركبتك.',
  'phone_not_verified': 'لازم توثّق رقم جوالك قبل المزايدة.',
  'profile_incomplete': 'ملفك ناقص: رقم الهوية مطلوب للمزايدة.',
  'below_floor': 'أقل مزايدة مقبولة 500.00 ريال.',
  'unpaid_dues': 'عليك مستحقات غير مسدَّدة قدرها 1200.00 ريال.',
  'no_deposit':
      'تحتاج تأميناً متاحاً قدره 10000.00 ريال للمزايدة في هذا المزاد، '
      'والمتاح لديك 0.00 ريال.',
};

/// رمز الخفض. ليس سبب رفض من `RefusalReason` — يكتبه
/// `backend/apps/bidding/services.py` — فهو مستثنى من المقارنة صراحةً ومغطّى
/// باختباراته الخاصة (حوار تأكيد الخفض، F3).
const String lowerNeedsConfirmCode = 'lower_needs_confirm';
