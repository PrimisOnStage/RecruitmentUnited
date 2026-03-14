import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def _create_candidates_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id               SERIAL PRIMARY KEY,
            name             TEXT,
            email            TEXT UNIQUE,
            phone            TEXT,
            country           TEXT,
            location         TEXT,
            "current_role"   TEXT,
            experience_years INT,
            skills           TEXT[],
            stage            TEXT DEFAULT 'applied',
            source           TEXT,
            raw_text         TEXT,
            source_metadata  JSONB DEFAULT '{}'::jsonb,
            created_at       TIMESTAMP DEFAULT NOW()
        );
    """)


def init_db(reset: bool | None = None):
    if reset is None:
        reset = _env_bool("RESET_DB_ON_STARTUP", default=False)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    if reset:
        # Explicitly recreate the table so schema changes can be applied cleanly.
        cur.execute("DROP TABLE IF EXISTS candidates;")

    _create_candidates_table(cur)

    # Backfill from old schema naming if this DB was created before the rename.
    cur.execute('ALTER TABLE candidates ADD COLUMN IF NOT EXISTS country TEXT;')
    cur.execute('ALTER TABLE candidates ADD COLUMN IF NOT EXISTS "current_role" TEXT;')
    cur.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'candidates' AND column_name = 'candidate_role'
            ) THEN
                UPDATE candidates
                SET "current_role" = COALESCE("current_role", candidate_role)
                WHERE candidate_role IS NOT NULL;
            END IF;
        END $$;
    """)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Database ready. reset={reset}")

if __name__ == "__main__":
    init_db(reset=("--reset" in sys.argv) or _env_bool("RESET_DB", default=False))
