import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../domain/catalog/entities/auction_phase.dart';
import '../../domain/catalog/entities/vehicle_feed.dart';
import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/entities/vehicle_summary.dart';
import '../../l10n/generated/app_localizations.dart';
import 'onboarding_parts.dart';

/// الصفحةُ الثانية — المزادُ الجاري، بصورةٍ من مزادٍ حقيقيّ.
///
/// **صورةُ سيّارةٍ وعرضٌ ونداءٌ للتالي. لا أرقام.** كان الكرتُ يعرض مركبةً
/// ببياناتها — اسمُها وسنتُها وحالتُها وموقعُها والرسومُ وعدّادُ الانتهاء —
/// ثم حُذف ذلك كلُّه بأمر المالك. وبقيت الصورةُ وثلاثُ شاراتٍ صغيرةٍ عليها.
///
/// وهو حذفٌ يُقرأ صواباً في موضعه: هذه شاشةُ **ترحيب** تُرى مرّةً قبل أن
/// يدخل أحد، ودورُ الصورة فيها أن تقول «مزادُ سيّاراتٍ فاخرة» في لمحة — لا
/// أن تعرض صفقةً تُدرَس. وكلُّ ما حُذف موجودٌ على كرت المركبة في الصالة بعد
/// ضغطتين، حيث يُقارَن ويُزايَد عليه.
///
/// **وفائدةٌ عرضيّةٌ في الحذف**: الموكاب كان يعرض «أعلى مزايدة ٨٧٥٬٠٠٠»
/// و«١٤٢ مزايد»، وهما غيرُ موجودين في العقد أصلاً — المزاد **مغلق**
/// (`ce013b9`) فلا يُنشر سعرُ وقوفٍ ولا عددُ مزايدات، ومكتوبٌ في
/// [VehicleSummary] أن الكرتَ عرضهما يوماً على مخططٍ وهميّ «فكان يعد بما لا
/// يصل». وشاشةٌ بلا أرقامٍ لا يمكن أن تقع في ذلك.
///
/// **والقطعُ المشتركةُ في `onboarding_parts.dart`**: الرأسُ والكرتُ
/// والشاراتُ والنقاطُ والزرُّ والذيل تقرؤها هذه الصفحةُ والثالثةُ معاً —
/// وتعديلٌ في الرأس يقع في الاثنتين لا في واحدةٍ ويُنسى في الأخرى.
class WelcomeScreen extends ConsumerStatefulWidget {
  const WelcomeScreen({super.key});

