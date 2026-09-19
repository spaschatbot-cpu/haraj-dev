import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../bidding/bidding_controllers.dart';
import '../catalog/widgets/vehicle_card.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';

/// تبويبات شاشة «مشاركاتي». الاسم النصّي هو ما يصل في رابط الإشعار.
///
/// **بقي التعداد وسقط التبويبان.** «مشترياتي» و«فواتيري» رُفعا من الشاشة بطلب
/// المالك في ٩ سبتمبر ٢٠٢٦، والتعدادُ باقٍ لأن `?tab=` في العنوان يقرؤه
/// الإشعارُ والرابطُ المشارَك (معيار H6): رابطُ فاتورةٍ أُرسل قبل اليوم يجب
/// أن يفتح شيئاً، لا أن يهبط على «مسار غير موجود».
enum MyActivityTab {
  participations('participations'),
  purchases('purchases'),
  invoices('invoices');

  const MyActivityTab(this.slug);

  final String slug;

  /// اسم غير معروف (أو غائب) يفتح التبويب الأول ولا يُسقط الشاشة: إشعار من
  /// نسخة خادم أحدث يجب أن يفتح شيئاً، لا أن يعرض عطباً.
  static MyActivityTab fromSlug(String? slug) => values.firstWhere(
    (tab) => tab.slug == slug,
    orElse: () => MyActivityTab.participations,
  );
}

/// مشاركاتي — **المركبات التي زايدتُ عليها، بكرت التصفّح نفسه**.
///
/// كانت ثلاثة تبويبات (مشاركاتي · مشترياتي · فواتيري) وكرتَ مشاركةٍ خاصّاً بها
/// يعرض المزادَ والتأمين. ورُفع الاثنان بطلب المالك في ٩ سبتمبر ٢٠٢٦: السؤال
/// الذي يفتح به العميلُ هذا القسم هو «أي سيّارةٍ زايدتُ عليها؟»، وجوابُه
/// السيّارةُ نفسُها — لا سطرٌ عن المزاد الذي تقف فيه.
///
/// **ونفس `VehicleCard` لا كرتٌ ثانٍ** (المادة ٤-٥): مركبةٌ زايدتُ عليها ليست
/// نوعاً آخر من المركبات، وكرتٌ خاصٌّ بها يعني حقلاً يُضاف في أحدهما ويُنسى في
/// الآخر — وهو بعينه ما كان في v1.
///
/// **والمصدرُ `myBidsProvider` لا `myParticipationsProvider`:** المشاركةُ في
/// عقد الخادم صفٌّ عن **مزاد** (تأمينٌ وعددُ مزايدات)، والمزايدةُ صفٌّ عن
/// **مركبة**. والسؤال هنا عن المركبات.
class MyActivityScreen extends ConsumerWidget {
  const MyActivityScreen({
    this.initialTab = MyActivityTab.participations,
    super.key,
  });

  /// يصل من `?tab=` ولا يُقرأ بعد أن سقطت التبويبات — باقٍ لأن حذفه يكسر
  /// جدولَ المسارات والروابطَ المرسَلة.
  final MyActivityTab initialTab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bids = ref.watch(myBidsProvider);

    return Scaffold(
      // **لا `appBar` هنا**: شريطُ العنوان يعيش **داخل القائمة** فينزلق
      // معها، بطلب المالك في ٩ سبتمبر ٢٠٢٦. الثابتُ فوقه هيدرُ العلامة في
      // القشرة، وشريطان ثابتان فوق قائمةٍ يأكلان من الشاشة القصيرة كرتاً.
      body: switch (bids) {
        AsyncData(value: final Snapshot<List<PlacedBid>> snapshot) =>
          RefreshIndicator(
            onRefresh: () async => ref.refresh(myBidsProvider.future),
            child: _BidVehicles(bids: snapshot.value),
          ),
        AsyncError(:final error, :final stackTrace) => Center(
          child: FailureView(
            failure: error is Failure
                ? error
                : UnexpectedFailure(error, stackTrace: stackTrace),
            onRetry: () => ref.invalidate(myBidsProvider),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _BidVehicles extends StatelessWidget {
  const _BidVehicles({required this.bids});

  final List<PlacedBid> bids;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    // **مركبةٌ واحدة لكل مركبة، لا كرتٌ لكل مزايدة**: من زايد ثلاثَ مرّاتٍ على
    // سيّارةٍ زايد على سيّارةٍ واحدة، وثلاثةُ كروتٍ متطابقة تُقرأ ثلاثَ
    // سيّارات. والأحدثُ أوّلاً كما وصلت من الخادم.
    //
    // **والكرتُ يأتي مع المزايدة الآن.** T951. كان يُقرأ بمعرّف المركبة من
    // `vehicleProvider`، وذاك يجلب التفاصيلَ **وكلَّ الصور** — طلبين لكلّ
    // صفّ. قِيس في سجلّ الخادم: سبعُ مزايدات = أربعةَ عشرَ طلباً زائداً،
    // وبعشرين أربعون. والآن صفرٌ: `bids/mine/` يحمل الكروت في استجابته،
    // وسبعةُ استعلاماتٍ في الخلفية مهما طالت الصفحة.
    final seen = <String>{};
    final cards = <VehicleSummary>[];
    for (final bid in bids) {
      final card = bid.vehicle;
      if (card != null && seen.add(bid.vehicleId)) cards.add(card);
    }

    // **`navActivity` لا `myActivityTitle`**: الثاني نصُّه «حسابي» من يوم
    // كانت الشاشةُ ثلاثةَ تبويبات تحت ذلك الاسم، فكان الشريطُ يقول «حسابي»
    // فوق قائمة مركبات. والاسمُ الصحيح هو اسمُ القسم في الشريط السفليّ نفسه.
    final header = HarajAppBar(title: l10n.navActivity);

    if (cards.isEmpty) {
      return ListView(
        // **قائمةٌ لا `Center`**: الحالةُ الفارغة يجب أن تُسحب لتحديث القائمة،
        // ومن فتح القسم قبل أول مزايدة سيعود إليه بعدها.
        children: <Widget>[
          header,
          Padding(
            padding: const EdgeInsets.all(24),
            child: Text(l10n.emptyParticipations, textAlign: TextAlign.center),
          ),
        ],
      );
    }

    return ListView.builder(
      // حاشيةُ الشريط السفليّ تُضاف: `ListView` بحشوةٍ مكتوبة لا يقرأ
      // `MediaQuery`، فيقع آخرُ كرتٍ تحت الشريط.
      padding: EdgeInsets.only(
        bottom: 24 + MediaQuery.paddingOf(context).bottom,
      ),
      // **العنوانُ عنصرٌ في القائمة**: هو ما يجعله ينزلق. وفهرسُ المركبة
      // يُزاح واحداً لأجله.
      itemCount: cards.length + 1,
      itemBuilder: (context, index) =>
          index == 0 ? header : VehicleCard(vehicle: cards[index - 1]),
    );
  }
}
