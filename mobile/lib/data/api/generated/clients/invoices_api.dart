// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/invoice.dart';
import '../models/paginated_invoice_list.dart';

part 'invoices_api.g.dart';

@RestApi()
abstract class InvoicesApi {
  factory InvoicesApi(Dio dio, {String? baseUrl}) = _InvoicesApi;

  /// [limit] - عدد النتائج التي يجب إرجاعها في كل صفحة.
  ///
  /// [offset] - الفهرس الأولي الذي يجب البدء منه لإرجاع النتائج.
  @GET('/api/v1/invoices/')
  Future<PaginatedInvoiceList> v1InvoicesList({
    @Query('limit') int? limit,
    @Query('offset') int? offset,
  });

  @GET('/api/v1/invoices/{id}/')
  Future<Invoice> v1InvoicesRetrieve({@Path('id') required int id});

  /// سداد فاتورة من الرصيد (مغلق).
  ///
  /// `POST /api/v1/invoices/{id}/pay/` — **مغلقٌ بقرار المالك.** T954.
  ///
  /// ## القاعدة.
  ///
  /// «رصيد التأمين لا يمكن، وممنوع السداد منه للفواتير. بعد سداد فاتورة.
  /// العربية يقدر يسترد التأمين» — المالك، ١٩ سبتمبر ٢٠٢٦.
  ///
  /// وهي المادةُ السادسة بنصّها: «مبلغ الضمان … **لا يُحتسب من ثمن المركبة**».
  /// وكان هذا البابُ يحتسبه: `pay_invoice_from_balance` يصرف قفلَ الفاتورة ثمّ.
  /// الرصيدَ الحرّ، فيخرج الضمانُ ثمناً للسيّارة — وهو ما يمنعه العقد.
  ///
  /// ## والفاتورةُ تحويلٌ بنكيٌّ وحدَه.
  ///
  /// يسجّلها `record_payment` حين يؤكّد البنكُ الحوالة عبر أودو. ولا يُفقَد.
  /// شيء: الرهنُ على الفاتورة (`HoldReason.DUES`) يتقلّص مع كلّ دفعةٍ حتى.
  /// الصفر (`_shrink_dues_claims`)، فيعود التأمينُ إلى `insurance_free` بعد.
  /// السداد الكامل — **وعندها** يطلب العميلُ استردادَه. وهو ترتيبُ المالك.
  /// نفسُه، ويعمل اليوم بلا تعديل.
  ///
  /// ## ولماذا ردٌّ لا حذفُ مسار.
  ///
  /// تطبيقٌ على جوّالٍ لم يُحدَّث سيضغط «ادفع» غداً. و404 يُقرأ عطلاً فيُعاد.
  /// ويُتّصل بالدعم؛ ورفضٌ برسالةٍ عربيّةٍ يقول **لماذا** وماذا يفعل بدلاً.
  /// منه. ويُحذف المسارُ يوم لا يبقى إصدارٌ يعرفه.
  @Deprecated('This method is marked as deprecated')
  @POST('/api/v1/invoices/{id}/pay/')
  Future<void> v1InvoicesPayCreate({@Path('id') required int id});
}
