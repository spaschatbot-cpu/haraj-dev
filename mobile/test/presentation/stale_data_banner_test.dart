import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/presentation/common/stale_data_banner.dart';

import '../support/pump_localized.dart';

/// معيار H5 — «قطع الشبكة يعرض البيانات القديمة **والعلامة**».
void main() {
  testWidgets('البيانات الطازجة بلا علامة', (tester) async {
    await pumpLocalized(
      tester,
      StaleDataBanner(
        snapshot: Snapshot<String>.fresh(
          'قيمة',
          at: DateTime.utc(2026, 9, 1, 7),
        ),
      ),
    );

    expect(find.textContaining('آخر تحديث'), findsNothing);
  });

  testWidgets('البيانات المحفوظة تظهر بعلامة وبتوقيت سعودي', (tester) async {
    // 07:00 UTC = 10:00 في السعودية (UTC+3، بلا توقيت صيفي).
    await pumpLocalized(
      tester,
      StaleDataBanner(
        snapshot: Snapshot<String>.cached(
          'قيمة',
          storedAt: DateTime.utc(2026, 9, 1, 7),
        ),
      ),
    );

    expect(find.textContaining('آخر تحديث'), findsOneWidget);
    expect(find.textContaining('10:00'), findsOneWidget);
  });
}
