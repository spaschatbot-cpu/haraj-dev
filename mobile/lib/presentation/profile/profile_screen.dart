import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../app/theme.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/money.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../l10n/generated/app_localizations.dart';
import '../auth/session_controller.dart';
import '../common/failure_view.dart';
import '../common/stale_data_banner.dart';
import '../wallet/wallet_controller.dart';
import 'profile_controller.dart';

/// شاشة «حسابي» — بطاقةُ العميل، ثم قائمةُ الخدمات.
///
/// **بلا `HarajAppBar`** (١٣ سبتمبر ٢٠٢٦، بطلب المالك): حُذف شريطُ «ملفي»
/// وزرُّ البيت وزرُّ الخروج، فصار الهيدرُ الكحليُّ في القشرة — يعرض «حسابي» —
/// هو عنوانَ الشاشة الوحيد. **وحُذف نموذجُ التعديل كلُّه** (الاسم والبريد
/// والهوية والجوال وبيانات الشركة والعنوان الوطنيّ) بطلب المالك؛ ما بقي عرضٌ
/// لا تحرير.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileControllerProvider);

    return Scaffold(
      body: switch (profile) {
        AsyncData(:final value) => _ProfileBody(snapshot: value),
        AsyncError(:final error) => Center(
          child: FailureView(
            failure: error is Failure ? error : UnexpectedFailure(error),
            onRetry: () =>
                ref.read(profileControllerProvider.notifier).refresh(),
          ),
        ),
        _ => const Center(child: CircularProgressIndicator()),
      },
    );
  }
}

class _ProfileBody extends ConsumerWidget {
  const _ProfileBody({required this.snapshot});

  final Snapshot<CustomerProfile> snapshot;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final profile = snapshot.value;

    // الرصيد للزرّ البارز في الرأس — من مزوّد المحفظة نفسه لا رقمٍ من عندنا.
    // يبقى `null` حتى يصل، فيعرض الزرُّ شرطةً بدل صفرٍ كاذب.
    final balance = switch (ref.watch(walletBalanceProvider)) {
      AsyncData(:final value) => value.value.available,
      _ => null,
    };

