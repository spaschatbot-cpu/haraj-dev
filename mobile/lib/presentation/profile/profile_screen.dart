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

    // تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): الخلفيّةُ المتدرّجة
    // مرسومةٌ خلف كلّ المسارات (`GlassBackdrop`)، وأرضيّةٌ صلبةٌ هنا تحجبها.
    return Scaffold(
      backgroundColor: Colors.transparent,
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
        // التسجيلُ الناقص يُقال أوّلَ الصفحة ويُفتح بابُه — لمن خرج من «أكمل
        // تسجيلك» قبل أن يُنهيها. والناقصُ جوابُ الخادم (`registrationMissing`)،
        // والمزايدةُ ترفض صاحبَه على أيّ حال.
        if (!profile.isRegistered) ...<Widget>[
          _RegistrationBanner(
            text: l10n.registrationBanner(
              profile.registrationMissing.map((gap) => gap.label).join('، '),
            ),
            onTap: () => context.pushNamed(Routes.completeRegistration),
          ),
          const SizedBox(height: 14),
        ],
        _ProfileHeaderCard(profile: profile, balance: balance),
        const SizedBox(height: 20),

        // قائمة صفحات «حسابي» (١٣ سبتمبر ٢٠٢٦). محتوى كل صفحةٍ يُملأ لاحقاً؛
        // هنا مداخلها فقط. «محفظتي» تفتح تبويب المحفظة القائم لا صفحةً ثانية.
        //
        // **السطورُ في بطاقةٍ واحدةٍ بخيوطٍ رفيعة** لا أحدَ عشرَ مربّعاً
        // متراصّاً (الزجاج الأبيض، ٣ أكتوبر ٢٠٢٦): المربّعاتُ المنفصلة على
        // خلفيّةٍ شفّافة تُقرأ ضجيجاً، والمجموعةُ تُقرأ قائمةً واحدة.
        _SectionTitle(l10n.accountMenuSection),
        const SizedBox(height: 10),
        _MenuCard(
          children: <Widget>[
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
          ],
        ),

        const SizedBox(height: 14),

        // تسجيل الخروج — عاد بطلب المالك (١٣ سبتمبر ٢٠٢٦) بعد حذف أيقونته من
        // الهيدر. أيقونتُه حمراء لأنه فعلٌ يُخرج من الحساب لا خدمةٌ مثلَ ما
        // فوقه، **وفي بطاقةٍ وحدَه** كي لا يُلمَس سهواً بين الخدمات.
        _MenuCard(
          children: <Widget>[
            _AccountMenuTile(
              icon: Icons.power_settings_new_rounded,
              label: l10n.profileSignOut,
              danger: true,
              onTap: () =>
                  ref.read(sessionControllerProvider.notifier).signOut(),
            ),
          ],
        ),

        const SizedBox(height: 20),

        // محدّد اللغة ثم مواقع التواصل — فوتر الصفحة على موكاب المالك.
        _LanguageSelector(l10n: l10n),
        const SizedBox(height: 24),
        const _SocialRow(),
        const SizedBox(height: 8),
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
      // **بطاقةٌ مقصوصة**: الشريطُ الداكن يبلغ حافّتها، والقصُّ هو ما يدوّر
      // زاويتيه العلويّتين — وتدويرٌ ثانٍ عليه يترك بين القوسين هلالاً أبيض.
      clipBehavior: Clip.antiAlias,
      decoration: _glassCard(palette),
      child: Column(
        children: <Widget>[
          // **شريطٌ فاتحٌ في رأس البطاقة والصورةُ نصفُها عليه**، لا كحليٌّ
          // داكن: جُرِّب الداكن في ١٣ سبتمبر ٢٠٢٦ وردَّه المالك — كتلةٌ
          // سوداء فوق بطاقةٍ بيضاء تحت هيدرٍ أسود تجعل الصفحة ثلاثَ طبقاتٍ
          // متنازعة. والفاتحُ يرفع الرأسَ عن باقي البطاقة بلا كتلة.
          Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.topCenter,
            children: <Widget>[
              Container(
                height: _bannerHeight,
                width: double.infinity,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: <Color>[
                      // مسحةٌ زرقاءُ تذوب في الشفّاف لا في أبيضَ صلب: السطحُ
                      // زجاجٌ، وأبيضُ معتمٌ هنا يقطع البطاقةَ نصفين.
                      palette.gold.withValues(alpha: 0.10),
                      palette.gold.withValues(alpha: 0),
                    ],
                  ),
                ),
              ),
              Positioned(
                top: _bannerHeight - _avatarSize / 2,
                child: _Avatar(isCompany: isCompany, palette: palette),
              ),
            ],
          ),
          const SizedBox(height: _avatarSize / 2 + 10),

          // الاسم.
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Text(
              profile.displayName,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: palette.ink,
                fontSize: 20,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.2,
                fontFamily: HarajTheme.fontFamily,
              ),
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
              letterSpacing: 0.4,
              fontFamily: HarajTheme.fontFamily,
            ),
          ),
          const SizedBox(height: 10),

          // شارتان: نوعُ الحساب، والتوثيقُ إن وُجد.
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Wrap(
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
          ),
          const SizedBox(height: 14),

          // خيطٌ يفصل التعريفَ عن الفعل: ما فوقه **من أنت**، وما تحته **ما
          // تفعله**. وبلا فصلٍ يُقرأ زرُّ المحفظة شارةً ثالثة.
          Divider(
            height: 1,
            thickness: 1,
            indent: 16,
            endIndent: 16,
            color: palette.navInactive.withValues(alpha: 0.7),
          ),

          // زرُّ المحفظة البارز — بلون العلامة، والرصيدُ من الخادم.
          Padding(
            padding: const EdgeInsets.all(16),
            child: _WalletButton(balance: balance, palette: palette),
          ),
        ],
      ),
    );
  }
}

