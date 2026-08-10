"""Schema verification after migrations.

Compares the live database schema against the SQLAlchemy models
(``Base.metadata``) and reports any drift: missing tables, missing columns,
incompatible column types, and (as warnings) missing primary keys, foreign
keys, indexes, and unique constraints.

This is deliberately conservative: only clear, data-affecting mismatches are
reported as errors.  Cosmetic variance (e.g. JSON vs JSONB, UUID stored as
text, enum vs varchar) is reported as a warning so existing databases are not
blocked from starting.
"""

from dataclasses import dataclass, field

import structlog
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    create_engine,
    inspect,
)
from sqlalchemy.dialects import postgresql

logger = structlog.get_logger(__name__)

# Column types whose differences never block startup (cosmetic variance).
_PERMISSIVE_BUCKET_PAIRS: set[tuple[str, str]] = {
    ("uuid", "string"),
    ("string", "uuid"),
    ("string", "enum"),
    ("enum", "string"),
    ("json", "json"),
    ("float", "integer"),
    ("integer", "float"),
    ("datetime", "datetime"),
}


@dataclass
class SchemaIssue:
    level: str  # "error" | "warning"
    kind: str
    table: str
    column: str | None = None
    detail: str = ""

    @property
    def is_error(self) -> bool:
        return self.level == "error"


@dataclass
class SchemaReport:
    ok: bool
    issues: list[SchemaIssue] = field(default_factory=list)
    tables_checked: int = 0
    columns_checked: int = 0
    database_revision: str | None = None
    required_revision: str | None = None

    @property
    def errors(self) -> list[SchemaIssue]:
        return [i for i in self.issues if i.is_error]

    @property
    def warnings(self) -> list[SchemaIssue]:
        return [i for i in self.issues if not i.is_error]

    def format_banner(self) -> str:
        lines = ["=" * 60, "DATABASE SCHEMA VALIDATION FAILED", "=" * 60]
        lines.append(f"Required migration revision: {self.required_revision or 'unknown'}")
        lines.append(f"Database migration revision: {self.database_revision or 'unknown'}")
        for issue in self.issues:
            loc = f"{issue.table}.{issue.column}" if issue.column else issue.table
            lines.append(f"  [{issue.level.upper()}] {issue.kind}: {loc} — {issue.detail}")
        return "\n".join(lines)


def _model_type_bucket(col_type) -> str:
    """Map a SQLAlchemy column type to a coarse affinity bucket."""
    if isinstance(col_type, Integer | BigInteger | SmallInteger):
        return "integer"
    if isinstance(col_type, Float | Numeric):
        return "float"
    if isinstance(col_type, Boolean):
        return "boolean"
    if isinstance(col_type, String | Text | Enum):
        return "string"
    if isinstance(col_type, DateTime | Date | Time):
        return "datetime"
    if isinstance(col_type, JSON | postgresql.JSONB):
        return "json"
    if isinstance(col_type, postgresql.UUID):
        return "uuid"
    if isinstance(col_type, LargeBinary):
        return "binary"
    if isinstance(col_type, postgresql.ARRAY):
        return "array"
    return "string"


def _db_type_bucket(db_type) -> str:
    """Map a database (inspector) column type to a coarse affinity bucket."""
    name = str(db_type).upper()
    if name.startswith("ARRAY"):
        return "array"
    if "UUID" in name:
        return "uuid"
    if "ENUM" in name:
        return "enum"
    if any(k in name for k in ("JSONB",)):
        return "json"
    if any(k in name for k in ("JSON",)):
        return "json"
    if any(k in name for k in ("TIMESTAMP", "DATE", "TIME")):
        return "datetime"
    if any(k in name for k in ("INT", "SERIAL")):
        return "integer"
    if any(k in name for k in ("FLOAT", "REAL", "NUMERIC", "DECIMAL", "DOUBLE")):
        return "float"
    if any(k in name for k in ("BOOL",)):
        return "boolean"
    if any(k in name for k in ("BYTEA", "BLOB", "BINARY", "VARBINARY")):
        return "binary"
    if any(k in name for k in ("VARCHAR", "CHAR", "TEXT", "NAME", "CITEXT")):
        return "string"
    return "string"


def _buckets_compatible(model_bucket: str, db_bucket: str) -> bool:
    if model_bucket == db_bucket:
        return True
    return (model_bucket, db_bucket) in _PERMISSIVE_BUCKET_PAIRS


def _sortable_bucket(bucket: str) -> str:
    """Normalize enum/uuid/string buckets so cosmetic variants sort together."""
    if bucket in ("enum", "uuid"):
        return "string"
    return bucket


