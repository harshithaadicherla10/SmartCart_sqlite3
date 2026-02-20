import sqlite3
import os

# Get the current project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database path
db_path = os.path.join(BASE_DIR, "smartcart.db")

# Schema file path
schema_path = os.path.join(BASE_DIR, "schema.sql")

def init_db():
    # Connect to SQLite (creates DB if not exists)
    conn = sqlite3.connect(db_path)

    # Read schema.sql and execute all SQL commands
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    conn.commit()
    conn.close()

    print("Database created successfully using schema.sql!")

# Run the function
if __name__ == "__main__":
    init_db()