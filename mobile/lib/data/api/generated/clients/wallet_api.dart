// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/paginated_ledger_entry_list.dart';
import '../models/payment_intent.dart';
import '../models/refund_request.dart';
import '../models/wallet.dart';

part 'wallet_api.g.dart';

@RestApi()
abstract class WalletApi {
  factory WalletApi(Dio dio, {String? baseUrl}) = _WalletApi;

  /// The customer's money, split by the pot it is actually sitting in.
  @GET('/api/v1/wallet/')
  Future<Wallet> v1WalletRetrieve();

  @GET('/api/v1/wallet/refund-requests/')
  Future<List<RefundRequest>> v1WalletRefundRequestsList();

  @MultiPart()
  @POST('/api/v1/wallet/refund-requests/')
  Future<RefundRequest> v1WalletRefundRequestsCreate({
    @Part(name: 'amount') required String amount,
  });

  /// Start a card top-up, or list the ones this customer started.
  @GET('/api/v1/wallet/topups/')
  Future<List<PaymentIntent>> v1WalletTopupsList();

  /// Start a card top-up, or list the ones this customer started.
  @MultiPart()
  @POST('/api/v1/wallet/topups/')
  Future<PaymentIntent> v1WalletTopupsCreate({
    @Part(name: 'auction') int? auction,
  });

  /// Where the customer lands on return from the gateway.
  ///
  /// It reads one stored row and answers with it. Not a single query parameter is.
  /// consulted — a return URL is under the payer's thumb, and in v1 that was.
  /// enough to make the app believe a payment had succeeded. Money moves in.
  /// :class:`PaymentCallbackView` and nowhere else.
  @GET('/api/v1/wallet/topups/{reference}/')
  Future<PaymentIntent> v1WalletTopupsRetrieve({
    @Path('reference') required String reference,
  });

  /// Hand the customer over to the gateway. One hop, decided on the server.
  ///
  /// A redirect and not a JSON body carrying a url: the client's whole job is to.
  /// send the customer here, and a `302` is what a browser and a webview both.
  /// already know how to follow. It also means the gateway's address never.
  /// reaches either client, which is the point of `apps.money.gateway` — see the.
  /// module docstring for why a "gateway url" field would have been the wrong.
  /// shape.
  ///
  /// Nothing is charged here and no money moves. This is a signpost; the ledger.
  /// is touched by :class:`PaymentCallbackView` and by nothing else.
  @GET('/api/v1/wallet/topups/{reference}/checkout/')
  Future<void> v1WalletTopupsCheckoutRetrieve({
    @Path('reference') required String reference,
  });

  /// Every ledger line belonging to the caller, newest first, paginated.
  ///
  /// [limit] - عدد النتائج التي يجب إرجاعها في كل صفحة.
  ///
  /// [offset] - الفهرس الأولي الذي يجب البدء منه لإرجاع النتائج.
  @GET('/api/v1/wallet/transactions/')
  Future<PaginatedLedgerEntryList> v1WalletTransactionsList({
    @Query('limit') int? limit,
    @Query('offset') int? offset,
  });
}
