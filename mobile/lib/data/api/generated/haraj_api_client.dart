// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';

import 'clients/auth_api.dart';
import 'clients/profile_api.dart';
import 'clients/auctions_api.dart';
import 'clients/vehicles_api.dart';
import 'clients/bids_api.dart';
import 'clients/live_api.dart';
import 'clients/wallet_api.dart';
import 'clients/invoices_api.dart';
import 'clients/devices_api.dart';

/// حراج واحد — API العميل (مخطط مؤقّت) `v0.0.0-mock`.
///
/// مخطط تمثيلي لبذرة تطبيق Flutter. يُستبدل بمخطط الخادم المثبَّت في T621.
///
class HarajApiClient {
  HarajApiClient(Dio dio, {String? baseUrl}) : _dio = dio, _baseUrl = baseUrl;

  final Dio _dio;
  final String? _baseUrl;

  static String get version => '0.0.0-mock';

  AuthApi? _auth;
  ProfileApi? _profile;
  AuctionsApi? _auctions;
  VehiclesApi? _vehicles;
  BidsApi? _bids;
  LiveApi? _live;
  WalletApi? _wallet;
  InvoicesApi? _invoices;
  DevicesApi? _devices;

  AuthApi get auth => _auth ??= AuthApi(_dio, baseUrl: _baseUrl);

  ProfileApi get profile => _profile ??= ProfileApi(_dio, baseUrl: _baseUrl);

  AuctionsApi get auctions =>
      _auctions ??= AuctionsApi(_dio, baseUrl: _baseUrl);

  VehiclesApi get vehicles =>
      _vehicles ??= VehiclesApi(_dio, baseUrl: _baseUrl);

  BidsApi get bids => _bids ??= BidsApi(_dio, baseUrl: _baseUrl);

  LiveApi get live => _live ??= LiveApi(_dio, baseUrl: _baseUrl);

  WalletApi get wallet => _wallet ??= WalletApi(_dio, baseUrl: _baseUrl);

  InvoicesApi get invoices =>
      _invoices ??= InvoicesApi(_dio, baseUrl: _baseUrl);

  DevicesApi get devices => _devices ??= DevicesApi(_dio, baseUrl: _baseUrl);
}
