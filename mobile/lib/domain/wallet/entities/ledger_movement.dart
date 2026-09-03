import '../../common/money.dart';
import 'wallet_balance.dart';

/// اتجاه الحركة **كما قاله الخادم**.
///
/// ليست `debit`/`credit`: معناهما يتبع جهة الحساب، فترجمتهما إلى «دخل» أو
/// «خرج» في الشاشة اجتهاد في اصطلاح محاسبي يسكن في `apps/money/models` وحده،
/// ولو اختلف اجتهادنا عن اجتهاد الويب لظهرت الحركة نفسها بإشارتين.
///
/// `unknown` مقصودة (المادة ٢-٣ و٣-٥): قيمة لم نرها لا تُسقط الكشف كله.
enum LedgerDirection { incoming, outgoing, unknown }

/// سطر واحد من كشف الحركات — قيدٌ في الدفتر لا ملخّص بجانبه.
final class LedgerMovement {
  const LedgerMovement({
    required this.id,
    required this.description,
    required this.bucketLabel,
    required this.money,
    required this.direction,
    required this.occurredAt,
    this.bucket,
    this.reference,
  });

  final String id;

  /// ماذا حدث، بالعربية، من الخادم. لا مفتاح إنجليزي يُترجَم هنا.
  final String description;

  /// أي دلو تحرّك — الاسم بالعربية من الخادم.
  final String bucketLabel;

  /// الدلو نفسه، حين يعرفه هذا الإصدار من التطبيق.
  final WalletBucketKind? bucket;

  final Money money;
  final LedgerDirection direction;

  /// بتوقيت UTC — التحويل للعرض عند حافة العرض وحدها (المادة ٣-١).
  final DateTime occurredAt;

  /// المزاد أو الفاتورة التي تخصّها الحركة، إن كانت تخصّ شيئاً.
  final String? reference;
}

/// صفحة واحدة من الكشف.
///
/// `hasMore` من الخادم (`next`) لا من مقارنة عدد الصفوف بحجم الصفحة: الحساب
/// الثاني تخمين، ويخطئ في آخر صفحة ممتلئة تماماً فيُظهر «المزيد» ثم لا شيء.
final class LedgerPage {
  const LedgerPage({
    required this.movements,
    required this.hasMore,
    required this.page,
    required this.total,
  });

  final List<LedgerMovement> movements;
  final bool hasMore;

  /// رقم الصفحة التي جاءت منها هذه الحركات.
  final int page;

  /// عدد الحركات كلها كما قاله الخادم — عدد لا مبلغ.
  final int total;
}
