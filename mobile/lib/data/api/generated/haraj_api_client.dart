// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';

import 'clients/auctions_api.dart';
import 'clients/auth_api.dart';
import 'clients/bids_api.dart';
import 'clients/devices_api.dart';
import 'clients/favourites_api.dart';
import 'clients/invoices_api.dart';
import 'clients/live_api.dart';
import 'clients/participations_api.dart';
import 'clients/payments_api.dart';
import 'clients/profile_api.dart';
import 'clients/purchases_api.dart';
import 'clients/vehicles_api.dart';
import 'clients/wallet_api.dart';

/// Haraj One API `v2.0.0`
class HarajApiClient {
  HarajApiClient(Dio dio, {String? baseUrl}) : _dio = dio, _baseUrl = baseUrl;

  final Dio _dio;
  final String? _baseUrl;

  static String get version => '2.0.0';

  AuctionsApi? _auctions;
  AuthApi? _auth;
  BidsApi? _bids;
  DevicesApi? _devices;
  FavouritesApi? _favourites;
  InvoicesApi? _invoices;
  LiveApi? _live;
  ParticipationsApi? _participations;
  PaymentsApi? _payments;
  ProfileApi? _profile;
  PurchasesApi? _purchases;
  VehiclesApi? _vehicles;
  WalletApi? _wallet;

  AuctionsApi get auctions =>
      _auctions ??= AuctionsApi(_dio, baseUrl: _baseUrl);

  AuthApi get auth => _auth ??= AuthApi(_dio, baseUrl: _baseUrl);

  BidsApi get bids => _bids ??= BidsApi(_dio, baseUrl: _baseUrl);

  DevicesApi get devices => _devices ??= DevicesApi(_dio, baseUrl: _baseUrl);

  FavouritesApi get favourites =>
      _favourites ??= FavouritesApi(_dio, baseUrl: _baseUrl);

  InvoicesApi get invoices =>
      _invoices ??= InvoicesApi(_dio, baseUrl: _baseUrl);

  LiveApi get live => _live ??= LiveApi(_dio, baseUrl: _baseUrl);

  ParticipationsApi get participations =>
      _participations ??= ParticipationsApi(_dio, baseUrl: _baseUrl);

  PaymentsApi get payments =>
      _payments ??= PaymentsApi(_dio, baseUrl: _baseUrl);

  ProfileApi get profile => _profile ??= ProfileApi(_dio, baseUrl: _baseUrl);

  PurchasesApi get purchases =>
      _purchases ??= PurchasesApi(_dio, baseUrl: _baseUrl);

  VehiclesApi get vehicles =>
      _vehicles ??= VehiclesApi(_dio, baseUrl: _baseUrl);

  WalletApi get wallet => _wallet ??= WalletApi(_dio, baseUrl: _baseUrl);
}
