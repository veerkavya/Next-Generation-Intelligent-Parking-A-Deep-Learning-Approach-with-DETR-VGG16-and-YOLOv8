import sqlite3
import csv
import os

def setup_database():
    """
    Creates and initializes the SQLite database (parking.db), including:
    - UserType
    - Users (populated from CSV if available)
    - Slots
    - Occupied (parking history)
    """
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    # Create UserType table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserType (
            type_id INTEGER PRIMARY KEY,
            type_name TEXT UNIQUE
        )
    """)

    # Insert UserTypes
    cursor.execute("INSERT OR IGNORE INTO UserType (type_id, type_name) VALUES (1, 'Faculty')")
    cursor.execute("INSERT OR IGNORE INTO UserType (type_id, type_name) VALUES (2, 'Guest')")

    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            vehicle_no TEXT UNIQUE,
            type_id INTEGER,
            FOREIGN KEY(type_id) REFERENCES UserType(type_id)
        )
    """)

    # Populate Users table from CSV if file exists
    csv_file = "users.csv"
    if os.path.exists(csv_file):
        with open(csv_file, "r") as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                name, vehicle_no, type_name = row
                cursor.execute("""
                    INSERT OR IGNORE INTO Users (name, vehicle_no, type_id)
                    VALUES (?, ?, (SELECT type_id FROM UserType WHERE type_id = ?))
                """, (name, vehicle_no, type_name))

    # Create Slots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Slots (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_no INTEGER,
            slot_type TEXT,
            status TEXT DEFAULT 'empty',
            car_license_plate TEXT
        )
    """)

    # Insert default slots if table is empty (4 Faculty slots and 6 Guest slots)
    cursor.execute("SELECT COUNT(*) FROM Slots")
    if cursor.fetchone()[0] == 0:
        slot_no = 1
        for _ in range(4):  # Faculty slots
            cursor.execute("INSERT INTO Slots (slot_no, slot_type, status) VALUES (?, 'faculty', 'empty')", (slot_no,))
            slot_no += 1
        for _ in range(6):  # Guest slots
            cursor.execute("INSERT INTO Slots (slot_no, slot_type, status) VALUES (?, 'guest', 'empty')", (slot_no,))
            slot_no += 1

    # Create Occupied table (parking history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Occupied (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_time TEXT,
            logout_time TEXT,
            date TEXT,
            slot_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY(slot_id) REFERENCES Slots(slot_id),
            FOREIGN KEY(user_id) REFERENCES Users(user_id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
    print("Database setup completed.")