    return ListView(
      // حاشيةٌ سفليّةٌ تُضاف إلى ما فرضته القشرة تحت الشريط السفليّ
      // (`_BarInset`): بلا هذه، حشوةُ `ListView` الصريحة تُلغي حاشيةَ
      // القشرة فيُقصّ آخرُ عنصرٍ تحت الشريط ولا يصل إليه التمرير. بطلب
      // المالك: «السكرول يشتغل لآخر الصفحة» (١٣ سبتمبر ٢٠٢٦).
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        16 + MediaQuery.paddingOf(context).bottom,
      ),
      children: [
        StaleDataBanner(snapshot: snapshot),
        _ProfileHeaderCard(profile: profile, balance: balance),
        const SizedBox(height: 20),

        // قائمة صفحات «حسابي» (١٣ سبتمبر ٢٠٢٦). محتوى كل صفحةٍ يُملأ لاحقاً؛
        // هنا مداخلها فقط. «محفظتي» تفتح تبويب المحفظة القائم لا صفحةً ثانية.
        Text(
          l10n.accountMenuSection,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 4),
        _AccountMenuTile(
          icon: Icons.account_balance_wallet_outlined,
          label: l10n.accountMenuWallet,
          onTap: () => context.goNamed(Routes.wallet),
        ),
        _AccountMenuTile(
          icon: Icons.assignment_return_outlined,
          label: l10n.accountMenuRefundDeposit,
          onTap: () => context.goNamed(Routes.accountRefundDeposit),
        ),
        _AccountMenuTile(
          icon: Icons.shopping_bag_outlined,
          label: l10n.accountMenuPurchases,
          onTap: () => context.goNamed(Routes.accountPurchases),
        ),
        _AccountMenuTile(
          icon: Icons.receipt_long_outlined,
          label: l10n.accountMenuOrders,
          onTap: () => context.goNamed(Routes.accountOrders),
        ),
        _AccountMenuTile(
          icon: Icons.edit_note_outlined,
          label: l10n.accountMenuEditRequest,
          onTap: () => context.goNamed(Routes.accountEditRequest),
        ),
        _AccountMenuTile(
          icon: Icons.how_to_reg_outlined,
          label: l10n.accountMenuRegistrationGuide,
          onTap: () => context.goNamed(Routes.accountRegistrationGuide),
        ),
        _AccountMenuTile(
          icon: Icons.savings_outlined,
          label: l10n.accountMenuWalletGuide,
          onTap: () => context.goNamed(Routes.accountWalletGuide),
        ),
        _AccountMenuTile(
          icon: Icons.info_outline,
          label: l10n.accountMenuAbout,
          onTap: () => context.goNamed(Routes.accountAbout),
        ),
        _AccountMenuTile(
          icon: Icons.help_outline,
          label: l10n.accountMenuFaq,
          onTap: () => context.goNamed(Routes.accountFaq),
        ),
        _AccountMenuTile(
          icon: Icons.gavel_outlined,
          label: l10n.accountMenuTerms,
          onTap: () => context.goNamed(Routes.accountTerms),
        ),
        _AccountMenuTile(
          icon: Icons.support_agent_outlined,
          label: l10n.accountMenuSupport,
          onTap: () => context.goNamed(Routes.accountSupport),
        ),

        const SizedBox(height: 4),

        // تسجيل الخروج — عاد بطلب المالك (١٣ سبتمبر ٢٠٢٦) بعد حذف أيقونته من
        // الهيدر. أيقونتُه حمراء لأنه فعلٌ يُخرج من الحساب لا خدمةٌ مثلَ ما
        // فوقه.
        _AccountMenuTile(
          icon: Icons.power_settings_new_rounded,
          label: l10n.profileSignOut,
          danger: true,
          onTap: () => ref.read(sessionControllerProvider.notifier).signOut(),
        ),

        const SizedBox(height: 20),

        // محدّد اللغة ثم مواقع التواصل — فوتر الصفحة على موكاب المالك.
        _LanguageSelector(l10n: l10n),
        const SizedBox(height: 20),
        const _SocialRow(),
      ],
    );
  }
}

/// بطاقةُ رأس الملف الشخصي — على موكاب المالك (١٣ سبتمبر ٢٠٢٦): صورةٌ رمزيّة
/// في الأعلى، ثم الاسم والجوال، ثم شارةُ نوع الحساب، ثم زرُّ المحفظة البارز.
///
/// **بطاقةٌ بيضاء لا داكنة**، بألوان التطبيق: الكحليُّ (`ink`) للنصّ، والذهبيُّ
/// (`gold`) للصورة والزرّ. الموكابُ كان بنّيّاً ذهبيّاً، والعائلةُ البنّيّةُ
/// بُدِّلت كحليّاً في ٩ سبتمبر — فالشكلُ من الموكاب واللونُ من اللوحة.
///
/// **الرصيدُ من الخادم لا صفرٌ مكتوب**: يصل `null` قبل أن تردَّ المحفظة فيعرض
/// الزرُّ شرطةً، ولا يُعرض صفرٌ يُقرأ رصيداً وهو غيابُ جواب (شاشةُ مال).
class _ProfileHeaderCard extends StatelessWidget {
  const _ProfileHeaderCard({required this.profile, this.balance});

  final CustomerProfile profile;

