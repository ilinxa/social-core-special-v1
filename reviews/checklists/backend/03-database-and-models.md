# 03 — Database & Models Checklist

## 3.1 Model Design & Field Choices

- [ ] Every model has a clear, **single responsibility** — no model doing double duty for two domain concepts
- [ ] **Primary keys** — UUID (`UUIDField`) used instead of auto-increment int where external exposure is possible
- [ ] `CharField` always has a **reasonable `max_length`** — no `max_length=255` everywhere by default without thought
- [ ] `TextField` is used for unbounded text — not `CharField(max_length=10000)`
- [ ] `DecimalField` is used for **money/financial values** — never `FloatField` (floating point imprecision)
- [ ] `JSONField` usage is deliberate — not used as a lazy alternative to proper relational modeling
- [ ] `BooleanField` has explicit `default` — never left without one
- [ ] `DateTimeField` uses `auto_now_add` and `auto_now` correctly — not confused with each other
- [ ] All `ForeignKey` fields have explicit `on_delete` — no implicit behavior left to Django's default
- [ ] `ForeignKey` `related_name` is always set — no relying on Django's auto-generated `_set` names
- [ ] `null=True` on `CharField`/`TextField` is avoided — use `blank=True, default=''` instead
- [ ] `null=True, blank=True` on non-string fields is intentional and documented
- [ ] `choices` fields use **Python `Enum`** or `TextChoices`/`IntegerChoices` — not bare tuples
- [ ] No storing **comma-separated values** in a single field — normalize into a related model

## 3.2 Abstract Base Models

- [ ] A shared **`TimeStampedModel`** abstract base provides `created_at` and `updated_at` on all models
- [ ] `created_at` uses `auto_now_add=True` — not manually set
- [ ] `updated_at` uses `auto_now=True` — not manually set
- [ ] A shared **`UUIDModel`** abstract base provides `id = UUIDField(primary_key=True, default=uuid4)`
- [ ] Soft delete logic (if used) lives in a shared **`SoftDeleteModel`** abstract base — not duplicated per model
- [ ] Abstract base models live in a dedicated `core/` or `common/` app — not copy-pasted across apps
- [ ] All concrete models inherit from the appropriate base — no model reimplementing `created_at` manually

## 3.3 Indexes & Performance

