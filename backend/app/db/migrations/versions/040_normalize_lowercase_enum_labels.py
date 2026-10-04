"""Normalize native PostgreSQL enum labels to lowercase.

Several ORM columns declare ``SQLEnum(SomeEnum, values_callable=...)``, which
makes SQLAlchemy persist and expect the enum *values* (lowercase) instead of
the member *names* (uppercase).  Databases originally created via
``Base.metadata.create_all()`` -- before ``values_callable`` was introduced --
ended up with uppercase labels, so reading a row raised::

    LookupError: 'OWNER' is not among the defined enum values

Migrations 007/022 create these same types with lowercase labels, so a
migration-built database is already correct; this revision repairs databases
whose types were seeded by ``create_all``.  PostgreSQL cannot rename an enum
label in place, so each affected type is rebuilt with lowercased labels and
existing rows are cast through ``lower()``.

Revision ID: 040
Revises: 039
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "040"
down_revision = "039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: Enum type name -> the labels the ORM expects, in declaration order.
_TARGETS: dict[str, tuple[str, ...]] = {
    "membershiprole": ("owner", "admin", "member", "viewer"),
    "prstatus": ("open", "merged", "closed", "draft"),
    "fixtype": ("terraform", "dockerfile", "kubernetes", "ci_cd", "general"),
    "suggestionstatus": ("open", "in_progress", "fixed", "ignored"),
}

#: Suffix for the shadow type used while swapping labels.
_TMP_SUFFIX = "__lowercase_tmp"


def _enum_labels(bind: sa.Connection, type_name: str) -> list[str] | None:
    """Return the current labels of ``type_name`` sorted by sort order, or None."""
    rows = bind.execute(
        sa.text(
            """
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE t.typname = :name
            ORDER BY e.enumsortorder
            """
        ),
        {"name": type_name},
    ).scalars()
    return list(rows) if rows else None


def _dependent_columns(bind: sa.Connection, type_name: str) -> list[tuple[str, str]]:
    """Return ``(table, column)`` pairs whose type is ``type_name``."""
    rows = bind.execute(
        sa.text(
            """
            SELECT c.relname, a.attname
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE a.atttypid = to_regtype(:name)
              AND a.attnum > 0
              AND NOT a.attisdropped
              AND c.relkind = 'r'
              AND n.nspname = current_schema()
            """
        ),
        {"name": type_name},
    ).all()
    return [(t, col) for t, col in rows]


def _column_default(bind: sa.Connection, table: str, column: str) -> str | None:
    """Return the column's DEFAULT expression, if any."""
    return bind.execute(
        sa.text(
            """
            SELECT pg_get_expr(d.adbin, d.adrelid)
            FROM pg_attrdef d
            JOIN pg_attribute a
              ON a.attrelid = d.adrelid AND a.attnum = d.adnum
            WHERE d.adrelid = to_regclass(:table) AND a.attname = :column
            """
        ),
        {"table": table, "column": column},
    ).scalar()


def _normalize(bind: sa.Connection, type_name: str) -> None:
    current = _enum_labels(bind, type_name)
    if current is None:
        return

    wanted = list(_TARGETS[type_name])
    if current == wanted:
        # Already exactly what the ORM expects -- nothing to do.
        return

    if [label.lower() for label in current] != wanted:
        raise RuntimeError(
            f"enum {type_name!r} labels {current!r} differ from the ORM's expected "
            f"labels {wanted!r} by more than letter case. Refusing to "
            f"rewrite the type; reconcile the labels manually first."
        )

    tmp_type = f"{type_name}{_TMP_SUFFIX}"
    new_labels = ", ".join(f"'{label.lower()}'" for label in current)
    columns = _dependent_columns(bind, type_name)
    if not columns:
        return

    bind.execute(sa.text(f"DROP TYPE IF EXISTS {tmp_type}"))

    defaults = {col: _column_default(bind, tbl, col) for tbl, col in columns}
    for table, column in columns:
        bind.execute(sa.text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT'))

    bind.execute(sa.text(f"CREATE TYPE {tmp_type} AS ENUM ({new_labels})"))

    for table, column in columns:
        # Cast through lower() so existing rows keep their meaning.
        bind.execute(
            sa.text(
                f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                f"TYPE {tmp_type} USING (lower(\"{column}\"::text))::{tmp_type}"
            )
        )

    bind.execute(sa.text(f"DROP TYPE {type_name}"))
    bind.execute(sa.text(f"ALTER TYPE {tmp_type} RENAME TO {type_name}"))

    for table, column in columns:
        default = defaults[column]
        if default:
            bind.execute(sa.text(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT {default}'))


def upgrade() -> None:
    bind = op.get_bind()
    for type_name in _TARGETS:
        _normalize(bind, type_name)


def downgrade() -> None:
    # Recreating the types with uppercase labels would require re-casing every
    # row and re-pointing the ORM back; leave the lowercase labels in place.
    pass