/// ارتفاعُ الشريط الداكن في رأس البطاقة، وقطرُ الصورة الرمزيّة — الصورةُ تقف
/// على حافّته بنصفها، فالرقمان يُقرأان معاً ولا يُبدَّل أحدهما وحده.
const double _bannerHeight = 62;
const double _avatarSize = 72;

/// الصورة الرمزيّة: أيقونةُ عميلٍ داخل حلقةٍ ذهبيّة على أرضيّةٍ كحليّة، وحولها
/// طوقٌ بلون البطاقة يفصلها عن الشريط الداكن الذي تقف عليه.
///
/// أيقونةٌ لا حرفان بطلب المالك — رمزٌ واحدٌ للحساب أوضحُ من حرفين يختلفان
/// بكل اسم.
class _Avatar extends StatelessWidget {
  const _Avatar({required this.isCompany, required this.palette});

  final bool isCompany;
  final HarajPalette palette;

  @override
  Widget build(BuildContext context) => Container(
    width: _avatarSize,
    height: _avatarSize,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      shape: BoxShape.circle,
      // أرضيّةٌ فاتحةٌ بمسحةٍ من لون العلامة، لا كحليٌّ صلب: الأيقونةُ هي
      // ما يُرى، والقرصُ الداكن حولها يبتلعها.
      color: Color.alphaBlend(
        palette.gold.withValues(alpha: 0.12),
        palette.cardSurface,
      ),
      border: Border.all(
        color: palette.gold.withValues(alpha: 0.35),
        width: 1.5,
      ),
      boxShadow: <BoxShadow>[
        BoxShadow(
          color: palette.ink.withValues(alpha: 0.10),
          blurRadius: 14,
          offset: const Offset(0, 5),
        ),
      ],
    ),
    child: Icon(
      isCompany ? Icons.business_rounded : Icons.person_rounded,
      color: palette.gold,
      size: 36,
    ),
  );
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
        borderRadius: BorderRadius.circular(14),
        onTap: () => context.goNamed(Routes.wallet),
        // لونٌ واحدٌ لا تدرّج، بارتفاع الأزرار الأساسيّة (٥٠) وتدويرِها (١٤)
        // — زرُّ المحفظة هو الزرُّ الأساسيّ في هذه الشاشة فيلبس زيَّها.
        child: Ink(
          width: double.infinity,
          height: 50,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            color: palette.gold,
            boxShadow: <BoxShadow>[
              BoxShadow(
                color: palette.gold.withValues(alpha: 0.25),
                blurRadius: 14,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          // **الاسمُ في طرفٍ والرصيدُ في الطرف الآخر**، لا الثلاثةُ متراصّةً
          // في الوسط: الرصيدُ هو ما تبحث عنه العينُ هنا، وفي الوسط كان يُقرأ
          // ذيلاً للاسم لا رقماً قائماً بنفسه.
          child: Row(
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
              const Spacer(),
              // الرصيد: شرطةٌ حتى يصل، ثم المبلغ والعملة كما أرسلهما الخادم.
              Directionality(
                textDirection: TextDirection.ltr,
                child: Text(
                  balance == null
                      ? '—'
                      : '${balance!.amount} ${balance!.currency}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.3,
                    fontFamily: HarajTheme.fontFamily,
                  ),
                ),
              ),
              const SizedBox(width: 4),
              const Icon(
                Icons.chevron_left_rounded,
                color: Colors.white70,
                size: 20,
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

/// زخرفةُ البطاقة الزجاجيّة الواحدة في الشاشة — رأسُ الملف ومجموعاتُ القائمة
/// ومحدّدُ اللغة. تصميمُ الزجاج الأبيض بطلب المالك (٣ أكتوبر ٢٠٢٦): سطحٌ شفّافٌ
/// أبيض، وحدٌّ رفيع، وظلٌّ خفيف — وفي مكانٍ واحد كي لا تفترق بطاقةٌ عن أختها.
BoxDecoration _glassCard(HarajPalette palette) => BoxDecoration(
  color: palette.cardSurface,
  borderRadius: BorderRadius.circular(20),
  border: Border.all(color: palette.navInactive.withValues(alpha: 0.7)),
  boxShadow: <BoxShadow>[
    BoxShadow(
      color: palette.ink.withValues(alpha: 0.05),
      blurRadius: 16,
      offset: const Offset(0, 6),
    ),
  ],
);

/// عنوانُ قسمٍ في الصفحة — بخطّ التطبيق ولونِ الحبر، لا `titleMedium` العامّ.
class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Padding(
      padding: const EdgeInsetsDirectional.only(start: 4),
      child: Text(
        text,
        style: TextStyle(
          fontFamily: HarajTheme.fontFamily,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: palette.ink,
        ),
      ),
    );
  }
}

/// بطاقةٌ زجاجيّةٌ تجمع سطورَ القائمة بخيوطٍ رفيعةٍ بينها.
///
/// **القصُّ على البطاقة** لا على السطر: لمسةُ السطر الأوّل والأخير تتبع
/// تدويرَ البطاقة، وبلا قصٍّ تخرج زواياها مربّعةً من الحافّة المدوّرة.
class _MenuCard extends StatelessWidget {
  const _MenuCard({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: _glassCard(palette),
      child: Material(
        color: Colors.transparent,
        child: Column(
          children: <Widget>[
            for (var i = 0; i < children.length; i++) ...<Widget>[
              // الخيطُ يبدأ بعد الأيقونة (١٦ + ٣٨ + ١٤) فيُقرأ فاصلاً بين
              // نصّين لا قطعاً للبطاقة.
              if (i > 0)
                Divider(
                  height: 1,
                  thickness: 1,
                  indent: 68,
                  endIndent: 16,
                  color: palette.navInactive.withValues(alpha: 0.7),
                ),
              children[i],
            ],
          ],
        ),
      ),
    );
  }
}

/// سطرٌ في قائمة «حسابي» — أيقونةٌ في مربّعٍ مدوّرٍ بمسحةٍ زرقاء، ثم الاسم،
/// ثم السهم. **بلا سطحٍ خاصٍّ به**: السطرُ يعيش داخل [_MenuCard]، والبطاقةُ
/// هي السطحُ الوحيد (الزجاج الأبيض، ٣ أكتوبر ٢٠٢٦).
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

  /// عنصرٌ خطِر (تسجيل الخروج) — أيقونتُه حمراء داخل مربّعٍ أحمرَ خفيف، لا
  /// زرقاء، فيُقرأ أنه يُخرج لا أنه خدمة.
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    const dangerColour = Color(0xFFB42335);
    final accent = danger ? dangerColour : palette.gold;
    return InkWell(
      onTap: onTap,
      // لمسةٌ خافتةٌ بلون الحبر لا ملوّنة — السطحُ زجاجٌ، والتلوينُ يعكّره.
      hoverColor: palette.ink.withValues(alpha: 0.03),
      splashColor: palette.ink.withValues(alpha: 0.04),
      highlightColor: palette.ink.withValues(alpha: 0.03),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(
          children: <Widget>[
            Container(
              width: 38,
              height: 38,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: accent, size: 20),
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
            // **`chevron_right`** بطلب المالك: يشير نحو النصّ لا بعيداً عنه.
            // وبحبرٍ خافتٍ كي لا ينازع الأيقونةَ البادئة.
            Icon(
              Icons.chevron_right_rounded,
              size: 22,
              color: palette.inkMuted.withValues(alpha: 0.7),
            ),
          ],
        ),
      ),
    );
  }
}

