from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_slots():
    """Fetch current slot data from the database."""
    conn = sqlite3.connect("parking.db")
    cursor = conn.cursor()
    cursor.execute("SELECT slot_no, status, car_license_plate FROM Slots")
    slots = cursor.fetchall()
    conn.close()

    free_slots = [slot for slot in slots if slot[1].lower() == "empty"]
    occupied_slots = [slot for slot in slots if slot[1].lower() == "occupied"]
    waiting_slots = [slot for slot in slots if slot[1].lower() == "waiting"]

    return {
        "free_slots": free_slots,
        "occupied_slots": occupied_slots,
        "waiting_slots": waiting_slots
    }

@app.route("/")
def dashboard():
    slots = get_slots()
    now = datetime.now()
    return render_template("dashboard.html", slots=slots, now=now)

@app.route("/api/slots")
def api_slots():
    return jsonify(get_slots())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