  /// رصيد المحفظة المتاح، أو `null` حتى يصل.
  final Money? balance;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final palette = HarajPalette.of(context);
    final isCompany = profile.accountType == 'company';

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
      decoration: BoxDecoration(
        color: palette.cardSurface,
        borderRadius: BorderRadius.circular(24),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: palette.ink.withValues(alpha: 0.10),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: <Widget>[
          // الصورة الرمزيّة: أيقونةُ عميلٍ بالذهبيّ داخل حلقةٍ ذهبيّة على
          // أرضيّةٍ كحليّة متدرّجة. أيقونةٌ لا حرفان بطلب المالك — رمزٌ واحدٌ
          // للحساب أوضحُ من حرفين يختلفان بكل اسم.
          Container(
            width: 84,
            height: 84,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topRight,
                end: Alignment.bottomLeft,
                colors: <Color>[palette.heroTop, palette.heroBottom],
              ),
              border: Border.all(color: palette.gold, width: 2.5),
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: palette.gold.withValues(alpha: 0.28),
                  blurRadius: 14,
                ),
              ],
            ),
            child: Icon(
              isCompany ? Icons.business_rounded : Icons.person_rounded,
              color: palette.goldOnDark,
              size: 44,
            ),
          ),
          const SizedBox(height: 14),

          // الاسم.
          Text(
            profile.displayName,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: palette.ink,
              fontSize: 20,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 6),

          // الجوال، باتجاه LTR كي لا تنقلب أرقامه.
          Text(
            profile.phone,
            textDirection: TextDirection.ltr,
            style: TextStyle(
              color: palette.inkMuted,
              fontSize: 14,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 14),

          // شارتان: نوعُ الحساب، والتوثيقُ إن وُجد.
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _HeaderChip(
                icon: isCompany
                    ? Icons.business_outlined
                    : Icons.person_outline,
                label: isCompany
                    ? l10n.profileAccountCompany
                    : l10n.profileAccountIndividual,
                palette: palette,
              ),
              if (profile.nationalIdVerified)
                _HeaderChip(
                  icon: Icons.verified_outlined,
                  label: l10n.profileIdVerified,
                  palette: palette,
                  highlight: true,
                ),
            ],
          ),
          const SizedBox(height: 18),

          // زرُّ المحفظة البارز — التدرّجُ الذهبيّ، والرصيدُ من الخادم.
          _WalletButton(balance: balance, palette: palette),
        ],
      ),
    );
  }
}

/// زرُّ المحفظة البارز في رأس الملف — يفتح المحفظة، ويعرض الرصيد المتاح.
class _WalletButton extends StatelessWidget {
  const _WalletButton({required this.balance, required this.palette});

  final Money? balance;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => context.goNamed(Routes.wallet),
        child: Ink(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: LinearGradient(
              begin: Alignment.topRight,
              end: Alignment.bottomLeft,
              colors: <Color>[palette.gold, palette.goldDeep],
            ),
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: palette.gold.withValues(alpha: 0.35),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              const Icon(
                Icons.account_balance_wallet_rounded,
                color: Colors.white,
                size: 20,
              ),
              const SizedBox(width: 10),
              Text(
                l10n.accountMenuWallet,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  fontFamily: HarajTheme.fontFamily,
                ),
              ),
              const SizedBox(width: 8),
              Container(width: 1, height: 16, color: Colors.white24),
              const SizedBox(width: 8),
              // الرصيد: شرطةٌ حتى يصل، ثم المبلغ والعملة كما أرسلهما الخادم.
              Directionality(
                textDirection: TextDirection.ltr,
                child: Text(
                  balance == null
                      ? '—'
                      : '${balance!.amount} ${balance!.currency}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// شارةٌ صغيرة في رأس الملف — نوعُ الحساب أو توثيقُ الهوية.
class _HeaderChip extends StatelessWidget {
  const _HeaderChip({
    required this.icon,
    required this.label,
    required this.palette,
    this.highlight = false,
  });

  final IconData icon;
  final String label;
  final HarajPalette palette;

  /// الشارةُ المميَّزة (التوثيق) ذهبيّةٌ محدَّدة؛ غيرُها كحليّةٌ هادئة.
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final colour = highlight ? palette.gold : palette.inkMuted;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: colour.withValues(alpha: highlight ? 0.12 : 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: colour.withValues(alpha: highlight ? 0.55 : 0.25),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 15, color: colour),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: colour,
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
        ],
      ),
    );
  }
}

