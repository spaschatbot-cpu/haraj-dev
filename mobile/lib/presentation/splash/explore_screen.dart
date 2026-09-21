import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../l10n/generated/app_localizations.dart';
import 'onboarding_parts.dart';

/// الصفحةُ الثالثة — ما تقدّمه المنصّة، ثم الدخول.
///
/// آخرُ ثلاثٍ: الشعار (`/splash`)، ثم المزادُ الجاري (`/welcome`)، ثم هذه —
/// **وهي التي تقول ماذا بعد المزايدة**: نقلُ الملكيّة، والدفعُ الآمن، والشحن.
/// وزرُّها يفتح الصالة.
///
/// **وتختلف عن أختها في ثلاثة أشياء مقصودة**، وإلا قُرئت الصفحتان صفحةً
/// واحدةً تكرّرت:
///
/// * **الكلامُ في الوسط لا على الحافّة.** الثانيةُ تعرض صفقةً فيُقرأ نصُّها
///   حاشيةً على الكرت (محاذاةٌ إلى البداية)، وهذه تعرض وعداً فيقف في الوسط.
/// * **الزرُّ كحليٌّ لا أزرق.** آخرُ زرٍّ قبل الدخول، ولونُه الأغمق يقول
///   «هذه النهاية» — ثلاثةُ أزرارٍ بلونٍ واحدٍ لا تقول أين أنت.
/// * **شاراتُ الصورة خدماتٌ لا حالةُ مزاد.** «مباشر» و«اللوت» تخصّان صفقةً
///   بعينها وهي في الثانية؛ وهنا «تسليم مفتاح فوري» و«نقل الملكيّة» و«شحن
///   لكل المدن» — وصفُ المنصّة، فتُعرض ولو لم يكن ثمّة مزادٌ جارٍ.
///
/// **والسيّارةُ الثانية لا الأولى** (`vehicleAt: 1`): الصفحتان متتاليتان،
/// وصورةٌ واحدةٌ فيهما تُقرأ شاشةً لم تتغيّر.
class ExploreScreen extends ConsumerStatefulWidget {
  const ExploreScreen({super.key});

  @override
  ConsumerState<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends ConsumerState<ExploreScreen> {
  /// طلبٌ واحدٌ يُبنى مرّة. والشبكةُ نفسُها التي طلبتها الصفحةُ قبلها، فترد
  /// من كاش الطبقة إن كان لها كاش، ولا تُطلب مرّتين في الثانية على أي حال.
  late final Future<VehicleFeed?> _feed = _load();

  Future<VehicleFeed?> _load() async {
    final snapshot = await ref.read(loadVehicleFeedProvider)(
      const VehicleQuery(phase: AuctionPhase.active),
    );
    return snapshot.value;
  }

  void _enter() => context.go(Routes.homePath);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<HarajPalette>()!;
    final strings = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: palette.pageBackground,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, box) {
            final metrics = OnboardingMetrics.of(box.maxHeight);
            return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
            child: ConstrainedBox(
              // `IntrinsicHeight` كي يعمل `Spacer` داخل غلافٍ قابلٍ للتمرير:
              // بدونه يحسب الباقيَ صفراً فيتكوّم المحتوى في الأعلى.
              constraints: BoxConstraints(minHeight: box.maxHeight - 32),
              child: IntrinsicHeight(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    OnboardingHeader(
                      theme: theme,
                      palette: palette,
                      strings: strings,
                      onSkip: _enter,
                      metrics: metrics,
                    ),
                    SizedBox(height: metrics.gap),
                    FutureBuilder<VehicleFeed?>(
                      future: _feed,
                      builder: (context, snap) => OnboardingCard(
                        palette: palette,
                        feed: snap.data,
                        loading:
                            snap.connectionState == ConnectionState.waiting,
                        // **٤٢٪ من الارتفاع المتاح سقفاً.** قِيس على ثلاثة
                        // هواتف: بدونه يفيض iPhone SE فيلزم التمرير،
                        // والزرُّ يقع تحت الطيّة.
                        maxHeight: metrics.cardMax,
                          // العرضُ من `LayoutBuilder` الخارجيّ ناقصاً الحشوة
                          // الأفقيّة — فلا `LayoutBuilder` داخل `IntrinsicHeight`.
                          width: box.maxWidth - 40,
                        vehicleAt: 1,
                        // `start` هي **اليمين** في صفحةٍ عربيّة و`end`
                        // اليسار. وكانت الثلاثُ معكوسةً عن التصميم: مفتاحٌ
                        // يساراً وضمانٌ يميناً. رُئي في اللقطة.
                        topStart: <Widget>[
                          OnboardingChip(
                            theme: theme,
                            tint: palette.timerBadge,
                            icon: Icons.vpn_key_outlined,
                            label: strings.exploreChipKeys,
                          ),
                        ],
                        bottomStart: <Widget>[
                          OnboardingChip(
                            theme: theme,
                            tint: palette.goldOnDark,
                            icon: Icons.assignment_turned_in_outlined,
                            label: strings.exploreChipTransfer,
                          ),
                        ],
                        bottomEnd: <Widget>[
                          OnboardingChip(
                            theme: theme,
                            tint: palette.gold,
                            icon: Icons.local_shipping_outlined,
                            label: strings.exploreChipShipping,
                          ),
                        ],
                      ),
                    ),
                    // **الفراغُ يُقسَم ٢:٢:١ على ثلاثة مواضع.** كان كلُّه
                    // فوق النصّ فحفر حفرةً تحت الكرت، ثمّ صار ٣:٢ فبقيت
                    // الكتلةُ ملتصقةً بحافّة الشاشة السفلى. والثلثُ الأخير
                    // **تحت سطر الترخيص** يرفع الزرَّ والكلامَ عن الحافّة.
                    const Spacer(flex: 2),
                    SizedBox(height: metrics.gap),
                    // **الكلامُ في الوسط**: الوعدُ يقف وسطَ الشاشة،
                    // والحاشيةُ تلزم حافّتها.
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: <Widget>[
                        OnboardingEyebrow(
                          theme: theme,
                          palette: palette,
                          label: strings.exploreEyebrow,
                        ),
                        const SizedBox(height: 14),
                        Text(
                          strings.exploreHeadline,
                          textAlign: TextAlign.center,
                          style: (metrics.compact
                                  ? theme.textTheme.titleLarge
                                  : theme.textTheme.headlineSmall)?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: palette.ink,
                            height: 1.4,
                            letterSpacing: -0.2,
                          ),
                        ),
                        const SizedBox(height: 9),
                        Text(
                          strings.exploreBody,
                          textAlign: TextAlign.center,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: palette.inkMuted,
                            height: 1.8,
                          ),
                        ),
                      ],
                    ),
                    const Spacer(flex: 2),
                    SizedBox(height: metrics.tight),
                    OnboardingDots(
                      palette: palette,
                      strings: strings,
                      count: 3,
                      current: 3,
                    ),
                    SizedBox(height: metrics.tight),
                    OnboardingCta(
                      theme: theme,
                      label: strings.exploreCta,
                      // **أزرقُ كالصفحة قبلها** بأمر المالك. وكان كحليّاً
                      // ليقول «هذه النهاية»؛ والقرارُ أن يتشابه الزرّان،
                      // فالتدرّجُ في النقاط لا في اللون.
                      fill: palette.gold,
                      onPressed: _enter,
                      metrics: metrics,
                    ),
                    // سطرُ الترخيص حُذف بأمر المالك. والفراغُ الذي كان
                    // تحته يبقى: هو الذي يرفع الزرَّ عن حافّة الشاشة.
                    const Spacer(flex: 1),
                  ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
