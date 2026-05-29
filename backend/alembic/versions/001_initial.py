"""initial schema — 7 entidades

Revision ID: 001_initial
Revises:
Create Date: 2026-05-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cria enums via SQL puro com guarda IF NOT EXISTS (Postgres não suporta IF NOT EXISTS
    # em CREATE TYPE; usamos DO block).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_type') THEN
                CREATE TYPE task_type AS ENUM ('structured_extraction', 'classification_response');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'slice_label') THEN
                CREATE TYPE slice_label AS ENUM ('typical', 'edge', 'known_failure', 'adversarial');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'provider') THEN
                CREATE TYPE provider AS ENUM ('fake', 'claude', 'openai', 'gemini');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'run_status') THEN
                CREATE TYPE run_status AS ENUM ('pending', 'running', 'done', 'failed');
            END IF;
        END
        $$;
        """
    )

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(2000), nullable=False, server_default=""),
        sa.Column(
            "task_type",
            postgresql.ENUM("structured_extraction", "classification_response", name="task_type", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_slug", "tasks", ["slug"], unique=True)

    # prompt_versions
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("model_params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_baseline", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("task_id", "version_number", name="uq_prompt_task_version"),
    )
    op.create_index(
        "ix_prompt_task_version", "prompt_versions", ["task_id", "version_number"]
    )

    # test_cases
    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input", postgresql.JSONB(), nullable=False),
        sa.Column("expected", postgresql.JSONB(), nullable=True),
        sa.Column(
            "slice",
            postgresql.ENUM("typical", "edge", "known_failure", "adversarial", name="slice_label", create_type=False),
            nullable=False,
        ),
        sa.Column("rubric_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_testcase_task_slice", "test_cases", ["task_id", "slice"])

    # model_configs
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "provider",
            postgresql.ENUM("fake", "claude", "openai", "gemini", name="provider", create_type=False),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("price_per_1m_input", sa.Float(), nullable=False),
        sa.Column("price_per_1m_output", sa.Float(), nullable=False),
        sa.UniqueConstraint("provider", "model_name", name="uq_model_provider_name"),
    )

    # eval_runs
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_version_id",
            sa.Integer(),
            sa.ForeignKey("prompt_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_config_id",
            sa.Integer(),
            sa.ForeignKey("model_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "running", "done", "failed", name="run_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_evalrun_task_status", "eval_runs", ["task_id", "status"])
    op.create_index("ix_evalrun_promptversion", "eval_runs", ["prompt_version_id"])

    # eval_results
    op.create_table(
        "eval_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "eval_run_id",
            sa.Integer(),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_case_id",
            sa.Integer(),
            sa.ForeignKey("test_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repetition_index", sa.Integer(), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("deterministic_scores", postgresql.JSONB(), nullable=True),
        sa.Column("rubric_scores", postgresql.JSONB(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_evalresult_run", "eval_results", ["eval_run_id"])
    op.create_index(
        "ix_evalresult_run_case_rep",
        "eval_results",
        ["eval_run_id", "test_case_id", "repetition_index"],
    )

    # scorecards
    op.create_table(
        "scorecards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "eval_run_id",
            sa.Integer(),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("aggregate_score", sa.Float(), nullable=False),
        sa.Column("quality", sa.Float(), nullable=False),
        sa.Column("instruction_adherence", sa.Float(), nullable=False),
        sa.Column("factual_structural", sa.Float(), nullable=False),
        sa.Column("tone_format", sa.Float(), nullable=False),
        sa.Column("avg_latency_ms", sa.Float(), nullable=False),
        sa.Column("total_cost_usd", sa.Float(), nullable=False),
        sa.Column("failure_rate", sa.Float(), nullable=False),
        sa.Column("variance", sa.Float(), nullable=False),
        sa.Column(
            "per_slice_breakdown", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
    )
    op.create_index("ix_scorecard_run", "scorecards", ["eval_run_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_scorecard_run", table_name="scorecards")
    op.drop_table("scorecards")
    op.drop_index("ix_evalresult_run_case_rep", table_name="eval_results")
    op.drop_index("ix_evalresult_run", table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index("ix_evalrun_promptversion", table_name="eval_runs")
    op.drop_index("ix_evalrun_task_status", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_table("model_configs")
    op.drop_index("ix_testcase_task_slice", table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index("ix_prompt_task_version", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_index("ix_tasks_slug", table_name="tasks")
    op.drop_table("tasks")

    op.execute("DROP TYPE IF EXISTS run_status;")
    op.execute("DROP TYPE IF EXISTS provider;")
    op.execute("DROP TYPE IF EXISTS slice_label;")
    op.execute("DROP TYPE IF EXISTS task_type;")
