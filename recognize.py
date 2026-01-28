"""
Face Recognition Attendance System - Recognition Module

Performs real-time face recognition with:
- Anti-spoofing detection (motion-based liveness)
- Lighting-aware recognition
- Attendance punch-in/out logging

REQUIREMENTS:
- opencv-python
- face_recognition
- numpy
- pandas
"""

import cv2
import face_recognition
import numpy as np
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configuration
ENCODING_PATH = "encodings"
ATTENDANCE_FILE = "attendance.csv"
RECOGNITION_THRESHOLD = 0.6  # Lower = stricter matching
CONFIDENCE_THRESHOLD = 0.55   # Minimum confidence for acceptance
LIVENESS_THRESHOLD = 15       # Minimum motion pixels for liveness

# Anti-spoofing configuration
MOTION_HISTORY_SIZE = 10      # Number of frames to track for motion
MIN_FACE_PRESENCE = 5         # Minimum frames face must be present

class LivenessDetector:
    """
    Detects spoofing attempts using motion-based liveness detection.
    A real face will show natural head movement; a photo/video will not.
    """
    
    def __init__(self, history_size=MOTION_HISTORY_SIZE):
        self.motion_history = []
        self.history_size = history_size
        self.face_presence_count = 0
        self.is_alive = False
    
    def detect_motion(self, frame, face_location):
        """Detect motion in the face region."""
        if face_location is None:
            self.face_presence_count = 0
            self.motion_history = []
            return False
        
        self.face_presence_count += 1
        top, right, bottom, left = face_location
        
        # Extract face region
        face_region = frame[top:bottom, left:right]
        
        # Calculate optical flow for motion detection
        if len(self.motion_history) == 0:
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            self.motion_history.append(gray)
            return False
        
        # Compare with previous frame
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Calculate difference between frames
        prev_gray = self.motion_history[-1]
        
        # Resize to match
        if prev_gray.shape != gray.shape:
            prev_gray = cv2.resize(prev_gray, (gray.shape[1], gray.shape[0]))
        
        diff = cv2.absdiff(prev_gray, gray)
        motion_pixels = np.sum(diff > 10)  # Pixels with significant change
        
        self.motion_history.append(gray)
        if len(self.motion_history) > self.history_size:
            self.motion_history.pop(0)
        
        # Determine liveness: real face should show some motion over time
        if len(self.motion_history) >= 3:
            total_motion = 0
            for i in range(1, len(self.motion_history)):
                prev_frame = self.motion_history[i-1]
                curr_frame = self.motion_history[i]
                
                # Ensure frames have same size
                if prev_frame.shape != curr_frame.shape:
                    curr_frame = cv2.resize(curr_frame, (prev_frame.shape[1], prev_frame.shape[0]))
                
                frame_diff = cv2.absdiff(prev_frame, curr_frame)
                total_motion += np.sum(frame_diff > 10)
            
            avg_motion = total_motion / (len(self.motion_history) - 1)
            self.is_alive = avg_motion > LIVENESS_THRESHOLD
        
        return self.is_alive
    
    def reset(self):
        """Reset detector state."""
        self.motion_history = []
        self.face_presence_count = 0
        self.is_alive = False

