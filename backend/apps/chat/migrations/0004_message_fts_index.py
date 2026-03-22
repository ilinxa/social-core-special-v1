"""
FTS GIN Index on Message.content
================================
PostgreSQL-only: adds GIN indexes for full-text search and trigram similarity.
Skipped on SQLite (no-op).
"""

from django.db import connection, migrations


def create_fts_indexes(apps, schema_editor):
    """Create FTS and trigram indexes (PostgreSQL only)."""
    if connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS chat_message_content_fts_idx
            ON chat_message
            USING GIN (to_tsvector('english', content));
        """)
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS chat_message_content_trgm_idx
            ON chat_message
            USING GIN (content gin_trgm_ops);
        """)


def drop_fts_indexes(apps, schema_editor):
    """Drop FTS and trigram indexes."""
    if connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS chat_message_content_fts_idx;")
        cursor.execute("DROP INDEX IF EXISTS chat_message_content_trgm_idx;")


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_messageattachment_messagereaction"),
    ]

    operations = [
        migrations.RunPython(create_fts_indexes, drop_fts_indexes),
    ]
