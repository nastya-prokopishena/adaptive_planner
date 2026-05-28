from sqlalchemy import text

from backend.infrastructure.db.database import engine

MIGRATION_SQL = """
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS task_type VARCHAR(100) DEFAULT 'other';

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS keywords TEXT;

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS estimated_duration_hours FLOAT DEFAULT 1;

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS difficulty_score INTEGER DEFAULT 3;

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS nlp_source VARCHAR(100) DEFAULT 'manual';

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS missed_at TIMESTAMP;
"""


def run_migration():
    with engine.begin() as connection:
        connection.execute(text(MIGRATION_SQL))

    print("Task NLP columns migration completed.")


if __name__ == "__main__":
    run_migration()
