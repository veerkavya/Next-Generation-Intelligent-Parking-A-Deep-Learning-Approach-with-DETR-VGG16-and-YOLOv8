import cv2
import sqlite3
import requests
import time
from datetime import datetime
import random

# Import the inference pipeline from your Roboflow integration.
# Ensure that the inference.py module is in your project directory.
from inference import InferencePipeline

# Configuration for Roboflow inference
RF_API_KEY = "7RdO6RJ5gzrJPPIWh4Gm"  # Replace with your Roboflow API key
RF_WORKSPACE = "darpan-neve-gigwd"     # Replace with your Roboflow workspace name
RF_WORKFLOW_ID = "custom-workflow-2-2"   # Replace with your Roboflow workflow ID

# Flask API URL is not used here because we'll update the database directly.
# If you want to call an API endpoint to update user data, you can uncomment and configure below:
# FLASK_API_URL = "http://localhost:5001/api/update_user_data"

def generate_random_name(vehicle_no):
    """Generates a random name based on the vehicle number."""
    return f"Guest_{vehicle_no}"

def assign_parking(vehicle_no):
    """
    Checks if the vehicle exists in the Users table; if not, adds it.
    Then, assigns a parking slot by updating the slot status to 'waiting'
    and returns the assigned slot information.
    """
    # If vehicle_no is empty, assign a random placeholder value
    if not vehicle_no or not vehicle_no.strip():
        vehicle_no = {random.randint(1, 9999)}
        print(f"No valid plate extracted. Using placeholder: {vehicle_no}")
    
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    # Check if user exists in the Users table
    cursor.execute("SELECT user_id, type_id FROM Users WHERE vehicle_no = ?", (vehicle_no,))
    user = cursor.fetchone()

    if user is None:
        # If not, register a new user (for simplicity, we assume type_id=1 for now)
        random_name = generate_random_name(vehicle_no)
        type_id = 1
        cursor.execute("INSERT INTO Users (name, vehicle_no, type_id) VALUES (?, ?, ?)", 
                       (random_name, vehicle_no, type_id))
        conn.commit()
        cursor.execute("SELECT user_id FROM Users WHERE vehicle_no = ?", (vehicle_no,))
        user_id = cursor.fetchone()[0]
        print(f"New user added: {random_name} ({vehicle_no})")
    else:
        user_id, type_id = user

    # Determine desired slot type (for simplicity, we use 'faculty' for type_id==1)
    desired_type = 'faculty' if type_id == 1 else 'guest'

    # Find an available slot for the user
    if desired_type == 'faculty':
        cursor.execute("SELECT slot_id, slot_no, slot_type FROM Slots WHERE slot_type = 'faculty' AND status = 'empty'")
        slot = cursor.fetchone()
        if slot is None:
            cursor.execute("SELECT slot_id, slot_no, slot_type FROM Slots WHERE slot_type = 'guest' AND status = 'empty'")
            slot = cursor.fetchone()
    else:
        cursor.execute("SELECT slot_id, slot_no, slot_type FROM Slots WHERE slot_type = 'guest' AND status = 'empty'")
        slot = cursor.fetchone()

    if slot is None:
        conn.close()
        print("No available parking slots.")
        return None, None, None

    slot_id, slot_no, slot_type = slot

    # Update slot status to 'waiting' and set the car_license_plate
    cursor.execute("UPDATE Slots SET status = 'waiting', car_license_plate = ? WHERE slot_id = ?",
                   (vehicle_no, slot_id))
    now = datetime.now()
    login_time = now.strftime("%H:%M:%S")
    conn.commit()
    conn.close()

    print(f"Assigned {vehicle_no} to Slot {slot_no} ({slot_type}) with status 'waiting'")
    return slot_no, slot_type, user_id

def custom_sink(result, video_frame):
    """
    Callback function for the inference pipeline.
    Processes the prediction result, extracts the detected license plate,
    and calls assign_parking().
    """
    # Show the inference visualization (if desired)
    try:
        cv2.imshow("Entry Camera Feed", result["line_counter_visualization"].numpy_image)
        cv2.waitKey(1)
    except cv2.error:
        pass

    # Check if a license plate was detected
    if result.get("google_gemini"):
        # Extract the detected plate (first line of the first prediction)
        detected_plate = result["google_gemini"][0].split('\n')[0]
        if detected_plate:
            slot_no, slot_type, user_id = assign_parking(detected_plate)
            if slot_no:
                print(f"Vehicle {detected_plate} assigned to Slot {slot_no} ({slot_type}).")
            else:
                print(f"No available slots for {detected_plate}.")

def main():
    """
    Initializes and runs the Roboflow inference pipeline on the entry camera video.
    """
    pipeline = InferencePipeline.init_with_workflow(
        api_key=RF_API_KEY,
        workspace_name=RF_WORKSPACE,
        workflow_id=RF_WORKFLOW_ID,
        video_reference="test.mp4",  # Path to the entry camera video file
        max_fps=10,
        on_prediction=custom_sink
    )
    pipeline.start()
    pipeline.join()

if __name__ == "__main__":
    main()
