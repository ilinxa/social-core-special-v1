# 03 — Database & Models Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 3.1 Model Design & Field Choices

| ID | Rule | Verdict |
|----|------|---------|
| 3.1.1 | FAIL if any model clearly owns two unrelated domain concepts (e.g. `User` model also storing billing info) | PASS/FAIL |
| 3.1.2 | FAIL if models exposed via API use auto-increment integer PKs — UUID required for external-facing IDs | PASS/FAIL |
| 3.1.3 | WARN if more than 30% of `CharField` fields use `max_length=255` without domain justification | PASS/WARN |
| 3.1.4 | FAIL if any `CharField(max_length=N)` where N > 1000 — should be `TextField` | PASS/FAIL |
| 3.1.5 | FAIL if `FloatField` is used for money or financial amounts | PASS/FAIL |
| 3.1.6 | WARN if `JSONField` is used where a proper relational model would better serve data integrity | PASS/WARN |
| 3.1.7 | FAIL if any `BooleanField` lacks an explicit `default` value | PASS/FAIL |
| 3.1.8 | WARN if `auto_now_add` and `auto_now` are confused or both applied to the same field | PASS/WARN |
| 3.1.9 | FAIL if any `ForeignKey` is missing an explicit `on_delete` parameter | PASS/FAIL |
| 3.1.10 | WARN if any `ForeignKey` relies on Django's auto-generated `_set` related name | PASS/WARN |
| 3.1.11 | WARN if `null=True` is used on `CharField` or `TextField` without documented reason | PASS/WARN |
| 3.1.12 | WARN if `null=True, blank=True` on non-string fields has no inline comment justifying it | PASS/WARN |
| 3.1.13 | WARN if `choices` fields use bare tuples instead of `TextChoices`/`IntegerChoices` | PASS/WARN |
| 3.1.14 | FAIL if comma-separated values are stored in a single field instead of a related model or `ArrayField`/`JSONField` | PASS/FAIL |

## 3.2 Abstract Base Models

| ID | Rule | Verdict |
|----|------|---------|
| 3.2.1 | FAIL if there is no shared `TimeStampedModel` and timestamp fields are manually defined on 3+ models | PASS/FAIL |
| 3.2.2 | FAIL if `created_at` does not use `auto_now_add=True` | PASS/FAIL |
| 3.2.3 | FAIL if `updated_at` does not use `auto_now=True` | PASS/FAIL |
| 3.2.4 | FAIL if API-facing models use auto-increment PKs and no shared `UUIDModel` exists | PASS/FAIL |
| 3.2.5 | FAIL if soft delete logic is copy-pasted across 2+ models instead of a shared abstract base | PASS/FAIL |
| 3.2.6 | FAIL if abstract base models are defined inside a domain app instead of `core/` | PASS/FAIL |
| 3.2.7 | WARN if any concrete model manually defines `created_at`/`updated_at` instead of inheriting | PASS/WARN |

## 3.3 Indexes & Performance

| ID | Rule | Verdict |
|----|------|---------|
| 3.3.1 | FAIL if any FK has `db_index=False` explicitly set without documented performance reason | PASS/FAIL |
| 3.3.2 | WARN if fields used in frequent `filter()`/`get()` calls across selectors/services lack indexes | PASS/WARN |
| 3.3.3 | WARN if fields used in `order_by()` lack indexes on large tables | PASS/WARN |
| 3.3.4 | WARN if multi-column filter patterns appear 3+ times without a composite index | PASS/WARN |
| 3.3.5 | INFO if no partial indexes exist — only relevant if filtered subsets are common | PASS/INFO |
| 3.3.6 | WARN if a `unique=True` field also has a duplicate explicit `Index` entry | PASS/WARN |
| 3.3.7 | INFO if `Meta.indexes` is not defined — only problematic if custom indexes are needed | PASS/INFO |
| 3.3.8 | WARN if write-heavy models have 5+ indexes without justification | PASS/WARN |
| 3.3.9 | INFO if index names don't follow a convention — cosmetic, not functional | PASS/INFO |

## 3.4 Database Constraints

| ID | Rule | Verdict |
|----|------|---------|
| 3.4.1 | FAIL if multi-column uniqueness is enforced only in application code without `UniqueConstraint` | PASS/FAIL |
| 3.4.2 | WARN if `unique_together` is used instead of `UniqueConstraint` (deprecated pattern) | PASS/WARN |
| 3.4.3 | WARN if value-range validation exists only in serializers without a `CheckConstraint` backstop | PASS/WARN |
| 3.4.4 | WARN if business rules that could be DB constraints are only enforced at the application level | PASS/WARN |
| 3.4.5 | FAIL if `IntegerField` stores FK IDs instead of using a proper `ForeignKey` | PASS/FAIL |
| 3.4.6 | WARN if nullable fields appear to be nullable by accident (no documented reason for `null=True`) | PASS/WARN |
| 3.4.7 | WARN if `default` values are set only in serializer/form but not on the model field | PASS/WARN |

## 3.5 QuerySet & Manager Design

