
from database import get_db_connection

conn = get_db_connection()

try:
    print("\n--- FOREIGN KEY VIOLATIONS ---")
    violations = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if violations:
        for row in violations:
            print(dict(row))
    else:
        print("No foreign key violations found.")

    print("\n--- DUPLICATE REGISTRATIONS ---")
    duplicates = conn.execute("""
        SELECT user_id, event_id, COUNT(*) AS total
        FROM registration
        GROUP BY user_id, event_id
        HAVING COUNT(*) > 1
    """).fetchall()

    if duplicates:
        for row in duplicates:
            print(dict(row))
    else:
        print("No duplicate registrations found.")

finally:
    conn.close()
