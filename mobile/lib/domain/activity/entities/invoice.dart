import '../../common/money.dart';

/// حالة الفاتورة **كما اشتقّها الخادم**.
///
/// ⚠️ لا تُستنتج في التطبيق من `total` و`paid`. في v1 كان عمود الحالة يُكتب
/// مرة واحدة عند الإدراج، فتقرأ كل فاتورة «مسودّة» إلى الأبد، وكل شاشة تفرّعت
/// عليه كانت تفرّع على قيمة مجمّدة. والدرس ليس «اشتقّها في الشاشة» بل
/// «اشتقّها في مكان واحد» — وهو الخادم (`derive_invoice_state`).
enum InvoiceState { open, partiallyPaid, paid, cancelled, unknown }

/// ما تعنيه فاتورة غير مسدَّدة لتأمين صاحبها.
///
/// النصّ من الخادم لا من التطبيق: من كتب القاعدة يكتب شرحها، وصياغة ثانية
/// عندنا تنحرف عنها فيسمع العميل جوابين لحالة واحدة.
final class InsuranceLock {
  const InsuranceLock({required this.money, required this.note});

  final Money money;

  /// شرح عربي جاهز للعرض — يُعرض حرفياً.
  final String note;
}

/// فاتورة العميل: المبلغ والمسدَّد والمتبقّي، وكلها تصل محسوبة.
final class Invoice {
  const Invoice({
    required this.id,
    required this.number,
    required this.total,
    required this.paid,
    required this.due,
    required this.state,
    required this.stateLabel,
    required this.issuedAt,
    this.insuranceLock,
  });

  final String id;
  final String number;

  final Money total;
  final Money paid;

  /// المتبقّي **كما وصل**. لا يُطرح هنا: الطرح في الشاشة رقم بلا قيد يقابله
  /// (المادة ١-٦)، ويفترق عن الفاتورة نفسها عند أول دفعة جزئية.
  final Money due;

  final InvoiceState state;

  /// وصف الحالة بالعربية من الخادم.
  final String stateLabel;

  /// بتوقيت UTC.
  final DateTime issuedAt;

  /// أثر هذه الفاتورة على التأمين، إن كان لها أثر.
  final InsuranceLock? insuranceLock;
}
