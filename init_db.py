import sqlite3
import os

DB_NAME = "smartcart1.db"   # Database name

def init_db():
    # Connect to SQLite database
    conn = sqlite3.connect(DB_NAME)
    
    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Execute schema file
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    
    conn.commit()
    conn.close()
    
    print("SmartCart database initialized successfully.")

if __name__ == "__main__":
    # Optional: remove old database during development
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print("Old smartcart database removed.")

    init_db()