| ID | Rule | Verdict |
|----|------|---------|
| 3.5.1 | WARN if the same filter chain appears 3+ times across the codebase without a QuerySet method | PASS/WARN |
| 3.5.2 | WARN if custom QuerySets exist but are not exposed via a Manager | PASS/WARN |
| 3.5.3 | FAIL if the default `objects` manager is replaced (not extended) and changes default behavior | PASS/FAIL |
| 3.5.4 | FAIL if soft-deletable models return deleted records via the default manager | PASS/FAIL |
| 3.5.5 | WARN if raw SQL is used in a manager without a comment explaining why ORM is insufficient | PASS/WARN |
| 3.5.6 | WARN if a QuerySet method returns a `list` instead of a QuerySet, breaking chainability | PASS/WARN |
| 3.5.7 | WARN if `.count() > 0` is used where `.exists()` would suffice | PASS/WARN |
| 3.5.8 | INFO if `.only()`/`.defer()` are not used — only relevant for models with 15+ fields | PASS/INFO |

## 3.6 Migrations

| ID | Rule | Verdict |
|----|------|---------|
| 3.6.1 | FAIL if any app has gaps or conflicts in migration numbering | PASS/FAIL |
| 3.6.2 | WARN if migration names are all auto-generated with no descriptive suffix | PASS/WARN |
| 3.6.3 | WARN if data migrations and schema migrations are combined in a single migration file | PASS/WARN |
| 3.6.4 | WARN if `RunPython` migrations lack a reverse function (even `RunPython.noop`) | PASS/WARN |
| 3.6.5 | PASS if `RunPython.noop` is used as reverse and the reason is clear | PASS |
| 3.6.6 | WARN if squashed migrations exist in a partially-applied state | PASS/WARN |
| 3.6.7 | WARN if CI does not run `manage.py migrate` from zero | PASS/WARN |
| 3.6.8 | WARN if CI does not run `migrate --check` to detect unapplied migrations | PASS/WARN |
| 3.6.9 | WARN if CI does not run `makemigrations --check` to detect missing migrations | PASS/WARN |
| 3.6.10 | FAIL if a migration modifies another app's model without a proper `dependencies` entry | PASS/FAIL |
| 3.6.11 | WARN if large-table index creation doesn't use `CONCURRENTLY` strategy | PASS/WARN |
| 3.6.12 | FAIL if circular migration dependencies exist | PASS/FAIL |

## 3.7 Model Meta Options

| ID | Rule | Verdict |
|----|------|---------|
| 3.7.1 | WARN if `Meta.ordering` is set on high-volume models without performance consideration | PASS/WARN |
| 3.7.2 | WARN if `Meta.ordering` adds `ORDER BY` to queries where order doesn't matter | PASS/WARN |
| 3.7.3 | WARN if `verbose_name` / `verbose_name_plural` are missing on models registered in admin | PASS/WARN |
| 3.7.4 | INFO if `db_table` is not explicitly set — only required for legacy/shared schemas | PASS/INFO |
| 3.7.5 | FAIL if `Meta.abstract = True` is missing on a model clearly intended as a base class | PASS/FAIL |
| 3.7.6 | WARN if `unique_together` or `index_together` is used instead of `UniqueConstraint`/`Index` | PASS/WARN |
| 3.7.7 | WARN if `.latest()` or `.earliest()` is called on a model without `get_latest_by` | PASS/WARN |

## 3.8 Model Methods & Properties

| ID | Rule | Verdict |
|----|------|---------|
| 3.8.1 | FAIL if any model is missing `__str__()` | PASS/FAIL |
| 3.8.2 | WARN if `__str__()` accesses FK fields that could trigger a DB query | PASS/WARN |
| 3.8.3 | INFO if `get_absolute_url()` is missing — only relevant for models with canonical URLs | PASS/INFO |
| 3.8.4 | PASS if `@property` is used for cheap, query-free computed values | PASS |
| 3.8.5 | FAIL if a model `@property` contains DB queries or expensive computation | PASS/FAIL |
| 3.8.6 | WARN if `clean()` is not used where multi-field validation is needed | PASS/WARN |
| 3.8.7 | FAIL if `save()` is overridden for side effects (emails, notifications, async tasks) | PASS/FAIL |
| 3.8.8 | FAIL if overridden `save()` does not call `super().save(*args, **kwargs)` | PASS/FAIL |

## 3.9 Relationships & Normalization

| ID | Rule | Verdict |
|----|------|---------|
| 3.9.1 | FAIL if repeated column groups exist (e.g. `tag1`, `tag2`, `tag3`) instead of a related model | PASS/FAIL |
| 3.9.2 | WARN if manual through-table FKs are used where `ManyToManyField` would suffice | PASS/WARN |
| 3.9.3 | WARN if `through` models on M2M are used but not explicitly defined | PASS/WARN |
| 3.9.4 | WARN if self-referential FKs lack `null=True` or `related_name` | PASS/WARN |
| 3.9.5 | WARN if denormalized fields exist without documented sync strategy | PASS/WARN |
| 3.9.6 | WARN if `GenericForeignKey` is used without documented justification | PASS/WARN |
| 3.9.7 | WARN if deeply nested FK traversals (3+ levels) appear in queries without `select_related` | PASS/WARN |

