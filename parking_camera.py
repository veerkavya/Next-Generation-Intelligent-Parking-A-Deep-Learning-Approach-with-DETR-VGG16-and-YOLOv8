import cv2
import numpy as np
import pickle
import pandas as pd
import requests
from ultralytics import YOLO
import cvzone
import sqlite3
from datetime import datetime

# Load slot data
with open("slot_data.pkl", "rb") as f:
    data = pickle.load(f)
    polylines, area_numbers = data['polylines'], data['area_numbers']

# Load COCO class names
with open("coco.txt", "r") as my_file:
    class_list = my_file.read().strip().split("\n")

def detect_vehicles(results, frame):
    """
    Processes YOLO detections from the Detections object.
    Expects:
      - results["model_predictions"].xyxy: NumPy array of shape (n,4) [x1, y1, x2, y2]
      - results["model_predictions"].data['class_name']: array of class names
    Returns a list of dicts for detections of class "car" with:
      - "center": center point (x, y)
      - "bbox": (x1, y1, x2, y2)
    """
    predictions = results["model_predictions"]
    xyxy = predictions.xyxy  # shape (n, 4)
    class_names = predictions.data['class_name']
    confidence = predictions.data.get('confidence', [1.0] * len(class_names))


    detection_list = []
    for i in range(xyxy.shape[0]):
        if class_names[i].lower() in ["car", "truck", "vehicle"]:
            if confidence[i] > 0.5:
                x1, y1, x2, y2 = xyxy[i]
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                detection_list.append((center_x, center_y))
    return detection_list

def custom_sink(result, video_frame):
            # We'll open a DB connection once per loop; you could optimize further if desired


    visualization = result["label_visualization"]
    # Create a resized copy of the numpy image
    resized_image = visualization.numpy_image

    # # Use the resized image for display and further processing
    # cv2.imshow("Video Feed", resized_image)
    # cv2.waitKey(1)

    vehicle_centers = detect_vehicles(result, resized_image)

    # We'll open a DB connection once per loop; you could optimize further if desired

    conn = sqlite3.connect("parking.db")
    cursor = conn.cursor()
    now = datetime.now()
    login_time = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")

    # occupied_slots = set()

    for idx, polyline in enumerate(polylines):
        slot_no = idx + 1
        # 1) Fetch current slot status to determine color for polylines
        cursor.execute("SELECT status FROM Slots WHERE slot_no = ?", (slot_no,))
        row = cursor.fetchone()

        if row:
            current_status = row[0].lower()
        else:
            current_status = 'empty'  # Fallback if not found (shouldn't happen if DB is correct)

        # Set polyline color based on current_status
        if current_status == 'occupied':
            color = (0, 0, 255)     # Red
        elif current_status == 'waiting':
            color = (0, 255, 255)  # Yellow
        else:
            color = (0, 255, 0)    # Green (empty by default)

        # Draw the slot region on the frame
        cv2.polylines(resized_image, [np.array(polyline)], isClosed=True, color=color, thickness=2)
        #cv2.polylines(resized_image, [polyline], isClosed=True, color=(0, 255, 0), thickness=2)
        #cvzone.putTextRect(resized_image, f'{area_numbers[idx]}', tuple(polyline[0]), 1, 1)

        # Display slot number text near the first point of the polyline or a chosen coordinate
        slot_label = f"Slot {slot_no}"
        slot_coords = polyline[0]  # e.g., top-left corner of the polygon
        cv2.putText(resized_image, slot_label, tuple(slot_coords), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2)


        # for (cx, cy) in vehicle_centers:
        #     # Draw a red circle for the vehicle center
        #     cv2.circle(resized_image, (cx, cy), 5, (0, 0, 255), -1)
        #     if cv2.pointPolygonTest(np.array(polyline), (cx, cy), False) > 0:
        #         occupied_slots.add(idx + 1)
        #         cv2.polylines(resized_image, [polyline], isClosed=True, color=(0, 0, 255), thickness=2)

# 2) Check if a vehicle is detected in this slot
        found_vehicle = False
        for (cx, cy) in vehicle_centers:
            if cv2.pointPolygonTest(np.array(polyline), (cx, cy), False) > 0:
                found_vehicle = True

                # If the slot is empty or waiting, we can mark it occupied
                if current_status in ["empty", "waiting"]:
                    # Check if there's an active Occupied record
                    cursor.execute(
                        "SELECT record_id FROM Occupied WHERE slot_id = ? AND logout_time IS NULL",
                        (slot_no,)
                    )
                    active_record = cursor.fetchone()
                    if not active_record:
                        # Retrieve the plate from the slot table
                        cursor.execute("SELECT car_license_plate FROM Slots WHERE slot_no = ?", (slot_no,))
                        row = cursor.fetchone()
                        user_id = None
                        if row and row[0]:
                            plate = row[0]
                            # Look up user by plate
                            cursor.execute("SELECT user_id FROM Users WHERE vehicle_no = ?", (plate,))
                            found_user = cursor.fetchone()
                            if found_user:
                                user_id = found_user[0]
                        # Insert a new Occupied record and update slot
                        cursor.execute(
                            "UPDATE Slots SET status = 'occupied' WHERE slot_no = ?",
                            (slot_no,)  # Replace with an actual plate if known
                        )
                        conn.commit()
                        cursor.execute(
                            "INSERT INTO Occupied (login_time, logout_time, date, slot_id, user_id) VALUES (?, NULL, ?, ?, ?)",
                            (login_time, date_str, slot_no, user_id)
                        )
                        conn.commit()
                # Once a vehicle is found in this slot, no need to check more vehicles
                break
        # 3) If no vehicle is found in this slot region, possibly reset to empty
        if not found_vehicle:
            # If it's currently 'occupied' with no vehicle found, assume the car left
            if current_status == 'occupied':
                cursor.execute(
                    "UPDATE Slots SET status = 'empty', car_license_plate = NULL WHERE slot_no = ?",
                    (slot_no,)
                )
                conn.commit()
                # Update the Occupied record's logout_time if it's still NULL
                cursor.execute(
                    "UPDATE Occupied SET logout_time = ? WHERE slot_id = ? AND logout_time IS NULL",
                    (login_time, slot_no)
                )
                conn.commit()

    conn.close()

    # Optionally display the frame (comment out if running headless)
    # try:
    #     cv2.imshow("Parking Camera Feed", resized_image)
    #     if cv2.waitKey(1) & 0xFF == ord("q"):
    #         break
    # except cv2.error:
    #     pass

    # total_slots = len(polylines)
    # car_count = len(occupied_slots)
    # free_slots = total_slots - car_count

    # cvzone.putTextRect(resized_image, f'Car Count: {car_count} {occupied_slots}', (50, 60), 2, 2)
    # cvzone.putTextRect(resized_image, f'Free Slots: {free_slots}', (50, 120), 2, 2)

    cv2.imshow('FRAME', resized_image)
    cv2.waitKey(1)


def main():
    from inference import InferencePipeline
    pipeline = InferencePipeline.init_with_workflow(
        api_key="1oMACvhnGJxsmhKPwZsZ",                            #"7RdO6RJ5gzrJPPIWh4Gm",
        workspace_name="apoorvas-workflows",          #"darpan-neve-gigwd",
        workflow_id="slot-car",
        video_reference="./parking.mp4",
        max_fps=30,
        on_prediction=custom_sink
    )
    pipeline.start()
    pipeline.join()

if __name__ == "__main__":
    main()

