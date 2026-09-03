import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/profile/entities/customer_profile.dart';
import '../../l10n/generated/app_localizations.dart';
import '../auth/session_controller.dart';
import '../common/failure_view.dart';
import '../common/stale_data_banner.dart';
import 'profile_controller.dart';
import 'widgets/locked_field_row.dart';

/// الملف الشخصي: عرض وتعديل، والهوية، وبوابتا الشركة وتغيير الجوال.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final profile = ref.watch(profileControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.profileTitle),
        actions: [
          IconButton(
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).signOut(),
            tooltip: l10n.profileSignOut,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
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

class _ProfileBody extends ConsumerStatefulWidget {
  const _ProfileBody({required this.snapshot});

  final Snapshot<CustomerProfile> snapshot;

  @override
  ConsumerState<_ProfileBody> createState() => _ProfileBodyState();
}

class _ProfileBodyState extends ConsumerState<_ProfileBody> {
  late final TextEditingController _fullName;
  late final TextEditingController _email;
  late final TextEditingController _nationalId;

  bool _busy = false;
  Failure? _failure;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    final profile = widget.snapshot.value;
    _fullName = TextEditingController(text: profile.fullName);
    _email = TextEditingController(text: profile.email);
    _nationalId = TextEditingController(text: profile.nationalId);
  }

  @override
  void dispose() {
    _fullName.dispose();
    _email.dispose();
    _nationalId.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _failure = null;
      _saved = false;
    });
    try {
      await action();
      if (mounted) setState(() => _saved = true);
    } on Failure catch (failure) {
      // رسالة الخادم كما جاءت، والنموذج المملوء يبقى كما هو ليصحّح المستخدم.
      if (mounted) setState(() => _failure = failure);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final profile = widget.snapshot.value;
    final controller = ref.read(profileControllerProvider.notifier);
    final phoneLock = profile.lockOn(ProfileFields.phone);
    final nationalIdLock = profile.lockOn(ProfileFields.nationalId);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        StaleDataBanner(snapshot: widget.snapshot),
        Text(
          profile.displayName,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 16),

        TextField(
          controller: _fullName,
          decoration: InputDecoration(labelText: l10n.profileFullName),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _email,
          keyboardType: TextInputType.emailAddress,
          decoration: InputDecoration(labelText: l10n.profileEmail),
        ),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: _busy
              ? null
              : () => _run(
                  () => controller.save(
                    fullName: _fullName.text.trim(),
                    email: _email.text.trim(),
                  ),
                ),
          child: Text(l10n.profileSave),
        ),

        const Divider(height: 32),

        if (phoneLock != null)
          LockedFieldRow(
            label: l10n.profilePhone,
            value: profile.phone,
            lock: phoneLock,
          ),

        // زرّ التغيير موجود مع القفل لا بدلاً منه: القفل يقول «ليس هنا»،
        // والسبب القادم من الخادم يقول أين.
        TextButton.icon(
          onPressed: () => context.goNamed(Routes.changePhone),
          icon: const Icon(Icons.sync_alt),
          label: Text(l10n.profileChangePhone),
        ),

        const Divider(height: 32),

        if (nationalIdLock != null)
          LockedFieldRow(
            label: l10n.profileNationalId,
            value: profile.nationalId,
            lock: nationalIdLock,
          )
        else ...[
          // غير مقفول = إمّا لم يُدخل بعد وإمّا أُدخل خطأً. الحالتان تُصحَّحان
          // من هنا (T606)، ولا تُحوَّلان إلى مكالمة مع الدعم كما في v1.
          TextField(
            controller: _nationalId,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: l10n.profileNationalId,
              hintText: l10n.profileNationalIdMissing,
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.tonal(
            onPressed: _busy
                ? null
                : () => _run(
                    () => controller.pinNationalId(_nationalId.text.trim()),
                  ),
            child: Text(l10n.profileNationalIdSave),
          ),
        ],

        const Divider(height: 32),

        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(l10n.profileCompanySection),
          subtitle: Text(_companyStatus(l10n, profile)),
          trailing: const Icon(Icons.chevron_left),
          onTap: () => context.goNamed(Routes.companyProfile),
        ),

        if (_busy) ...[
          const SizedBox(height: 16),
          const Center(child: CircularProgressIndicator()),
        ],
        if (_failure != null) ...[
          const SizedBox(height: 16),
          FailureView(failure: _failure!),
        ],
        if (_saved && _failure == null) ...[
          const SizedBox(height: 16),
          Text(l10n.profileSaved, textAlign: TextAlign.center),
        ],
      ],
    );
  }

  String _companyStatus(AppLocalizations l10n, CustomerProfile profile) {
    if (!profile.hasCompanyProfile) return l10n.profileCompanyMissing;
    return profile.companyProfileComplete
        ? l10n.profileCompanyComplete
        : l10n.profileCompanyIncomplete;
  }
}
