import 'dart:convert';

import '../../domain/catalog/entities/vehicle_query.dart';
import '../../domain/catalog/repositories/favourites_repository.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../api/api_call.dart';
import '../api/generated/clients/favourites_api.dart';
import '../api/generated/models/vehicle_page.dart' as api;
import '../local/cache/response_cache.dart';
import 'catalog_mapper.dart';

/// المفضلة: الخادم أولاً، والكاش شبكة أمان عند **صمت** الخادم وحده — نفس قرار
/// `CatalogRepositoryImpl` حرفاً بحرف، ولنفس السبب.
final class FavouritesRepositoryImpl implements FavouritesRepository {
  FavouritesRepositoryImpl({
    required FavouritesApi api,
    required ResponseCache cache,
    DateTime Function()? clock,
  }) : _api = api,
       _cache = cache,
       _clock = clock ?? DateTime.now;

  /// حجم الصفحة يُرسَل صراحةً كي لا يكون التمرير رهناً بافتراضٍ في الخادم.
  static const int pageSize = 20;

  final FavouritesApi _api;
  final ResponseCache _cache;
  final DateTime Function() _clock;

  @override
  Future<Snapshot<VehiclePage>> loadFavourites({int page = 1}) async {
    try {
      final response = await callApi(
        () =>
            _api.favouritesList(limit: pageSize, offset: (page - 1) * pageSize),
      );

      final fetchedAt = _clock().toUtc();
      if (page == 1) {
        await _cache.write(
          CacheKeys.favourites,
          jsonEncode(response.toJson()),
          fetchedAtUtc: fetchedAt,
        );
      }
      return Snapshot.fresh(response.toPage(), at: fetchedAt);
    } on TransportFailure {
      // الصفحة الأولى وحدها محفوظة، فما بعدها لا جواب له بلا خادم.
      if (page != 1) rethrow;
      final cached = await _readCache();
      if (cached != null) return cached;
      rethrow;
    }
  }

  @override
  Future<void> mark(String vehicleId) =>
      callApi(() => _api.favouritesMark(id: _idOf(vehicleId)));

  @override
  Future<void> unmark(String vehicleId) =>
      callApi(() => _api.favouritesUnmark(id: _idOf(vehicleId)));

  Future<Snapshot<VehiclePage>?> _readCache() async {
    final document = await _cache.read(CacheKeys.favourites);
    if (document == null) return null;
    try {
      final page = api.VehiclePage.fromJson(document.decode());
      return Snapshot.cached(page.toPage(), storedAt: document.fetchedAtUtc);
    } on Object {
      // كاشٌ من نسخة مخطط أقدم لم يعد يُفكّ: يُعامل كغياب كاش، لا كعطب.
      return null;
    }
  }

  /// المعرّف نصٌّ في النطاق ورقمٌ على السلك.
  static int _idOf(String value) =>
      int.tryParse(value) ?? (throw ArgumentError.value(value, 'vehicleId'));
}
