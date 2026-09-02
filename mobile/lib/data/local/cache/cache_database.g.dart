// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cache_database.dart';

// ignore_for_file: type=lint
class $CachedDocumentsTable extends CachedDocuments
    with TableInfo<$CachedDocumentsTable, CachedDocumentRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedDocumentsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
    'key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadMeta = const VerificationMeta(
    'payload',
  );
  @override
  late final GeneratedColumn<String> payload = GeneratedColumn<String>(
    'payload',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _fetchedAtUtcMillisMeta =
      const VerificationMeta('fetchedAtUtcMillis');
  @override
  late final GeneratedColumn<int> fetchedAtUtcMillis = GeneratedColumn<int>(
    'fetched_at_utc_millis',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [key, payload, fetchedAtUtcMillis];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_documents';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedDocumentRow> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(
        _keyMeta,
        key.isAcceptableOrUnknown(data['key']!, _keyMeta),
      );
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('payload')) {
      context.handle(
        _payloadMeta,
        payload.isAcceptableOrUnknown(data['payload']!, _payloadMeta),
      );
    } else if (isInserting) {
      context.missing(_payloadMeta);
    }
    if (data.containsKey('fetched_at_utc_millis')) {
      context.handle(
        _fetchedAtUtcMillisMeta,
        fetchedAtUtcMillis.isAcceptableOrUnknown(
          data['fetched_at_utc_millis']!,
          _fetchedAtUtcMillisMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_fetchedAtUtcMillisMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  CachedDocumentRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedDocumentRow(
      key: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}key'],
      )!,
      payload: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload'],
      )!,
      fetchedAtUtcMillis: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}fetched_at_utc_millis'],
      )!,
    );
  }

  @override
  $CachedDocumentsTable createAlias(String alias) {
    return $CachedDocumentsTable(attachedDatabase, alias);
  }
}

