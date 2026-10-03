import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../domain/bidding/entities/live_bids_update.dart';
import '../../domain/bidding/entities/placed_bid.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../l10n/generated/app_localizations.dart';
import '../common/failure_message.dart';
import '../common/failure_view.dart';
import '../common/haraj_app_bar.dart';
import '../common/money_text.dart';
import '../common/saudi_time.dart';
import '../common/stale_data_banner.dart';
import 'bidding_controllers.dart';
import 'live_status_banner.dart';

/// مزايداتي.
///
/// ثلاث حالات لا اثنتان: تحميل، وفشل بجواب الخادم وزرّ إعادة، وحالة فارغة
/// مكتوبة. شاشةٌ تعرض دوّامةً إلى الأبد عند سقوط الشبكة عطلٌ لا تصميم — ولذلك
/// أيضاً تظهر البيانات المحفوظة بعلامة «آخر تحديث» بدل شاشة خطأ (H5).
class MyBidsScreen extends ConsumerWidget {
  const MyBidsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final bids = ref.watch(myBidsProvider);
    final live = ref.watch(liveBidsProvider);

    return Scaffold(
      // شفّافةٌ فوق `GlassBackdrop` — تصميمُ الزجاج الأبيض بطلب المالك
      // (٣ أكتوبر ٢٠٢٦).
      backgroundColor: Colors.transparent,
      appBar: HarajAppBar(title: l10n.myBidsTitle),
      body: Column(
        children: [
          LiveStatusBanner(
            connection: live.value?.connection ?? LiveConnection.connecting,
          ),
          Expanded(
            child: bids.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stackTrace) => Center(
                child: FailureView(
                  failure: error is Failure
                      ? error
                      : UnexpectedFailure(error, stackTrace: stackTrace),
                  onRetry: () => ref.invalidate(myBidsProvider),
                ),
              ),
              data: (snapshot) => _Bids(snapshot: snapshot),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bids extends ConsumerWidget {
  const _Bids({required this.snapshot});

  final Snapshot<List<PlacedBid>> snapshot;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final bids = snapshot.value;

    return Column(
      children: [
        StaleDataBanner(snapshot: snapshot),
        Expanded(
          child: bids.isEmpty
              ? _EmptyBids(message: l10n.myBidsEmpty)
              : RefreshIndicator(
                  onRefresh: () async => ref.invalidate(myBidsProvider),
                  // كروتٌ زجاجيّة بفجوة ١٢ لا صفوفٌ بفواصل — تصميمُ الزجاج
                  // الأبيض (٣ أكتوبر ٢٠٢٦): الفاصلُ الرماديّ على أرضيّةٍ
                  // متدرّجة يُقرأ خدشاً لا حدّاً.
                  child: ListView.separated(
                    padding: EdgeInsets.fromLTRB(
                      16,
                      16,
                      16,
                      24 + MediaQuery.paddingOf(context).bottom,
                    ),
                    itemCount: bids.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 12),
                    itemBuilder: (context, index) => _BidTile(bid: bids[index]),
                  ),
                ),
        ),
      ],
    );
  }
}

class _BidTile extends ConsumerWidget {
  const _BidTile({required this.bid});

  final PlacedBid bid;

  Future<void> _withdraw(BuildContext context, WidgetRef ref) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.bidWithdrawConfirmTitle),
        content: Text(l10n.bidWithdrawConfirmBody(bid.vehicleTitle)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(l10n.bidWithdrawAction),
          ),
        ],
      ),
    );
    if (!(confirmed ?? false) || !context.mounted) return;

    try {
      await ref.read(withdrawBidProvider)(bid.id);
      ref.invalidate(myBidsProvider);
      messenger.showSnackBar(SnackBar(content: Text(l10n.bidWithdrawn)));
    } on Failure catch (failure) {
      // جواب الخادم كما جاء: «هذه المزايدة ليست مزايدتك»، «انتهى المزاد»… أي
      // منها أوضح من «تعذّر السحب» التي كنا سنكتبها نحن.
      if (!context.mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(failureMessage(context, failure))),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final placedAt = SaudiTime.forDisplay(bid.placedAtUtc);

    // كرتٌ زجاجيّ بدل `ListTile` — تصميمُ الزجاج الأبيض بطلب المالك
    // (٣ أكتوبر ٢٠٢٦). المحتوى نفسُه: العنوان، والحال، والوقت، والمبلغ،
    // وزرُّ السحب للقائمة وحدها.
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Text(
                  bid.vehicleTitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: palette.ink,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    height: 1.4,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              // **النصّ من ملفّ الترجمة لا من الخادم.** العقد يرسل علمين
              // (`is_withdrawn` و`is_superseded`) ولا يرسل جملةً لهما — والوصف
              // نصُّ واجهةٍ يعيش حيث تعيش نصوص الواجهة (المعيار H3).
              _StatePill(state: bid.state, label: _stateLabel(l10n, bid.state)),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: <Widget>[
              Icon(Icons.schedule_rounded, size: 14, color: palette.inkMuted),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  l10n.bidPlacedAt(placedAt, placedAt),
                  style: TextStyle(
                    color: palette.inkMuted,
                    fontSize: 12.5,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: <Widget>[
              Expanded(
                child: Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: MoneyText(
                    bid.money,
                    style: TextStyle(
                      color: palette.gold,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      fontFamily: HarajTheme.fontFamily,
                    ),
                  ),
                ),
              ),
              // **السحب يُعرض للقائمة وحدها.** مزايدةٌ مسحوبةٌ لا تُسحب مرّتين،
              // ومتجاوَزةٌ لم تعد قائمةً بيده. والخادم يبقى هو الفاصل إن ضُغط
              // الزرّ على حالٍ تغيّر بين الرسم والضغط.
              if (bid.state == BidState.standing)
                OutlinedButton(
                  onPressed: () => _withdraw(context, ref),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: palette.gold,
                    side: BorderSide(
                      color: palette.gold.withValues(alpha: 0.5),
                    ),
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    textStyle: const TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  child: Text(l10n.bidWithdrawAction),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

/// شارةُ الحال — **القائمةُ بالأزرق** (ما زال أمرُها جارياً)، والمتجاوَزةُ
/// والمسحوبةُ بالباهت (انتهى أمرُهما). ألوانُ شارات كرت المركبة نفسُها،
/// بتصميم الزجاج الأبيض (٣ أكتوبر ٢٠٢٦).
class _StatePill extends StatelessWidget {
  const _StatePill({required this.state, required this.label});

  final BidState state;
  final String label;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final (ink, surface) = state == BidState.standing
        ? (palette.gold, palette.gold.withValues(alpha: 0.08))
        : (palette.inkMuted, palette.pageBackground);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: ink,
          fontSize: 11.5,
          fontWeight: FontWeight.w700,
          fontFamily: HarajTheme.fontFamily,
        ),
      ),
    );
  }
}

/// الحالةُ الفارغة — أيقونةٌ في دائرةٍ مزرقّة وسطرٌ تحتها، بتصميم الزجاج
/// الأبيض (٣ أكتوبر ٢٠٢٦). كانت سطراً عارياً على الأرضيّة.
class _EmptyBids extends StatelessWidget {
  const _EmptyBids({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Container(
              width: 88,
              height: 88,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: palette.gold.withValues(alpha: 0.10),
              ),
              child: Icon(Icons.gavel_rounded, size: 40, color: palette.gold),
            ),
            const SizedBox(height: 18),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: palette.ink,
                fontSize: 16,
                fontWeight: FontWeight.w700,
                height: 1.5,
                fontFamily: HarajTheme.fontFamily,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// وصفُ حال المزايدة بالعربية.
///
/// خريطةٌ في طبقة العرض لا في الخادم: العقد يرسل علمين برمجيّين، وترجمتُهما
/// إلى جملةٍ يقرأها إنسان شأنُ الواجهة — ولذلك هي في ملفّ الترجمة، وهذه
/// الدالة تختار المفتاح لا الجملة.
String _stateLabel(AppLocalizations l10n, BidState state) => switch (state) {
  BidState.standing => l10n.bidStateStanding,
  BidState.superseded => l10n.bidStateSuperseded,
  BidState.withdrawn => l10n.bidStateWithdrawn,
  BidState.unknown => l10n.bidStateUnknown,
};
