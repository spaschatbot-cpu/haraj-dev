import '../../common/money.dart';

/// ما يصير عليه مبلغُ المزايدة بعد الضريبة — **كما يحسبه الخادم**.
///
/// ولماذا يُسأل الخادم ولا يُضرب الرقمُ هنا: نسبةُ الضريبة قاعدةٌ واحدة تعيش
/// في `apps/money`، وكلُّ حسابٍ لها في التطبيق نسخةٌ ثانية تفترق عنها في أوّل
/// يومٍ تتغيّر فيه — وحينها يرى العميلُ رقماً ويُفوتَر بغيره.
final class BidQuote {
  const BidQuote({
    required this.amount,
    required this.tax,
    required this.total,
  });

  /// المبلغ كما أرسله العميل، مُطبَّعاً كما يخزّنه الدفتر.
  final Money amount;

  final Money tax;

  final Money total;
}
