import '../../common/snapshot.dart';
import '../entities/invoice.dart';
import '../entities/participation.dart';
import '../entities/purchase.dart';

/// عقد «ما يخصّني»: مشاركاتي ومشترياتي وفواتيري.
///
/// **لماذا عقد واحد لثلاث قوائم:** الثلاث إجابات على سؤال واحد يسأله العميل —
/// «وين فلوسي، وإيش اللي عليّ؟» — والفاتورة غير المسدَّدة هي بعينها سببُ القفل
/// الذي تعرضه المشاركة. فصلها إلى ثلاثة عقود يجعل ما هو مترابط في ذهن العميل
/// مبعثراً في الشيفرة، بلا مقابل.
///
/// كل دالة ترجع `Snapshot` لا قائمة مجرَّدة: العرض يحتاج أن يعرف إن كانت هذه
/// آخر نسخة من الخادم أم نسخة محفوظة ومتى جُلبت — وإلا تعذّر تنفيذ H5 بصدق.
abstract interface class ActivityRepository {
  /// المزادات التي دخلها العميل وحالة تأمينه في كل واحد.
  Future<Snapshot<List<Participation>>> loadParticipations();

  /// ما رسا عليه، ومعه فاتورته إن صدرت.
  Future<Snapshot<List<Purchase>>> loadPurchases();

  /// فواتيره بحالتها المشتقّة من الخادم.
  Future<Snapshot<List<Invoice>>> loadInvoices();
}