def verify_schema(url: str, database_revision: str | None = None) -> SchemaReport:
    """Verify the live database schema matches the SQLAlchemy models.

    Returns a :class:`SchemaReport`; ``report.ok`` is True only when no
    blocking mismatches were found.
    """
    import app.models  # noqa: F401 — ensure every model is registered on Base.metadata
    from alembic.script import ScriptDirectory
    from app.db.base import Base
    from app.db.migrate import _alembic_config

    cfg = _alembic_config(url)
    try:
        required_revision = ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        required_revision = None

    report = SchemaReport(
        ok=True,
        database_revision=database_revision,
        required_revision=required_revision,
    )

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        db_tables = set(inspector.get_table_names())
    except Exception as exc:
        report.ok = False
        report.issues.append(
            SchemaIssue(
                level="error",
                kind="inspection_failed",
                table="",
                detail=f"Could not inspect database schema: {exc}",
            )
        )
        return report

    model_tables = Base.metadata.tables

    for table_name, model_table in model_tables.items():
        if table_name == "alembic_version":
            continue
        report.tables_checked += 1

        if table_name not in db_tables:
            report.ok = False
            report.issues.append(
                SchemaIssue(
                    level="error",
                    kind="missing_table",
                    table=table_name,
                    detail="Table defined in models but missing from the database.",
                )
            )
            continue

        try:
            db_columns = inspector.get_columns(table_name)
            db_pk = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
            db_fks = inspector.get_foreign_keys(table_name)
            db_indexes = inspector.get_indexes(table_name)
            db_unique = inspector.get_unique_constraints(table_name)
        except Exception as exc:
            report.ok = False
            report.issues.append(
                SchemaIssue(
                    level="error",
                    kind="inspection_failed",
                    table=table_name,
                    detail=f"Could not inspect table: {exc}",
                )
            )
            continue

        db_columns_by_name = {col["name"]: col for col in db_columns}

        for column in model_table.columns:
            report.columns_checked += 1
            col_name = column.name

            if col_name not in db_columns_by_name:
                report.ok = False
                report.issues.append(
                    SchemaIssue(
                        level="error",
                        kind="missing_column",
                        table=table_name,
                        column=col_name,
                        detail="Column defined in models but missing from the database.",
                    )
                )
                continue

            db_col = db_columns_by_name[col_name]
            model_bucket = _model_type_bucket(column.type)
            db_bucket = _db_type_bucket(db_col["type"])
            if not _buckets_compatible(model_bucket, db_bucket):
                report.ok = False
                report.issues.append(
                    SchemaIssue(
                        level="error",
                        kind="type_mismatch",
                        table=table_name,
                        column=col_name,
                        detail=(
                            f"Model type '{column.type}' is incompatible with "
                            f"database type '{db_col['type']}'."
                        ),
                    )
                )
            elif _sortable_bucket(model_bucket) != _sortable_bucket(db_bucket):
                report.issues.append(
                    SchemaIssue(
                        level="warning",
                        kind="type_variance",
                        table=table_name,
                        column=col_name,
                        detail=(
                            f"Model type '{column.type}' differs cosmetically from "
                            f"database type '{db_col['type']}'."
                        ),
                    )
                )

        # Primary key
        model_pk = (
            {c.name for c in model_table.primary_key.columns} if model_table.primary_key else set()
        )
        if model_pk and model_pk != db_pk:
            report.ok = False
            report.issues.append(
                SchemaIssue(
                    level="error",
                    kind="primary_key_mismatch",
                    table=table_name,
                    detail=f"Model primary key {sorted(model_pk)} does not match database {sorted(db_pk)}.",
                )
            )

        # Foreign keys
        model_fks = set()
        for fk in model_table.foreign_keys:
            model_fks.add((tuple(fk.parent.name.split(".")), tuple(fk.column.name.split("."))))
        db_fk_cols = {tuple(fk["constrained_columns"]) for fk in db_fks}
        missing_fks = {cols for (cols, _target) in model_fks if cols not in db_fk_cols}
        for cols in sorted(missing_fks):
            report.issues.append(
                SchemaIssue(
                    level="warning",
                    kind="missing_foreign_key",
                    table=table_name,
                    detail=f"Model expects a foreign key on {list(cols)} not present in the database.",
                )
            )

        # Indexes
        model_indexes: set[tuple[str, ...]] = set()
        for idx in model_table.indexes:
            model_indexes.add(tuple(idx.columns.keys()))
        for column in model_table.columns:
            if column.index and not column.unique:
                model_indexes.add((column.name,))
        db_index_colsets = {
            tuple(c for c in idx["column_names"] if c is not None) for idx in db_indexes
        }
        missing_indexes = sorted(model_indexes - db_index_colsets)
        for cols in missing_indexes:
            report.issues.append(
                SchemaIssue(
                    level="warning",
                    kind="missing_index",
                    table=table_name,
                    detail=f"Model expects an index on {list(cols)} not present in the database.",
                )
            )

        # Unique constraints
        model_unique: set[tuple[str, ...]] = set()
        for column in model_table.columns:
            if column.unique and not column.index:
                model_unique.add((column.name,))
        for constraint in model_table.constraints:
            from sqlalchemy import UniqueConstraint

            if isinstance(constraint, UniqueConstraint):
                model_unique.add(tuple(constraint.columns.keys()))
        db_unique_colsets = {
            tuple(c for c in uc["column_names"] if c is not None) for uc in db_unique
        }
        db_unique_index_colsets = {
            tuple(c for c in idx["column_names"] if c is not None)
            for idx in db_indexes
            if idx.get("unique")
        }
        satisfied_uniques = db_unique_colsets | db_unique_index_colsets
        missing_uniques = sorted(model_unique - satisfied_uniques)
        for cols in missing_uniques:
            report.issues.append(
                SchemaIssue(
                    level="warning",
                    kind="missing_unique_constraint",
                    table=table_name,
                    detail=f"Model expects a unique constraint on {list(cols)} not present in the database.",
                )
            )

    if not report.ok:
        logger.error("Database schema verification failed", issues=len(report.issues))
    else:
        logger.info(
            "Database schema verification passed",
            tables=report.tables_checked,
            columns=report.columns_checked,
            warnings=len(report.warnings),
        )
    return report