class AttendanceSystem:
    """Manages attendance logging and face recognition."""
    
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.load_known_faces()
        self.create_attendance_file()
        self.liveness_detector = LivenessDetector()
        self.last_marked = {}  # Prevent duplicate marking
    
    def load_known_faces(self):
        """Load all registered face encodings."""
        if not os.path.exists(ENCODING_PATH):
            print(f"⚠ Encodings directory not found: {ENCODING_PATH}")
            return
        
        for file in os.listdir(ENCODING_PATH):
            if file.endswith(".npy"):
                try:
                    encoding = np.load(f"{ENCODING_PATH}/{file}")
                    name = file.replace(".npy", "")
                    self.known_encodings.append(encoding)
                    self.known_names.append(name)
                    print(f"✓ Loaded: {name}")
                except Exception as e:
                    print(f"✗ Error loading {file}: {e}")
        
        if len(self.known_encodings) == 0:
            print("\n⚠ No registered faces found!")
            print("Please run register.py first to register users.")
    
    def create_attendance_file(self):
        """Create attendance CSV if it doesn't exist."""
        if not os.path.exists(ATTENDANCE_FILE):
            df = pd.DataFrame(columns=["Name", "Date", "Punch_In", "Punch_Out", "Confidence", "Liveness_Check"])
            df.to_csv(ATTENDANCE_FILE, index=False)
            print(f"✓ Created attendance file: {ATTENDANCE_FILE}")
    
    def get_brightness_level(self, frame):
        """Calculate frame brightness."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return np.mean(gray)
    
    def recognize_face(self, frame, rgb_frame):
        """
        Recognize faces in frame with spoof detection.
        Returns: (name, distance, is_alive, confidence)
        """
        faces = face_recognition.face_locations(rgb_frame, model="hog")
        
        if len(faces) == 0:
            return None, 1.0, False, 0.0
        
        if len(faces) > 1:
            # Multiple faces - potential spoofing attempt
            return "MULTIPLE_FACES", 1.0, False, 0.0
        
        face_location = faces[0]
        
        # Check liveness
        is_alive = self.liveness_detector.detect_motion(frame, face_location)
        
        # Get face encoding
        face_encodings = face_recognition.face_encodings(rgb_frame, faces)
        if len(face_encodings) == 0:
            return None, 1.0, is_alive, 0.0
        
        face_encoding = face_encodings[0]
        
        # Compare with known faces
        if len(self.known_encodings) == 0:
            return "UNKNOWN", 1.0, is_alive, 0.0
        
        distances = face_recognition.face_distance(self.known_encodings, face_encoding)
        min_distance = np.min(distances)
        min_index = np.argmin(distances)
        
        # Calculate confidence (inverse of distance)
        confidence = 1.0 - min_distance
        
        # Recognize if distance is below threshold AND confidence is sufficient
        if min_distance < RECOGNITION_THRESHOLD and confidence > CONFIDENCE_THRESHOLD:
            name = self.known_names[min_index]
        else:
            name = "UNKNOWN"
        
        return name, min_distance, is_alive, confidence
    
    def mark_attendance(self, name, is_alive):
        """Mark attendance with liveness verification."""
        if not is_alive:
            return "REJECTED_SPOOF"
        
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        # Read CSV with all columns as string type
        df = pd.read_csv(ATTENDANCE_FILE, dtype=str)
        
        record = df[(df["Name"] == name) & (df["Date"] == date)]
        
        if record.empty:
            # New punch-in - prevent duplicate punch-in within 5 seconds
            key = f"{name}_{date}"
            if key in self.last_marked:
                time_diff = (datetime.now() - self.last_marked[key]).total_seconds()
                if time_diff < 5:
                    return "DUPLICATE"
            
            # Create new punch-in record
            df.loc[len(df)] = [name, date, time_str, "", "HIGH", "VERIFIED"]
            status = "PUNCH_IN"
            self.last_marked[key] = datetime.now()
        else:
            # Punch-out logic
            punch_out_val = str(record.iloc[0]["Punch_Out"]).strip()
            # Check if punch_out is empty
            if punch_out_val == "" or punch_out_val == "nan":
                df.loc[record.index[0], "Punch_Out"] = time_str
                df.loc[record.index[0], "Liveness_Check"] = "VERIFIED"
                status = "PUNCH_OUT"
                # Clear the duplicate timer on punch-out
                key = f"{name}_{date}"
                if key in self.last_marked:
                    del self.last_marked[key]
            else:
                return "ALREADY_MARKED"
        
        df.to_csv(ATTENDANCE_FILE, index=False)
        
        return status

def main():
    """Main recognition loop."""
    print("\n" + "="*70)
    print("FACE RECOGNITION ATTENDANCE SYSTEM")
    print("="*70)
    
    system = AttendanceSystem()
    
    if len(system.known_encodings) == 0:
        print("\n❌ No registered faces found!")
        print("Please run register.py first to register users.\n")
        return
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera!")
        return
    
    print("\n📸 Camera initialized")
    print("-"*70)
    print("Controls:")
    print("  'a' - Mark attendance (punch-in/out)")
    print("  'q' - Quit")
    print("  'r' - Reset liveness detector")
    print("-"*70 + "\n")
    
    # Get screen dimensions for display
    ret, frame = cap.read()
    if ret:
        height, width = frame.shape[:2]
    else:
        height, width = 480, 640
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break
        
        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get brightness
        brightness = system.get_brightness_level(frame)
        brightness_status = "Low" if brightness < 85 else ("Medium" if brightness < 170 else "High")
        
        # Recognize face
        name, distance, is_alive, confidence = system.recognize_face(frame, rgb_frame)
        
        # Draw information
        cv2.putText(frame, f"Brightness: {brightness_status} ({brightness:.0f})", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"Liveness: {'VERIFIED' if is_alive else 'CHECKING'}", 
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if is_alive else (0, 165, 255), 2)
        
        # Draw face detection
        faces = face_recognition.face_locations(rgb_frame)
        
        if len(faces) == 0:
            cv2.putText(frame, "No face detected", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        elif len(faces) > 1:
            cv2.putText(frame, f"Multiple faces: {len(faces)} (SPOOF RISK)", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        else:
            top, right, bottom, left = faces[0]
            
            # Color based on recognition status
            if name == "UNKNOWN":
                color = (0, 0, 255)  # Red
            elif name == "MULTIPLE_FACES":
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 0)  # Green
            
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Show recognition result
            if name != "UNKNOWN" and name != "MULTIPLE_FACES":
                label = f"{name} ({confidence:.2f})"
                cv2.putText(frame, label, (left, top - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(frame, f"Distance: {distance:.3f}", (left, bottom + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                cv2.putText(frame, "UNKNOWN", (left, top - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Instructions
        cv2.putText(frame, "Press 'a' to mark attendance, 'q' to quit", 
                   (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Face Recognition Attendance System", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('a'):
            if name and name != "UNKNOWN" and name != "MULTIPLE_FACES" and is_alive:
                status = system.mark_attendance(name, is_alive)
                
                if status == "PUNCH_IN":
                    print(f"✅ Punch-In marked for {name} at {datetime.now().strftime('%H:%M:%S')}")
                elif status == "PUNCH_OUT":
                    print(f"✅ Punch-Out marked for {name} at {datetime.now().strftime('%H:%M:%S')}")
                elif status == "DUPLICATE":
                    print(f"⚠ Duplicate marking ignored for {name}")
                elif status == "ALREADY_MARKED":
                    print(f"⚠ Attendance already marked for {name} today")
                elif status == "REJECTED_SPOOF":
                    print(f"❌ Spoof detected! Attendance rejected.")
            else:
                reason = ""
                if name == "UNKNOWN":
                    reason = "face not recognized"
                elif name == "MULTIPLE_FACES":
                    reason = "multiple faces detected"
                elif not is_alive:
                    reason = "liveness check failed"
                print(f"❌ Cannot mark attendance: {reason}")
        
        elif key == ord('r'):
            print("🔄 Resetting liveness detector...")
            system.liveness_detector.reset()
        
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "="*70)
    print("Attendance system closed.")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
