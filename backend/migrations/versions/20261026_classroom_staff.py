"""Classroom staff roles and the allowed email domains.

PRD §3 gives a classroom four roles instead of one undifferentiated instructor
list, and FR-AUTH-02 lets a classroom restrict which email domains may join.

Staff get their own table rather than a role column on `students`: a `students`
row is an evaluation subject and an evaluator everywhere in the system, so
putting staff there would make them candidates for evaluation unless every
query remembered to filter them out.

Revision ID: 20261026_classroom_staff
Revises: 20261025_assignment_status
"""

import sqlalchemy as sa
from alembic import op

revision = "20261026_classroom_staff"
down_revision = "20261025_assignment_status"
branch_labels = None
depends_on = None

ROLES = ("OWNER", "CO_TEACHER", "TA")


def upgrade() -> None:
    op.create_table(
        "classroom_staff",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("classroom_id", sa.Integer(), sa.ForeignKey("classrooms.id"),
                  nullable=False, index=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("classroom_id", "email", name="uq_classroom_staff_member"),
        sa.CheckConstraint(" OR ".join(f"role = '{role}'" for role in ROLES),
                           name="ck_classroom_staff_role"),
    )

    # The creator's address is first in instructor_emails, so it becomes the
    # owner and anyone invited later becomes a co-teacher. No existing classroom
    # distinguished the two, and co-teacher is the weaker of the two.
    connection = op.get_bind()
    classrooms = sa.table("classrooms", sa.column("id", sa.Integer()),
                          sa.column("instructor_emails", sa.Text()))
    staff = sa.table("classroom_staff", sa.column("classroom_id", sa.Integer()),
                     sa.column("email", sa.String()), sa.column("role", sa.String()),
                     sa.column("added_at", sa.DateTime(timezone=True)))
    rows = []
    for classroom_id, emails in connection.execute(sa.select(classrooms.c.id,
                                                             classrooms.c.instructor_emails)):
        seen = []
        for address in (emails or "").split(","):
            address = address.strip().lower()
            if address and address not in seen:
                seen.append(address)
        rows.extend({"classroom_id": classroom_id, "email": address,
                     "role": "OWNER" if index == 0 else "CO_TEACHER",
                     "added_at": None}
                    for index, address in enumerate(seen))
    if rows:
        connection.execute(staff.insert(), rows)

    op.add_column("classrooms", sa.Column("allowed_email_domains", sa.Text(), nullable=True))
    op.drop_column("classrooms", "instructor_emails")


def downgrade() -> None:
    op.add_column("classrooms", sa.Column("instructor_emails", sa.Text(), nullable=True,
                                          server_default=""))
    connection = op.get_bind()
    staff = sa.table("classroom_staff", sa.column("classroom_id", sa.Integer()),
                     sa.column("email", sa.String()), sa.column("role", sa.String()))
    classrooms = sa.table("classrooms", sa.column("id", sa.Integer()),
                          sa.column("instructor_emails", sa.Text()))
    grouped: dict[int, list[str]] = {}
    for classroom_id, email, role in connection.execute(
            sa.select(staff.c.classroom_id, staff.c.email, staff.c.role)):
        if role in ("OWNER", "CO_TEACHER"):
            grouped.setdefault(classroom_id, []).append(email)
    for classroom_id, emails in grouped.items():
        connection.execute(classrooms.update().where(classrooms.c.id == classroom_id)
                           .values(instructor_emails=",".join(sorted(emails))))
    op.drop_column("classrooms", "allowed_email_domains")
    op.drop_table("classroom_staff")
