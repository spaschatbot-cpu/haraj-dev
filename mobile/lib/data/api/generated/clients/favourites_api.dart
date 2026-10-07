// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/vehicle_page.dart';

part 'favourites_api.g.dart';

@RestApi()
abstract class FavouritesApi {
  factory FavouritesApi(Dio dio, {String? baseUrl}) = _FavouritesApi;

  /// المفضّلة.
  ///
  /// `GET /api/v1/favourites/` — the cars this customer marked, newest first.
  ///
  /// Rendered through `cards.vehicle_card`, like every other list of vehicles in.
  /// the product: a favourites screen that assembled its own row would be the.
  /// second card builder `ops/checks/one_vehicle_card.py` exists to refuse, and.
  /// the field that went missing from it would be missing only here.
  ///
  /// The visibility rule still applies. A car marked while it was listed and.
  /// since withdrawn is not shown — a favourite is a bookmark, never a claim, and.
  /// it does not grant sight of a row its owner may no longer see.
  @GET('/api/v1/favourites/')
  Future<VehiclePage> favouritesList({
    @Query('limit') int? limit = 20,
    @Query('offset') int? offset = 0,
  });

  /// إضافة إلى المفضّلة.
  ///
  /// `PUT` and `DELETE /api/v1/favourites/{id}/` — mark and unmark.
  ///
  /// `PUT`, not `POST`, and both are idempotent: marking twice is marking once,.
  /// and unmarking something unmarked is not an error. That is what a.
  /// double-tapped heart and a retried request produce, and «هذه المركبة في.
  /// مفضّلتك بالفعل» is a refusal for a thing that already happened the way the.
  /// customer wanted.
  ///
  /// Both answer `204`. There is nothing to return — the client already knows.
  /// which car it asked about, and a body here would be a second place the mark's.
  /// shape is described.
  @PUT('/api/v1/favourites/{id}/')
  Future<void> favouritesMark({@Path('id') required int id});

  /// إزالة من المفضّلة.
  ///
  /// `PUT` and `DELETE /api/v1/favourites/{id}/` — mark and unmark.
  ///
  /// `PUT`, not `POST`, and both are idempotent: marking twice is marking once,.
  /// and unmarking something unmarked is not an error. That is what a.
  /// double-tapped heart and a retried request produce, and «هذه المركبة في.
  /// مفضّلتك بالفعل» is a refusal for a thing that already happened the way the.
  /// customer wanted.
  ///
  /// Both answer `204`. There is nothing to return — the client already knows.
  /// which car it asked about, and a body here would be a second place the mark's.
  /// shape is described.
  @DELETE('/api/v1/favourites/{id}/')
  Future<void> favouritesUnmark({@Path('id') required int id});
}