## 3.10 Soft Delete Pattern

| ID | Rule | Verdict |
|----|------|---------|
| 3.10.1 | WARN if soft delete is used inconsistently — some models hard delete, some soft delete, without rationale | PASS/WARN |
| 3.10.2 | WARN if soft delete uses only `is_deleted = BooleanField` without a `deleted_at` timestamp | PASS/WARN |
| 3.10.3 | FAIL if default manager returns soft-deleted records alongside active records | PASS/FAIL |
| 3.10.4 | FAIL if no admin/recovery manager exists to access soft-deleted records | PASS/FAIL |
| 3.10.5 | WARN if unique constraints don't exclude soft-deleted records (allowing re-creation) | PASS/WARN |
| 3.10.6 | WARN if cascade soft-delete behavior is undefined — related records silently orphaned | PASS/WARN |
| 3.10.7 | INFO if no periodic cleanup task exists for old soft-deleted records | PASS/INFO |

## 3.11 Admin Registration

| ID | Rule | Verdict |
|----|------|---------|
| 3.11.1 | WARN if models are not registered in `admin.py` (invisible to admin interface) | PASS/WARN |
| 3.11.2 | WARN if `ModelAdmin` classes use default `list_display` (only `__str__`) | PASS/WARN |
| 3.11.3 | WARN if models with large record counts lack `list_filter` and `search_fields` | PASS/WARN |
| 3.11.4 | WARN if FK fields with large related tables use dropdowns instead of `raw_id_fields`/`autocomplete_fields` | PASS/WARN |
| 3.11.5 | FAIL if sensitive fields (passwords, tokens, secrets) are displayed in admin | PASS/FAIL |
| 3.11.6 | WARN if auto-managed fields (`created_at`, `updated_at`, `id`) are editable in admin | PASS/WARN |
| 3.11.7 | INFO if no admin actions are defined — only relevant for models needing bulk operations | PASS/INFO |

## 3.12 Signals

| ID | Rule | Verdict |
|----|------|---------|
| 3.12.1 | WARN if signals are used for core business logic within a single app — should be a service method | PASS/WARN |
| 3.12.2 | FAIL if signal receivers are registered via module-level `@receiver` without `ready()` in `apps.py` | PASS/FAIL |
| 3.12.3 | FAIL if signal imports cause circular dependencies | PASS/FAIL |
| 3.12.4 | WARN if signal handlers contain heavy computation (DB queries, API calls) without delegation | PASS/WARN |
| 3.12.5 | WARN if `post_save` handlers don't check `created` kwarg when behavior should differ | PASS/WARN |
| 3.12.6 | FAIL if `pre_save`/`post_save` handlers call `.save()` on the same model instance — infinite loop risk | PASS/FAIL |
| 3.12.7 | WARN if signal handlers lack `dispatch_uid` — risk of duplicate registration | PASS/WARN |
| 3.12.8 | WARN if signal-driven business logic is undocumented and invisible to new developers | PASS/WARN |

## 3.13 Database Transactions

| ID | Rule | Verdict |
|----|------|---------|
| 3.13.1 | WARN if multi-step write operations lack `@transaction.atomic` wrapping | PASS/WARN |
| 3.13.2 | WARN if concurrent-write scenarios lack `select_for_update()` protection | PASS/WARN |
| 3.13.3 | FAIL if side effects (emails, Celery tasks) are triggered inside `@transaction.atomic` without `on_commit()` | PASS/FAIL |
| 3.13.4 | WARN if nested `@transaction.atomic` blocks don't consider savepoint behavior | PASS/WARN |
| 3.13.5 | WARN if long-running operations are wrapped in a single transaction causing lock contention | PASS/WARN |
| 3.13.6 | INFO if `ATOMIC_REQUESTS` is not set — deliberate per-view control is acceptable | PASS/INFO |

## 3.14 Query Optimization

| ID | Rule | Verdict |
|----|------|---------|
| 3.14.1 | FAIL if views/serializers traverse FK relations without `select_related()` causing N+1 | PASS/FAIL |
| 3.14.2 | FAIL if views/serializers traverse reverse FK or M2M without `prefetch_related()` causing N+1 | PASS/FAIL |
| 3.14.3 | INFO if custom `Prefetch()` objects are not used — only needed for filtered prefetches | PASS/INFO |
| 3.14.4 | WARN if full model instances are loaded when only 1-2 fields are needed (should use `.values()`) | PASS/WARN |
| 3.14.5 | WARN if looping `.save()` calls are used instead of `bulk_create()`/`bulk_update()` | PASS/WARN |
| 3.14.6 | INFO if `.iterator()` is not used for large querysets — only relevant for memory-sensitive contexts | PASS/INFO |
| 3.14.7 | WARN if read-modify-write patterns are used where `F()` expressions would prevent race conditions | PASS/WARN |
| 3.14.8 | WARN if Python loops aggregate data that could be done with `annotate()`/`aggregate()` | PASS/WARN |
| 3.14.9 | FAIL if any list view returns unbounded querysets without pagination | PASS/FAIL |