class CachedDocumentRow extends DataClass
    implements Insertable<CachedDocumentRow> {
  final String key;

  /// جسم الاستجابة كما وصل، نصّاً — لا نموذج مفكوك: الكاش لا يعرف الشكل، فلا
  /// يحتاج ترحيلاً كلما تغيّر المخطط.
  final String payload;

  /// عدد الميلي ثانية منذ Epoch **بتوقيت UTC**.
  ///
  /// عدد صريح لا `DateTime`: عمود التاريخ في drift يُقرأ بتوقيت الجهاز
  /// افتراضياً، والمادة ٣-١ تمنع مقارنة عمودين أحدهما محوَّل والآخر لا.
  final int fetchedAtUtcMillis;
  const CachedDocumentRow({
    required this.key,
    required this.payload,
    required this.fetchedAtUtcMillis,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['payload'] = Variable<String>(payload);
    map['fetched_at_utc_millis'] = Variable<int>(fetchedAtUtcMillis);
    return map;
  }

  CachedDocumentsCompanion toCompanion(bool nullToAbsent) {
    return CachedDocumentsCompanion(
      key: Value(key),
      payload: Value(payload),
      fetchedAtUtcMillis: Value(fetchedAtUtcMillis),
    );
  }

  factory CachedDocumentRow.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedDocumentRow(
      key: serializer.fromJson<String>(json['key']),
      payload: serializer.fromJson<String>(json['payload']),
      fetchedAtUtcMillis: serializer.fromJson<int>(json['fetchedAtUtcMillis']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'key': serializer.toJson<String>(key),
      'payload': serializer.toJson<String>(payload),
      'fetchedAtUtcMillis': serializer.toJson<int>(fetchedAtUtcMillis),
    };
  }

  CachedDocumentRow copyWith({
    String? key,
    String? payload,
    int? fetchedAtUtcMillis,
  }) => CachedDocumentRow(
    key: key ?? this.key,
    payload: payload ?? this.payload,
    fetchedAtUtcMillis: fetchedAtUtcMillis ?? this.fetchedAtUtcMillis,
  );
  CachedDocumentRow copyWithCompanion(CachedDocumentsCompanion data) {
    return CachedDocumentRow(
      key: data.key.present ? data.key.value : this.key,
      payload: data.payload.present ? data.payload.value : this.payload,
      fetchedAtUtcMillis: data.fetchedAtUtcMillis.present
          ? data.fetchedAtUtcMillis.value
          : this.fetchedAtUtcMillis,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedDocumentRow(')
          ..write('key: $key, ')
          ..write('payload: $payload, ')
          ..write('fetchedAtUtcMillis: $fetchedAtUtcMillis')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, payload, fetchedAtUtcMillis);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedDocumentRow &&
          other.key == this.key &&
          other.payload == this.payload &&
          other.fetchedAtUtcMillis == this.fetchedAtUtcMillis);
}

class CachedDocumentsCompanion extends UpdateCompanion<CachedDocumentRow> {
  final Value<String> key;
  final Value<String> payload;
  final Value<int> fetchedAtUtcMillis;
  final Value<int> rowid;
  const CachedDocumentsCompanion({
    this.key = const Value.absent(),
    this.payload = const Value.absent(),
    this.fetchedAtUtcMillis = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedDocumentsCompanion.insert({
    required String key,
    required String payload,
    required int fetchedAtUtcMillis,
    this.rowid = const Value.absent(),
  }) : key = Value(key),
       payload = Value(payload),
       fetchedAtUtcMillis = Value(fetchedAtUtcMillis);
  static Insertable<CachedDocumentRow> custom({
    Expression<String>? key,
    Expression<String>? payload,
    Expression<int>? fetchedAtUtcMillis,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (payload != null) 'payload': payload,
      if (fetchedAtUtcMillis != null)
        'fetched_at_utc_millis': fetchedAtUtcMillis,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedDocumentsCompanion copyWith({
    Value<String>? key,
    Value<String>? payload,
    Value<int>? fetchedAtUtcMillis,
    Value<int>? rowid,
  }) {
    return CachedDocumentsCompanion(
      key: key ?? this.key,
      payload: payload ?? this.payload,
      fetchedAtUtcMillis: fetchedAtUtcMillis ?? this.fetchedAtUtcMillis,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (payload.present) {
      map['payload'] = Variable<String>(payload.value);
    }
    if (fetchedAtUtcMillis.present) {
      map['fetched_at_utc_millis'] = Variable<int>(fetchedAtUtcMillis.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedDocumentsCompanion(')
          ..write('key: $key, ')
          ..write('payload: $payload, ')
          ..write('fetchedAtUtcMillis: $fetchedAtUtcMillis, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$CacheDatabase extends GeneratedDatabase {
  _$CacheDatabase(QueryExecutor e) : super(e);
  $CacheDatabaseManager get managers => $CacheDatabaseManager(this);
  late final $CachedDocumentsTable cachedDocuments = $CachedDocumentsTable(
    this,
  );
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [cachedDocuments];
}

typedef $$CachedDocumentsTableCreateCompanionBuilder =
    CachedDocumentsCompanion Function({
      required String key,
      required String payload,
      required int fetchedAtUtcMillis,
      Value<int> rowid,
    });
typedef $$CachedDocumentsTableUpdateCompanionBuilder =
    CachedDocumentsCompanion Function({
      Value<String> key,
      Value<String> payload,
      Value<int> fetchedAtUtcMillis,
      Value<int> rowid,
    });

class $$CachedDocumentsTableFilterComposer
    extends Composer<_$CacheDatabase, $CachedDocumentsTable> {
  $$CachedDocumentsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get fetchedAtUtcMillis => $composableBuilder(
    column: $table.fetchedAtUtcMillis,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedDocumentsTableOrderingComposer
    extends Composer<_$CacheDatabase, $CachedDocumentsTable> {
  $$CachedDocumentsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get fetchedAtUtcMillis => $composableBuilder(
    column: $table.fetchedAtUtcMillis,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedDocumentsTableAnnotationComposer
    extends Composer<_$CacheDatabase, $CachedDocumentsTable> {
  $$CachedDocumentsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get key =>
      $composableBuilder(column: $table.key, builder: (column) => column);

  GeneratedColumn<String> get payload =>
      $composableBuilder(column: $table.payload, builder: (column) => column);

  GeneratedColumn<int> get fetchedAtUtcMillis => $composableBuilder(
    column: $table.fetchedAtUtcMillis,
    builder: (column) => column,
  );
}

class $$CachedDocumentsTableTableManager
    extends
        RootTableManager<
          _$CacheDatabase,
          $CachedDocumentsTable,
          CachedDocumentRow,
          $$CachedDocumentsTableFilterComposer,
          $$CachedDocumentsTableOrderingComposer,
          $$CachedDocumentsTableAnnotationComposer,
          $$CachedDocumentsTableCreateCompanionBuilder,
          $$CachedDocumentsTableUpdateCompanionBuilder,
          (
            CachedDocumentRow,
            BaseReferences<
              _$CacheDatabase,
              $CachedDocumentsTable,
              CachedDocumentRow
            >,
          ),
          CachedDocumentRow,
          PrefetchHooks Function()
        > {
  $$CachedDocumentsTableTableManager(
    _$CacheDatabase db,
    $CachedDocumentsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedDocumentsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedDocumentsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedDocumentsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> key = const Value.absent(),
                Value<String> payload = const Value.absent(),
                Value<int> fetchedAtUtcMillis = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedDocumentsCompanion(
                key: key,
                payload: payload,
                fetchedAtUtcMillis: fetchedAtUtcMillis,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String key,
                required String payload,
                required int fetchedAtUtcMillis,
                Value<int> rowid = const Value.absent(),
              }) => CachedDocumentsCompanion.insert(
                key: key,
                payload: payload,
                fetchedAtUtcMillis: fetchedAtUtcMillis,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedDocumentsTableProcessedTableManager =
    ProcessedTableManager<
      _$CacheDatabase,
      $CachedDocumentsTable,
      CachedDocumentRow,
      $$CachedDocumentsTableFilterComposer,
      $$CachedDocumentsTableOrderingComposer,
      $$CachedDocumentsTableAnnotationComposer,
      $$CachedDocumentsTableCreateCompanionBuilder,
      $$CachedDocumentsTableUpdateCompanionBuilder,
      (
        CachedDocumentRow,
        BaseReferences<
          _$CacheDatabase,
          $CachedDocumentsTable,
          CachedDocumentRow
        >,
      ),
      CachedDocumentRow,
      PrefetchHooks Function()
    >;

class $CacheDatabaseManager {
  final _$CacheDatabase _db;
  $CacheDatabaseManager(this._db);
  $$CachedDocumentsTableTableManager get cachedDocuments =>
      $$CachedDocumentsTableTableManager(_db, _db.cachedDocuments);
}