/// سطرٌ في قائمة «حسابي» — بطاقةٌ بيضاء بأيقونةٍ ذهبيّةٍ دائريّة على موكاب
/// المالك، واللونُ من لوحة التطبيق لا من الموكاب.
///
/// عنصرٌ واحد يُعاد استعماله لكل السطور (المادة ٤-٥): تغييرُ هيئة القائمة يحدث
/// في مكانٍ واحد، فلا يفترق سطرٌ عن سطر.
class _AccountMenuTile extends StatelessWidget {
  const _AccountMenuTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.danger = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  /// عنصرٌ خطِر (تسجيل الخروج) — أيقونتُه حمراء داخل دائرةٍ حمراء خفيفة، لا
  /// ذهبيّة، فيُقرأ أنه يُخرج لا أنه خدمة.
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    const dangerColour = Color(0xFFC0392B);
    // **سطحٌ واحدٌ أبيضُ لا سطحان.** كان الظلُّ على `Ink` داخلَ `Material`
    // أبيض، فبدا مربّعاً داخل مربّع (١٣ سبتمبر ٢٠٢٦). الآن: حاويةٌ واحدةٌ
    // بيضاءُ ناصعةٌ بظلٍّ خارجيٍّ خفيفٍ فقط، وفوقها `Material` شفّافةٌ للنقر —
    // فلا لونَ في الداخل غيرُ الأبيض، ولا حدَّ داخليّ.
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: palette.cardSurface,
          borderRadius: BorderRadius.circular(16),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: palette.ink.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            // لا تحويمَ ولا لمسةَ ملوّنة — المربّعُ أبيضُ فقط على الويب.
            hoverColor: Colors.transparent,
            splashColor: Colors.transparent,
            highlightColor: Colors.transparent,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
              children: <Widget>[
                // أيقونةٌ دائريّة (البادئة في RTL = يمين السطر): ذهبيّة
                // للخدمات، وحمراءُ خفيفةٌ لتسجيل الخروج.
                Container(
                  width: 44,
                  height: 44,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: danger
                        ? null
                        : LinearGradient(
                            begin: Alignment.topRight,
                            end: Alignment.bottomLeft,
                            colors: <Color>[palette.gold, palette.goldDeep],
                          ),
                    color: danger
                        ? dangerColour.withValues(alpha: 0.12)
                        : null,
                  ),
                  child: Icon(
                    icon,
                    color: danger ? dangerColour : Colors.white,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: danger ? dangerColour : palette.ink,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      fontFamily: HarajTheme.fontFamily,
                    ),
                  ),
                ),
                // دائرةٌ خافتةٌ حول السهم — بحبرٍ خفيف لا ذهبيّ فلا ينازع
                // الأيقونةَ البادئة. **`chevron_right`** بطلب المالك: يشير
                // نحو النصّ لا بعيداً عنه.
                Container(
                  width: 30,
                  height: 30,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: palette.ink.withValues(alpha: 0.06),
                  ),
                  child: Icon(
                    Icons.chevron_right,
                    size: 20,
                    color: palette.inkMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
    );
  }
}

/// محدّدُ اللغة في فوتر «حسابي» — على موكاب المالك: العربيّةُ مختارةٌ ذهبيّة،
/// وبقيّةُ اللغات معروضة.
///
/// **العربيّةُ وحدها مفعَّلةٌ اليوم**: لغةُ التطبيق مثبَّتةٌ عليها في جذره
/// (`HarajApp`: «العربيّة هي الأصل… لا يُغيَّر من داخل التطبيق»)، ولا ترجمةَ
/// للهنديّة والأورديّة والإنجليزيّة بعد. فاختيارُ غيرِها يقول «لم تُفعَّل بعد»
/// بدل أن يبدّل صامتاً إلى نصفِ ترجمة — وهو نظيرُ «قريباً» في طرق الدفع.
class _LanguageSelector extends StatelessWidget {
  const _LanguageSelector({required this.l10n});

  final AppLocalizations l10n;

