import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'cache_database.g.dart';

/// آخر استجابة معروفة لكل مفتاح شاشة.
///
/// **ما لا يوضع هنا:** رمز وصول أو تحديث. الرموز في التخزين الآمن وحده
/// (`SecureTokenStore`) — قاعدة SQLite تُقرأ من نسخة احتياطية للجهاز.
@DataClassName('CachedDocumentRow')
class CachedDocuments extends Table {
  TextColumn get key => text()();

  /// جسم الاستجابة كما وصل، نصّاً — لا نموذج مفكوك: الكاش لا يعرف الشكل، فلا
  /// يحتاج ترحيلاً كلما تغيّر المخطط.
  TextColumn get payload => text()();

  /// عدد الميلي ثانية منذ Epoch **بتوقيت UTC**.
  ///
  /// عدد صريح لا `DateTime`: عمود التاريخ في drift يُقرأ بتوقيت الجهاز
  /// افتراضياً، والمادة ٣-١ تمنع مقارنة عمودين أحدهما محوَّل والآخر لا.
  IntColumn get fetchedAtUtcMillis => integer()();

  @override
  Set<Column> get primaryKey => {key};
}

@DriftDatabase(tables: [CachedDocuments])
class CacheDatabase extends _$CacheDatabase {
  CacheDatabase(super.executor);

  /// قاعدة الجهاز الحقيقية.
  ///
  /// **`web` ليست منصّة شحن** — المنصّتان أندرويد وiOS (المعيار H1). وهي
  /// مضبوطة هنا لأن `driftDatabase` يرمي عند الترجمة للويب بلا هذا المعامل،
  /// فتسقط الشاشة الأولى قبل أن تُرسم — وتشغيلُ التطبيق في متصفّح هو أرخص
  /// طريقة لمعاينة الشاشات على جهازٍ بلا محاكٍ أندرويد.
  ///
  /// الملفّان في `web/` ويُنزَّلان مع إصدار drift، ولا أثر لهما على حزمتَي
  /// المتجرين: `driftDatabase` يتجاهل `web` تماماً خارج الويب.
  CacheDatabase.onDevice()
    : super(
        driftDatabase(
          name: 'haraj_cache',
          web: DriftWebOptions(
            sqlite3Wasm: Uri.parse('sqlite3.wasm'),
            driftWorker: Uri.parse('drift_worker.js'),
          ),
        ),
      );

  @override
  int get schemaVersion => 1;
}