/// تنبيهُ «أكمل تسجيلك» أعلى الصفحة — بطاقةٌ زجاجيّة بحدٍّ ومسحةٍ من لون
/// الخطأ، لا كتلةُ `errorContainer` صلبة تقطع الخلفيّة.
class _RegistrationBanner extends StatelessWidget {
  const _RegistrationBanner({required this.text, required this.onTap});

  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = HarajPalette.of(context);
    final error = Theme.of(context).colorScheme.error;
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: _glassCard(palette).copyWith(
        color: Color.alphaBlend(
          error.withValues(alpha: 0.06),
          palette.cardSurface,
        ),
        border: Border.all(color: error.withValues(alpha: 0.30)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: <Widget>[
                Container(
                  width: 38,
                  height: 38,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: error.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    Icons.assignment_late_outlined,
                    color: error,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    text,
                    style: TextStyle(
                      fontFamily: HarajTheme.fontFamily,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                      height: 1.5,
                      color: palette.ink,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Icon(Icons.chevron_left_rounded, color: error, size: 22),
              ],
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
    // في بطاقةٍ زجاجيّةٍ كبقيّة الصفحة (٣ أكتوبر ٢٠٢٦): أزرارٌ معلّقةٌ على
    // الخلفيّة المتدرّجة بلا وعاءٍ تبدو طافيةً لا تنتمي إلى شيء.
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _glassCard(palette),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            l10n.accountLanguageSection,
            style: TextStyle(
              fontFamily: HarajTheme.fontFamily,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: palette.ink,
            ),
          ),
          const SizedBox(height: 12),
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
      ),
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
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        // المختارةُ بلون العلامة صلباً، والبقيّةُ زجاجٌ بحدٍّ رفيع — لونٌ
        // واحدٌ لا تدرّج، كبقيّة أزرار التصميم.
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 11),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: active ? palette.gold : palette.cardSurface,
            border: Border.all(
              color: active
                  ? palette.gold
                  : palette.navInactive.withValues(alpha: 0.7),
            ),
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
    // كلُّ شعارٍ في دائرةٍ زجاجيّةٍ صغيرة (٣ أكتوبر ٢٠٢٦): الشعاراتُ العاريةُ
    // على الخلفيّة المتدرّجة تبدو مبعثرة، والدوائرُ تجعلها صفّاً واحداً.
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        for (final icon in _icons)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5),
            child: Container(
              width: 40,
              height: 40,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: palette.cardSurface,
                border: Border.all(
                  color: palette.navInactive.withValues(alpha: 0.7),
                ),
              ),
              child: Icon(icon, size: 17, color: palette.inkMuted),
            ),
          ),
      ],
    );
  }
}
