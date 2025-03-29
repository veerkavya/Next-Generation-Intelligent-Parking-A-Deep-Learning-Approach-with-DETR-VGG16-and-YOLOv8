import cv2
import numpy as np
import cvzone
import pickle
import os

# Open video file (or update to your IP camera URL if needed)
cap = cv2.VideoCapture('easy1.mp4')

drawing = False
area_numbers = []

# Attempt to load existing data if available
if os.path.exists("slot_data.pkl"):
    try:
        with open("slot_data.pkl", "rb") as f:
            data = pickle.load(f)
            polylines, area_numbers = data['polylines'], data['area_numbers']
        print("Loaded existing slot data.")
    except Exception as e:
        print("Error loading existing data:", e)
        polylines = []
else:
    polylines = []

points = []
# Global variable to store the current frame copy for preview
current_frame_copy = None

def get_next_slot_number():
    """
    Automatically assigns the next slot number based on already stored numbers.
    Assumes slot numbers are numeric strings.
    """
    if area_numbers:
        next_number = int(max(area_numbers, key=lambda x: int(x))) + 1
    else:
        next_number = 1
    return str(next_number)

# Mouse callback function for drawing polygons
def draw(event, x, y, flags, param):
    global points, drawing, current_frame_copy
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        points = [(x, y)]
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        # Append the new point
        points.append((x, y))
        # Show live drawing feedback: overlay current points on a copy of the frame
        temp_frame = current_frame_copy.copy() if current_frame_copy is not None else None
        if temp_frame is not None and len(points) > 1:
            cv2.polylines(temp_frame, [np.array(points, np.int32)], isClosed=False, color=(0, 255, 255), thickness=2)
            cv2.imshow('FRAME', temp_frame)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        # Final drawn polygon (not necessarily closed)
        temp_poly = np.array(points, np.int32)
        temp_frame = current_frame_copy.copy() if current_frame_copy is not None else None
        if temp_frame is not None:
            # Draw a final preview polygon (closed) for confirmation
            cv2.polylines(temp_frame, [temp_poly], isClosed=True, color=(0, 255, 255), thickness=2)
            cv2.imshow('FRAME', temp_frame)
        # Ask for confirmation before adding the slot
        confirmation = input('Confirm slot? (y/n): ')
        if confirmation.lower() == 'y':
            new_slot_number = get_next_slot_number()
            area_numbers.append(new_slot_number)
            polylines.append(temp_poly)
            print(f"Slot {new_slot_number} added.")
        else:
            print("Slot discarded.")

# Create window and set mouse callback
cv2.namedWindow('FRAME')
cv2.setMouseCallback('FRAME', draw)

while True:
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    frame = cv2.resize(frame, (1020, 500))
    # Update the global current frame copy for use in mouse callback
    current_frame_copy = frame.copy()

    # Draw all saved polylines and their labels on the frame
    for i, polyline in enumerate(polylines):
        cv2.polylines(frame, [polyline], isClosed=True, color=(0, 0, 255), thickness=2)
        cvzone.putTextRect(frame, f'{area_numbers[i]}', tuple(polyline[0]), 1, 1)

    cv2.imshow('FRAME', frame)
    Key = cv2.waitKey(1) & 0xFF

    if Key == ord('s'):
        try:
            with open("slot_data.pkl", "wb") as f:
                data = {'polylines': polylines, 'area_numbers': area_numbers}
                pickle.dump(data, f)
            print("Data saved to slot_data.pkl")
            if os.path.exists("slot_data.pkl"):
                size = os.path.getsize("slot_data.pkl")
                print("File size (bytes):", size)
            else:
                print("File not found after saving!")
        except Exception as e:
            print("Error saving file:", e)

    if Key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
