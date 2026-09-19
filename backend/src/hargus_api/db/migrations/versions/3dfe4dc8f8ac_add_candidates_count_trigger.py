"""add_candidates_count_trigger

Revision ID: 3dfe4dc8f8ac
Revises: 0384569732a1
Create Date: 2026-05-17 21:24:51.636256

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3dfe4dc8f8ac'
down_revision: Union[str, Sequence[str], None] = '0384569732a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION update_vacancy_candidates_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE vacancies
                SET candidates_count = candidates_count + 1
                WHERE id = NEW.vacancy_id;

            ELSIF TG_OP = 'DELETE' THEN
                UPDATE vacancies
                SET candidates_count = candidates_count - 1
                WHERE id = OLD.vacancy_id;

            ELSIF TG_OP = 'UPDATE' AND
                  OLD.vacancy_id IS DISTINCT FROM NEW.vacancy_id THEN
                IF OLD.vacancy_id IS NOT NULL THEN
                    UPDATE vacancies
                    SET candidates_count = candidates_count - 1
                    WHERE id = OLD.vacancy_id;
                END IF;
                IF NEW.vacancy_id IS NOT NULL THEN
                    UPDATE vacancies
                    SET candidates_count = candidates_count + 1
                    WHERE id = NEW.vacancy_id;
                END IF;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_candidates_count ON candidates;
               """)

    op.execute("""
        CREATE TRIGGER trg_candidates_count
        AFTER INSERT OR DELETE OR UPDATE OF vacancy_id ON candidates
        FOR EACH ROW EXECUTE FUNCTION update_vacancy_candidates_count();
    """)

    op.execute("""
        UPDATE vacancies v
        SET candidates_count = (
            SELECT COUNT(*) FROM candidates c WHERE c.vacancy_id = v.id
        );
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_candidates_count ON candidates;")
    op.execute("DROP FUNCTION IF EXISTS update_vacancy_candidates_count();")
