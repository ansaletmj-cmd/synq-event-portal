
import os
import re

import psycopg


# --------------------------------------------------
# ROW COMPATIBILITY
# Supports both row["column"] and row[0]
# --------------------------------------------------

class HybridRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def hybrid_row_factory(cursor):
    columns = [column.name for column in cursor.description]

    def make_row(values):
        return HybridRow(zip(columns, values))

    return make_row


# --------------------------------------------------
# SQL COMPATIBILITY
# --------------------------------------------------

def adapt_sql(sql):
    # PostgreSQL requires the table name "user" to be quoted
    # when it appears as a table following these SQL keywords.
    sql = re.sub(
        r'(\bFROM\s+|\bJOIN\s+|\bINTO\s+|\bUPDATE\s+)user\b',
        r'\1"user"',
        sql,
        flags=re.IGNORECASE,
    )

    # Convert SQLite parameter placeholders to Psycopg syntax.
    sql = sql.replace("?", "%s")

    # Handle generated IDs previously retrieved with lastrowid.
    match = re.match(
        r'\s*INSERT\s+INTO\s+(?:"user"|user|event)\b',
        sql,
        flags=re.IGNORECASE,
    )

    if match and not re.search(r'\bRETURNING\b', sql, re.IGNORECASE):
        table_match = re.search(
            r'\bINSERT\s+INTO\s+("?user"?|event)\b',
            sql,
            flags=re.IGNORECASE,
        )

        if table_match:
            table = table_match.group(1).replace('"', '').lower()

            if table == "user":
                id_column = "user_id"
            elif table == "event":
                id_column = "event_id"
            else:
                id_column = None

            if id_column:
                sql = sql.rstrip().rstrip(";")
                sql += f" RETURNING {id_column}"

    return sql


# --------------------------------------------------
# CURSOR COMPATIBILITY
# --------------------------------------------------

class CursorAdapter:
    def __init__(self, cursor):
        self._cursor = cursor
        self._lastrowid = None
        self._insert_returning = False

    def execute(self, sql, params=None):
        original_sql = sql

        self._insert_returning = bool(
            re.match(
                r'\s*INSERT\s+INTO\s+(?:"user"|user|event)\b',
                original_sql,
                flags=re.IGNORECASE,
            )
            and not re.search(
                r'\bRETURNING\b',
                original_sql,
                flags=re.IGNORECASE,
            )
        )

        self._cursor.execute(
            adapt_sql(sql),
            () if params is None else params,
        )

        self._lastrowid = None

        if self._insert_returning:
            row = self._cursor.fetchone()
            if row is not None:
                self._lastrowid = row[0]

        return self

    @property
    def lastrowid(self):
        return self._lastrowid

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        if size is None:
            return self._cursor.fetchmany()
        return self._cursor.fetchmany(size)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        self._cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()



# --------------------------------------------------
# CONNECTION COMPATIBILITY
# --------------------------------------------------

class ConnectionAdapter:
    def __init__(self, connection):
        self._connection = connection

    def execute(self, sql, params=None):
        cursor = CursorAdapter(self._connection.cursor())
        return cursor.execute(sql, params)

    def cursor(self):
        return CursorAdapter(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()

        return False


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    connection = psycopg.connect(
        database_url,
        row_factory=hybrid_row_factory,
        sslmode="require",
    )

    return ConnectionAdapter(connection)


# --------------------------------------------------
# CREATE DATABASE TABLES
# --------------------------------------------------

def create_tables():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS "user" (
            user_id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('Student', 'Admin')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS event (
            event_id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            venue TEXT NOT NULL,
            date TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            category TEXT NOT NULL,
            created_by INTEGER NOT NULL REFERENCES "user"(user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS registration (
            registration_id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(user_id),
            event_id INTEGER NOT NULL REFERENCES event(event_id),
            status TEXT NOT NULL DEFAULT 'Confirmed',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            phone TEXT,
            department TEXT,
            year_of_study TEXT,
            class_division TEXT,
            UNIQUE(user_id, event_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS notification (
            notification_id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(user_id),
            event_id INTEGER REFERENCES event(event_id),
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        ALTER TABLE registration
        ADD COLUMN IF NOT EXISTS phone TEXT
        """,
        """
        ALTER TABLE registration
        ADD COLUMN IF NOT EXISTS department TEXT
        """,
        """
        ALTER TABLE registration
        ADD COLUMN IF NOT EXISTS year_of_study TEXT
        """,
        """
        ALTER TABLE registration
        ADD COLUMN IF NOT EXISTS class_division TEXT
        """,
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

    print("PostgreSQL tables created successfully!")


if __name__ == "__main__":
    create_tables()
