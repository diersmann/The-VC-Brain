"""Add constraints for API-facing domain status values.

Revision ID: 019
Revises: 018
"""

from collections.abc import Sequence

from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_opportunities_lifecycle_state",
        "opportunities",
        "lifecycle_state IN ("
        "'discovered','interesting','investigating','contacted','received',"
        "'memo_ready','hold','approved','closed','screening','triage','diligence')",
    )
    op.create_check_constraint(
        "ck_claims_status",
        "claims",
        "status IN ('supported','contradicted','unverified','tavily_synthesized')",
    )
    op.create_check_constraint(
        "ck_assessments_axis",
        "assessments",
        "axis IN ('Founder','Market','Idea-Market','execution','technical','commercial')",
    )
    op.create_check_constraint(
        "ck_assessments_rating",
        "assessments",
        "rating IN ('Bullish','Neutral','Bearish','bullish','neutral','bearish')",
    )
    op.create_check_constraint(
        "ck_assessments_trend",
        "assessments",
        "trend IN ('Improving','Stable','Declining','improving','stable','declining')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_assessments_trend", "assessments", type_="check")
    op.drop_constraint("ck_assessments_rating", "assessments", type_="check")
    op.drop_constraint("ck_assessments_axis", "assessments", type_="check")
    op.drop_constraint("ck_claims_status", "claims", type_="check")
    op.drop_constraint("ck_opportunities_lifecycle_state", "opportunities", type_="check")