- [ ] Every `ForeignKey` field has a DB index (Django adds this by default — verify it hasn't been disabled via `db_index=False`)
- [ ] All fields used in **`filter()`**, **`exclude()`**, or **`get()`** calls have appropriate indexes
- [ ] All fields used in **`order_by()`** calls have indexes
- [ ] **Composite indexes** (`Index(fields=['a', 'b'])`) are used where multi-column filtering is common
- [ ] **Partial indexes** are used where filtering on a subset (e.g. `WHERE is_active = TRUE`) is frequent
- [ ] `unique=True` constraints double as indexes — not duplicated with a separate `Index`
- [ ] `Meta.indexes` is defined explicitly in the model — not relying solely on implicit Django indexes
- [ ] No over-indexing — write-heavy tables don't have unnecessary indexes degrading insert performance
- [ ] Index naming follows a consistent convention (`idx_<table>_<field>`)

## 3.4 Database Constraints

- [ ] **`unique_together`** or `UniqueConstraint` is used to enforce multi-column uniqueness at DB level
- [ ] `UniqueConstraint` is preferred over `unique_together` (modern Django)
- [ ] **`CheckConstraint`** is used for value validation that must be guaranteed at DB level (e.g. `amount > 0`)
- [ ] No business rule constraints enforced **only** at serializer/view level without a DB constraint backstop
- [ ] Foreign key constraints are present — no `IntegerField` storing IDs without a proper `ForeignKey`
- [ ] `NOT NULL` constraints are correct — nullable fields are nullable for a deliberate reason
- [ ] `default` values are set at the DB level (via `Field(default=...)`) not just in application code

## 3.5 QuerySet & Manager Design

- [ ] Custom **`QuerySet`** classes encapsulate reusable filter logic — no repeated `.filter(is_active=True)` inline
- [ ] Custom **`Manager`** classes expose the custom QuerySet via `as_manager()` or explicit manager
- [ ] `objects` manager is never replaced — custom managers are **added**, not substituted
- [ ] **Soft delete managers** return only non-deleted records by default — with explicit `all_objects` manager for unfiltered access
- [ ] No raw SQL in managers unless absolutely necessary and clearly documented
- [ ] QuerySet methods are **chainable** — no method that breaks the chain by returning a list prematurely
- [ ] `.exists()` is used instead of `.count() > 0` for existence checks
- [ ] `.only()` and `.defer()` are used on fat models where full object loading is wasteful

## 3.6 Migrations

- [ ] Migrations are **sequential with no gaps** in numbering
- [ ] Every migration has a clear, descriptive **`name`** — not just `0042_auto_20240301_1234`
- [ ] **No data migrations mixed with schema migrations** — they are in separate migration files
- [ ] Data migrations use `RunPython` with both **forward and reverse** functions defined
- [ ] `RunPython.noop` is used as reverse when rollback is intentionally a no-op
- [ ] No **squashed migrations** left in a partially-applied state
- [ ] Migrations are **tested in CI** — `manage.py migrate` runs cleanly from zero on every PR
- [ ] `--check` flag (`manage.py migrate --check`) runs in CI to detect unapplied migrations
- [ ] `makemigrations --check` runs in CI to detect missing migrations for model changes
- [ ] No migration directly modifies **another app's model** — cross-app dependencies are explicit
- [ ] Long-running migrations (adding indexes on large tables) use `SeparateDatabaseAndState` or are run manually with `CREATE INDEX CONCURRENTLY`
- [ ] Migration dependencies are correct — no circular migration dependencies

## 3.7 Model Meta Options

- [ ] `Meta.ordering` is set only where a **universal default order** makes domain sense — not as a performance shortcut
- [ ] `Meta.ordering` on large tables is used with caution — it adds an `ORDER BY` to every query
- [ ] `Meta.verbose_name` and `Meta.verbose_name_plural` are set for all models (admin readability)
- [ ] `Meta.db_table` is set explicitly for models that map to a legacy or shared schema table
- [ ] `Meta.abstract = True` is correctly set on all base models — never missing
- [ ] `Meta.constraints` is used instead of deprecated `unique_together` and `index_together`
- [ ] `Meta.get_latest_by` is set if `.latest()` and `.earliest()` are used on the model

## 3.8 Model Methods & Properties

- [ ] `__str__()` is defined on every model — returns a meaningful human-readable representation
- [ ] `__str__()` never triggers additional DB queries (no FK traversal inside `__str__`)
- [ ] `get_absolute_url()` is defined where models have a canonical URL
- [ ] Model **properties** (`@property`) are used for computed fields that are cheap and query-free
- [ ] No **heavy computation or DB queries** inside model properties — those belong in the service layer
- [ ] `clean()` is used for model-level validation that spans multiple fields
- [ ] `save()` is not overridden for side effects (sending emails, triggering tasks) — use signals or service layer
- [ ] If `save()` is overridden, it calls `super().save(*args, **kwargs)` correctly

## 3.9 Relationships & Normalization

- [ ] Data is **normalized** to at least 3NF — no repeated groups of columns (`tag1`, `tag2`, `tag3`)
- [ ] **Many-to-many** relationships use `ManyToManyField` — not manual through-table FKs unless extra fields are needed
- [ ] When a `through` model is needed on M2M, it is explicitly defined and registered
- [ ] **Self-referential** FK relationships (`parent = ForeignKey('self')`) have `null=True, blank=True` and `related_name` set
- [ ] No **denormalized fields** without a documented reason and a strategy for keeping them in sync
- [ ] `GenericForeignKey` usage is rare, deliberate, and documented — not used as a lazy polymorphism shortcut
- [ ] Deeply nested FK traversals (`order.user.profile.company.address`) are flagged for query optimization

## 3.10 Soft Delete Pattern

- [ ] If soft delete is used, it is **consistent across all applicable models** — not some hard, some soft
- [ ] A `deleted_at = DateTimeField(null=True, blank=True)` field is used — not a `is_deleted = BooleanField`
- [ ] Default manager **excludes soft-deleted records** automatically
- [ ] An `all_objects` or `unscoped` manager is available for admin and recovery use cases
- [ ] Soft-deleted records are **excluded from unique constraints** where applicable (use `UniqueConstraint` with `condition`)
- [ ] Cascade behavior on soft delete is defined — related records are also soft-deleted or handled explicitly
- [ ] A periodic cleanup task exists for permanently purging old soft-deleted records if needed

## 3.11 Admin Registration

- [ ] Every model is registered in `admin.py` — no orphaned models invisible to admin
- [ ] `list_display` is set for all `ModelAdmin` classes — not defaulting to just `__str__`
- [ ] `list_filter` and `search_fields` are configured for models with large record counts
- [ ] `raw_id_fields` or `autocomplete_fields` is used for FK fields with large related tables — not a dropdown of 10,000 records
- [ ] Sensitive fields (passwords, tokens) are excluded from admin display
- [ ] `readonly_fields` is set for auto-managed fields (`created_at`, `updated_at`, `id`)
- [ ] Admin actions are defined for bulk operations rather than one-at-a-time manual edits

## 3.12 Signals

- [ ] Signals are used only for **decoupled cross-app notifications** — not for core business logic within an app
- [ ] Signal receivers are registered in the app's `ready()` method via `apps.py` — not at module level
- [ ] No circular imports caused by signal handler imports
- [ ] Signal handlers are **lightweight** — heavy work is delegated to a service or Celery task
- [ ] `post_save` signals check `created` kwarg to differentiate create vs update
- [ ] `pre_save` / `post_save` handlers do not call `.save()` on the same model — infinite loop risk
- [ ] Signal handlers have `dispatch_uid` set to prevent duplicate registration
- [ ] Signal usage is documented — not hidden business logic invisible to new developers

## 3.13 Database Transactions

- [ ] `@transaction.atomic` is used around multi-step write operations that must succeed or fail together
- [ ] `select_for_update()` is used where concurrent writes could cause race conditions
- [ ] `transaction.on_commit()` is used for side effects (emails, tasks) — not triggered inside the atomic block
- [ ] Nested `@transaction.atomic` uses `savepoint=True` (default) deliberately — no accidental partial rollbacks
- [ ] Long-running operations are NOT wrapped in a single transaction — risk of lock contention
- [ ] `ATOMIC_REQUESTS` setting is deliberately configured with documented rationale

## 3.14 Query Optimization

- [ ] `select_related()` is used for all **single-valued FK/OneToOne** traversals — no N+1 queries
- [ ] `prefetch_related()` is used for all **reverse FK and M2M** traversals — no N+1 queries
- [ ] `Prefetch()` objects are used where custom querysets are needed on prefetched relations
- [ ] `.values()` or `.values_list()` is used when only specific columns are needed — not loading full model instances
- [ ] `bulk_create()` and `bulk_update()` are used for batch operations — not looping `.save()` calls
- [ ] `iterator()` is used for large querysets that don't need caching in memory
- [ ] `F()` expressions are used for in-place updates — not read-modify-write patterns
- [ ] `annotate()` and `aggregate()` push computation to the database — not done in Python loops
- [ ] No unbounded querysets — all list views have pagination or explicit `LIMIT`
