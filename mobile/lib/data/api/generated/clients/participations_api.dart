// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/participation_page.dart';

part 'participations_api.g.dart';

@RestApi()
abstract class ParticipationsApi {
  factory ParticipationsApi(Dio dio, {String? baseUrl}) = _ParticipationsApi;

  /// مشاركاتي.
  ///
  /// `GET /api/v1/participations/` — the auctions the caller is in.
  ///
  /// One row per auction, carrying the two facts a «مشاركاتي» screen needs and.
  /// cannot combine for itself: how many of the caller's bids still stand, and.
  /// what their deposit for that auction is doing.
  ///
  /// Why the server and not the screen.
  /// ---------------------------------.
  /// Both halves exist separately — `bids/mine/` and the wallet — and the app.
  /// could in principle match one against the other. It must not. That match is a.
  /// rule, and a rule in a screen is a second copy of a rule (Article 4-5): the.
  /// day a hold is released or consumed while the bid rows stay exactly as they.
  /// were, the screen's «محجوز» and the ledger's disagree, and the customer is.
  /// told two different things about one deposit. The hold is the only thing that.
  /// knows, so the hold is what this reads.
  ///
  /// Being *in* an auction is either half on its own: a standing bid, or money.
  /// pinned to it. A bidder whose deposit is held but whose only bid was.
  /// withdrawn is still in — otherwise their wallet shows 10,000 محجوز against a.
  /// list that shows nothing holding it.
  ///
  /// No eligibility is decided here and none is read. This says what is, not what.
  /// may be; `check_eligibility` remains the one door (T502).
  @GET('/api/v1/participations/')
  Future<ParticipationPage> participationsMine({
    @Query('limit') int? limit = 20,
    @Query('offset') int? offset = 0,
  });
}
