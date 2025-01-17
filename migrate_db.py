import sqlite3

def add_is_bot_column():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    try:
        # Check if is_bot column exists
        cursor.execute("SELECT is_bot FROM user LIMIT 1")
    except sqlite3.OperationalError:
        # Add is_bot column if it doesn't exist
        print("Adding is_bot column to user table...")
        cursor.execute("ALTER TABLE user ADD COLUMN is_bot BOOLEAN DEFAULT FALSE")
        conn.commit()
        print("Column added successfully!")
    
    conn.close()

if __name__ == "__main__":
    add_is_bot_column()