  @override
  ConsumerState<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends ConsumerState<WelcomeScreen> {
  /// أوّلُ مركبةٍ نشطة. طلبٌ واحدٌ يُبنى مرّة، لا في `build`: `build` يُستدعى
  /// مع كلّ إعادةِ رسم، وطلبٌ فيه يعني طلباً في الثانية.
  late final Future<VehicleFeed?> _feed = _load();

  Future<VehicleFeed?> _load() async {
    final snapshot = await ref.read(loadVehicleFeedProvider)(
      const VehicleQuery(phase: AuctionPhase.active),
    );
    return snapshot.value;
  }

  void _next() => context.go(Routes.explorePath);

  void _skip() => context.go(Routes.homePath);

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
              constraints: BoxConstraints(minHeight: box.maxHeight - 32),
              child: IntrinsicHeight(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    OnboardingHeader(
                      theme: theme,
                      palette: palette,
                      strings: strings,
                      onSkip: _skip,
                      metrics: metrics,
                    ),
                    SizedBox(height: metrics.gap),
                    FutureBuilder<VehicleFeed?>(
                      future: _feed,
                      builder: (context, snap) {
                        final feed = snap.data;
                        final cars =
                            feed?.page.vehicles ?? const <VehicleSummary>[];
                        // شاراتُ **حالة المزاد**، فلا تُعرض بلا مركبةٍ
                        // حقيقيّة: «مباشر» على صورةٍ من الأصول ادّعاءٌ لا
                        // مصدرَ له. وشاراتُ الخدمة في الصفحة الثالثة تُعرض
                        // دائماً لأنها وصفُ المنصّة لا وصفُ صفقة.
                        return OnboardingCard(
                          palette: palette,
                          feed: feed,
                          loading:
                              snap.connectionState == ConnectionState.waiting,
                          // **٤٢٪ من الارتفاع المتاح سقفاً.** قِيس على
                          // ثلاثة هواتف: بدونه يفيض iPhone SE فيلزم
                          // التمرير، والزرُّ يقع تحت الطيّة.
                          maxHeight: metrics.cardMax,
                          topStart: cars.isEmpty
                              ? const <Widget>[]
                              : <Widget>[
                                  OnboardingChip(
                                    theme: theme,
                                    tint: kLiveRed,
                                    label: strings.welcomeLive,
                                    pulse: true,
                                  ),
                                ],
                          topEnd: cars.isEmpty
                              ? const <Widget>[]
                              : <Widget>[
                                  OnboardingChip(
                                    theme: theme,
                                    tint: palette.gold,
                                    icon: Icons.sell_outlined,
                                    label: strings.welcomeLot(
                                      cars.first.lotNumber,
                                    ),
                                  ),
                                ],
                          bottomEnd: cars.isEmpty
                              ? const <Widget>[]
                              : <Widget>[
                                  OnboardingChip(
                                    theme: theme,
                                    tint: palette.timerBadge,
                                    icon: Icons.directions_car_filled_outlined,
                                    label: strings.welcomeActiveVehicles(
                                      '${feed?.counts.active ?? cars.length}',
                                    ),
                                  ),
                                ],
                        );
                      },
                    ),
                    // **الفراغُ يُقسَم ٢:٢:١ على ثلاثة مواضع.** كان كلُّه
                    // فوق النصّ فحفر حفرةً تحت الكرت، ثمّ صار ٣:٢ فبقيت
                    // الكتلةُ ملتصقةً بحافّة الشاشة السفلى. والثلثُ الأخير
                    // **تحت سطر الترخيص** يرفع الزرَّ والكلامَ عن الحافّة.
                    const Spacer(flex: 2),
                    SizedBox(height: metrics.gap),
                    // **الكلامُ على الحافّة لا في الوسط**: هذه الصفحةُ تعرض
                    // صفقةً، فنصُّها حاشيةٌ على الكرت. والثالثةُ تعرض وعداً
                    // فيقف كلامُها في الوسط.
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        OnboardingEyebrow(
                          theme: theme,
                          palette: palette,
                          label: strings.welcomeEyebrow,
                        ),
                        const SizedBox(height: 14),
                        // عنوانٌ بلونين في فقرةٍ واحدة: `Text.rich` لا نصّان
                        // متجاوران — النصّان ينكسران عند حافّتين مختلفتين.
                        Text.rich(
                          TextSpan(
                            children: <InlineSpan>[
                              TextSpan(
                                text: '${strings.welcomeHeadlineLead} ',
                              ),
                              TextSpan(
                                text: strings.welcomeHeadlineAccent,
                                style: TextStyle(color: palette.gold),
                              ),
                            ],
                          ),
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
                        // **ولا سقفَ عرضٍ هنا.** جرّبتُ `maxWidth` لأمنع
                        // الكلمةَ اليتيمة في آخر السطر فزادها سوءاً: يقصّ
                        // السطرَ الأوّل مبكّراً ويتركها وحدها كما كانت.
                        // والعلاجُ في الجملة — قُصِّرت كلمةً فملأت سطرها.
                        Text(
                          strings.welcomeBody,
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
                      current: 2,
                    ),
                    SizedBox(height: metrics.tight),
                    OnboardingCta(
                      theme: theme,
                      label: strings.welcomeCta,
                      fill: palette.gold,
                      onPressed: _next,
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