  /// أسماءُ اللغات بأسمائها لا مترجَمةً — الاسمُ الأصليّ هو ما يعرفه صاحبُها.
  static const List<({String name, bool active})> _languages =
      <({String name, bool active})>[
        (name: 'العربية', active: true),
        (name: 'English', active: false),
        (name: 'اردو', active: false),
        (name: 'हिन्दी', active: false),
      ];

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          l10n.accountLanguageSection,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 10),
        // الأربعُ في صفٍّ واحد بأعمدةٍ متساوية — بطلب المالك (١٣ سبتمبر
        // ٢٠٢٦). صفٌّ من `Expanded` لا `Wrap`: يقسم العرضَ بالتساوي فلا
        // تنكسر لغةٌ إلى سطرٍ ثانٍ، ويُقرأ محدِّداً مقطعيّاً واحداً.
        Row(
          children: <Widget>[
            for (var i = 0; i < _languages.length; i++) ...<Widget>[
              if (i > 0) const SizedBox(width: 8),
              Expanded(
                child: _LanguageChip(
                  name: _languages[i].name,
                  active: _languages[i].active,
                  palette: palette,
                  onTap: _languages[i].active
                      ? null
                      : () => ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(l10n.accountLanguageSoon)),
                        ),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }
}

class _LanguageChip extends StatelessWidget {
  const _LanguageChip({
    required this.name,
    required this.active,
    required this.palette,
    required this.onTap,
  });

  final String name;
  final bool active;
  final HarajPalette palette;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            gradient: active
                ? LinearGradient(
                    begin: Alignment.topRight,
                    end: Alignment.bottomLeft,
                    colors: <Color>[palette.gold, palette.goldDeep],
                  )
                : null,
            color: active ? null : palette.cardSurface,
            border: active
                ? null
                : Border.all(color: palette.ink.withValues(alpha: 0.15)),
          ),
          child: Text(
            name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: active ? Colors.white : palette.inkMuted,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
        ),
      ),
    );
  }
}

/// صفُّ أيقونات مواقع التواصل — على موكاب المالك.
///
/// **بلا روابط بعد**: عناوينُ الحسابات لم تصل، فالأيقوناتُ علامةٌ بصريّة لا
/// أزرارٌ تفتح شيئاً — زرٌّ يفتح صفحةً فارغة أسوأ من أيقونةٍ تدلّ. تُوصَل
/// بالروابط حين تصل.
///
/// **`IconData` مبنيّةٌ باليد لا `FontAwesomeIcons`**: حزمة `font_awesome_flutter`
/// تُبقى تبعيّةً لأنها تحمل خطَّ الشعارات، لكنّ أصنافها (`IconDataBrands extends
/// IconData`) لا تُترجَم على نسخة Flutter هنا — `IconData` صارت `final`
/// فيُرفَض توريثُها. والبناءُ المباشر يمرّ: الصنفُ النهائيّ يُنشَأ ولا يُورَّث،
/// والخطُّ يُحمَّل باسم عائلته من تبعيّة الحزمة. ورموزُ النقاط من تعريفات
/// الحزمة نفسها (Font Awesome 7 Brands).
class _SocialRow extends StatelessWidget {
  const _SocialRow();

  static const String _family = 'FontAwesomeBrands';
  static const String _package = 'font_awesome_flutter';

  static const List<IconData> _icons = <IconData>[
    IconData(0xf2ab, fontFamily: _family, fontPackage: _package), // snapchat
    IconData(0xe07b, fontFamily: _family, fontPackage: _package), // tiktok
    IconData(0xf08c, fontFamily: _family, fontPackage: _package), // linkedin
    IconData(0xe61b, fontFamily: _family, fontPackage: _package), // x
    IconData(0xf16d, fontFamily: _family, fontPackage: _package), // instagram
    IconData(0xf09a, fontFamily: _family, fontPackage: _package), // facebook
  ];

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        for (final icon in _icons)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Icon(icon, size: 22, color: palette.ink),
          ),
      ],
    );
  }
}
