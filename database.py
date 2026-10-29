
import sqlite3

DATABASE = "college_events.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    conn = get_db_connection()

    try:
        # USER table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('Student', 'Admin')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # EVENT table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS event (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                venue TEXT NOT NULL,
                date TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                category TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                FOREIGN KEY (created_by) REFERENCES user(user_id)
            )
        """)

        # REGISTRATION table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registration (
                registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(user_id),
                FOREIGN KEY (event_id) REFERENCES event(event_id),
                UNIQUE(user_id, event_id)
            )
        """)

        # Add registration details to existing databases
        existing_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(registration)"
            ).fetchall()
        }

        new_columns = {
            "phone": "TEXT",
            "department": "TEXT",
            "year_of_study": "TEXT",
            "class_division": "TEXT",
        }

        for column, data_type in new_columns.items():
            if column not in existing_columns:
                conn.execute(
                    f"ALTER TABLE registration "
                    f"ADD COLUMN {column} {data_type}"
                )

        # NOTIFICATION table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(user_id),
                FOREIGN KEY (event_id) REFERENCES event(event_id)
            )
        """)

        conn.commit()
        print("Database and tables created successfully!")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
