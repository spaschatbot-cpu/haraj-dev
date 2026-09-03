import 'package:haraj_mobile/data/api/generated/clients/profile_api.dart';
import 'package:haraj_mobile/data/api/generated/models/company_profile.dart';
import 'package:haraj_mobile/data/api/generated/models/company_profile_read.dart';
import 'package:haraj_mobile/data/api/generated/models/national_id.dart';
import 'package:haraj_mobile/data/api/generated/models/patched_profile_update.dart';
import 'package:haraj_mobile/data/api/generated/models/profile.dart';

/// خادم ملف شخصي صوري فوق الواجهة **المولَّدة**.
final class FakeProfileApi implements ProfileApi {
  FakeProfileApi({this.profile, this.company});

  Profile? profile;
  CompanyProfileRead? company;

  /// عطب يُرمى بدل الردّ — لاختبار السقوط إلى الكاش ومرور رسالة الخادم.
  Object? failure;

  final List<Object> bodies = <Object>[];

  @override
  Future<Profile> profileRetrieve() async {
    if (failure != null) throw failure!;
    return profile!;
  }

  @override
  Future<Profile> profileUpdate({required PatchedProfileUpdate body}) async {
    bodies.add(body);
    if (failure != null) throw failure!;
    return profile!;
  }

  @override
  Future<Profile> profileSetNationalId({required NationalId body}) async {
    bodies.add(body);
    if (failure != null) throw failure!;
    return profile!;
  }

  @override
  Future<CompanyProfileRead> profileCompanyRetrieve() async {
    if (failure != null) throw failure!;
    return company!;
  }

  @override
  Future<CompanyProfileRead> profileCompanySave({
    required CompanyProfile body,
  }) async {
    bodies.add(body);
    if (failure != null) throw failure!;
    return company!;
  }
}
