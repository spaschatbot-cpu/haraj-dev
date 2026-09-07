import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:yaml/yaml.dart';

/// قسما المصادقة والملف الشخصي في المخطط المؤقّت **نسخة من عقد الخادم**.
///
/// المخطط المؤقّت (`openapi/haraj-mock.yaml`) موجود ليعمل خط التوليد قبل تثبيت
/// T621، وخطره المعروف أنه يخترع: مسار لا وجود له، أو حقل باسم آخر، فتُبنى
/// شاشة على عقد لا يقابله شيء عند الخادم — ولا يظهر ذلك إلا بعد الشحن.
///
/// شاشات T706 و T715 مبنيّة على المسارات الثمانية أدناه، وهذه موجودة اليوم في
/// `backend/openapi/schema.yaml` المثبَّت. فالاختبار يقارن الاثنين: أي انحراف —
/// عندنا أو عند الخادم — يسقط هنا لا عند المستخدم. وحين يأتي T621 يصير التبديل
/// بلا أثر على شيفرة التطبيق، لأن الأسماء واحدة أصلاً.
void main() {
  final serverSchema = File('../backend/openapi/schema.yaml');

  YamlMap load(File file) => loadYaml(file.readAsStringSync()) as YamlMap;

  /// المسارات التي تستهلكها شاشات المجموعة ب من هذا الفرع، بأسماء عملياتها.
  const mirroredOperations = <String, String>{
    '/api/v1/auth/code/': 'v1_auth_code_create',
    '/api/v1/auth/verify/': 'v1_auth_verify_create',
    '/api/v1/auth/refresh/': 'v1_auth_refresh_create',
    '/api/v1/auth/phone/change/': 'v1_auth_phone_change_create',
    '/api/v1/auth/phone/change/confirm/': 'v1_auth_phone_change_confirm_create',
    '/api/v1/profile/': 'profile_retrieve',
    '/api/v1/profile/national-id/': 'profile_set_national_id',
    '/api/v1/profile/company/': 'profile_company_retrieve',
  };

  /// النماذج المشتركة بين الطرفين — كل ما تمرّ به شاشتا الدخول والملف.
  const mirroredSchemas = <String>[
    'SendCode',
    'SendCodeResponse',
    'VerifyCode',
    'TokenPair',
    'AuthenticatedUser',
    'Refresh',
    'StartPhoneChange',
    'StartPhoneChangeResponse',
    'ConfirmPhoneChange',
    'Profile',
    'PatchedProfileUpdate',
    'NationalId',
    'CompanyProfile',
    'CompanyProfileRead',
    'LockedField',
  ];

  test('مخطط الخادم المثبَّت موجود ليُقارَن به', () {
    expect(
      serverSchema.existsSync(),
      isTrue,
      reason: 'بلا مخطط الخادم لا معنى لمقارنة، ولا حارس على الاختراع',
    );
  });

  test('كل مسار مصادقة أو ملف شخصي موجود عند الخادم بنفس اسم عمليته', () {
    final mock = load(File('openapi/haraj-mock.yaml'))['paths'] as YamlMap;
    final server = load(serverSchema)['paths'] as YamlMap;

    for (final entry in mirroredOperations.entries) {
      final mockPath = mock[entry.key] as YamlMap?;
      expect(mockPath, isNotNull, reason: 'مسار ناقص محلياً: ${entry.key}');

      final serverPath = server[entry.key] as YamlMap?;
      expect(
        serverPath,
        isNotNull,
        reason: 'مسار لا وجود له عند الخادم: ${entry.key}',
      );

      for (final method in mockPath!.keys) {
        expect(
          serverPath!.containsKey(method),
          isTrue,
          reason: 'طريقة $method على ${entry.key} غير موجودة عند الخادم',
        );
        expect(
          (serverPath[method] as YamlMap)['operationId'],
          (mockPath[method] as YamlMap)['operationId'],
          reason:
              'اسم العملية يقرّر اسم الدالة المولَّدة؛ اختلافه يعني إعادة كتابة '
              'الشيفرة عند التبديل (${entry.key} $method)',
        );
      }
    }
  });

  test('نماذج المصادقة والملف تحمل نفس الحقول ونفس الإلزام', () {
    YamlMap schemasOf(File file) =>
        (load(file)['components'] as YamlMap)['schemas'] as YamlMap;

    final mock = schemasOf(File('openapi/haraj-mock.yaml'));
    final server = schemasOf(serverSchema);

    Set<String> namesOf(YamlMap? map) =>
        (map?['properties'] as YamlMap?)?.keys.cast<String>().toSet() ??
        <String>{};

    Set<String> requiredOf(YamlMap? map) =>
        (map?['required'] as YamlList?)?.cast<String>().toSet() ?? <String>{};

    for (final name in mirroredSchemas) {
      final ours = mock[name] as YamlMap?;
      final theirs = server[name] as YamlMap?;
      expect(ours, isNotNull, reason: 'نموذج ناقص محلياً: $name');
      expect(theirs, isNotNull, reason: 'نموذج لا وجود له عند الخادم: $name');

      expect(
        namesOf(ours),
        namesOf(theirs),
        reason: 'حقول $name تختلف عن الخادم — حقل مخترَع أو حقل فات علينا',
      );
      expect(
        requiredOf(ours),
        requiredOf(theirs),
        reason:
            'الإلزام في $name يختلف: حقل إلزامي عندهم واختياري عندنا يعني '
            'نموذجاً مولَّداً يقبل `null` حيث لا يأتي `null` أبداً — والعكس '
            'يُسقط الاستجابة كاملة',
      );
    }
  });
}
