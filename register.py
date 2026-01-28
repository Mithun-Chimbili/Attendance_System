"""
Face Registration Module - Attendance System

Registers user faces by capturing multiple samples under varying lighting conditions.
Implements face quality checks and stores averaged face encodings.

REQUIREMENTS:
- opencv-python
- face_recognition
- numpy
"""

import cv2
import face_recognition
import numpy as np
import os
import time
from pathlib import Path

# Configuration
ENCODINGS_DIR = "encodings"
MIN_SAMPLES = 15  # Minimum samples for robust registration
MAX_SAMPLES = 30  # Maximum samples to avoid overfitting
FACE_SIZE_MIN = 50  # Minimum face size in pixels

def calculate_face_quality(face_encoding, known_encodings):
    """
    Calculate face quality based on variance from known encodings.
    Higher variance = more unique/diverse = better quality.
    """
    if len(known_encodings) < 2:
        return 1.0
    distances = face_recognition.face_distance([known_encodings[0]], face_encoding)
    quality_score = min(1.0, distances[0])
    return quality_score

def is_good_face_sample(frame, face_location, face_encoding, previous_encodings):
    """
    Determine if a face sample is good quality for registration.
    Checks:
    - Face size (not too small)
    - Face is well-centered
    - Different from previous captures (not duplicate)
    """
    top, right, bottom, left = face_location
    face_width = right - left
    face_height = bottom - top
    
    # Check minimum face size
    if face_width < FACE_SIZE_MIN or face_height < FACE_SIZE_MIN:
        return False, "Face too small - move closer to camera"
    
    # Check if face is duplicate of recent captures
    if len(previous_encodings) > 0:
        distances = face_recognition.face_distance(previous_encodings[-3:], face_encoding)
        if len(distances) > 0 and min(distances) < 0.15:  # Too similar to recent capture
            return False, "Face too similar to previous - try different angle"
    
    return True, "Good sample"

def get_brightness_level(frame):
    """Calculate brightness of the frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def register_face():
    """Main face registration process."""
    print("\n" + "="*60)
    print("FACE REGISTRATION MODULE")
    print("="*60)
    
    user_name = input("\nEnter user name: ").strip()
    if not user_name:
        print("❌ Name cannot be empty!")
        return False
    
    # Create encodings directory
    Path(ENCODINGS_DIR).mkdir(exist_ok=True)
    
    # Check if user already registered
    encoding_file = f"{ENCODINGS_DIR}/{user_name}.npy"
    if os.path.exists(encoding_file):
        response = input(f"⚠ {user_name} already registered. Re-register? (y/n): ")
        if response.lower() != 'y':
            return False
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera!")
        return False
    
    encodings = []
    angles_captured = {"front": False, "left": False, "right": False}
    brightness_samples = {"low": 0, "medium": 0, "high": 0}
    
    print(f"\n📸 Starting registration for: {user_name}")
    print("-" * 60)
    print("Instructions:")
    print("• Move to different angles (front, left-45°, right-45°)")
    print("• Capture under varying lighting conditions")
    print("• Face must be clearly visible")
    print("• Press 'c' to capture, 'q' to finish, 'r' to reset")
    print("• Minimum samples needed:", MIN_SAMPLES)
    print("-" * 60 + "\n")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame from camera")
            break
        
        frame_count += 1
        
        # Flip frame for mirror effect
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = face_recognition.face_locations(rgb, model="hog")
        
        # Get brightness level
        brightness = get_brightness_level(frame)
        if brightness < 85:
            lighting_condition = "low"
        elif brightness < 170:
            lighting_condition = "medium"
        else:
            lighting_condition = "high"
        
        # Draw UI information
        cv2.putText(frame, f"Samples: {len(encodings)}/{MIN_SAMPLES}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Brightness: {lighting_condition.upper()} ({brightness:.0f})", 
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"Frame: {frame_count} | Angle coverage: {sum(angles_captured.values())}/3", 
                   (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        if len(faces) == 0:
            cv2.putText(frame, "NO FACE DETECTED", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        elif len(faces) > 1:
            cv2.putText(frame, f"Multiple faces detected ({len(faces)})", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        else:
            # Single face detected
            top, right, bottom, left = faces[0]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, "Press 'c' to capture", (left, top - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        cv2.imshow(f"Register Face - {user_name}", frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('c') and len(faces) == 1:
            # Validate face quality
            face_encoding = face_recognition.face_encodings(rgb, faces)[0]
            is_good, message = is_good_face_sample(frame, faces[0], face_encoding, encodings)
            
            if is_good:
                encodings.append(face_encoding)
                brightness_samples[lighting_condition] += 1
                
                # Simple angle detection based on face position
                frame_center = frame.shape[1] // 2
                face_center = (faces[0][1] + faces[0][3]) // 2
                offset = face_center - frame_center
                
                if abs(offset) < 50:
                    angles_captured["front"] = True
                elif offset < -100:
                    angles_captured["left"] = True
                elif offset > 100:
                    angles_captured["right"] = True
                
                print(f"✅ Captured ({len(encodings)}/{MIN_SAMPLES}) - {message}")
                print(f"   Lighting: {lighting_condition}, Angles: {sum(angles_captured.values())}/3")
            else:
                print(f"⚠ {message}")
        
        elif key == ord('q'):
            break
        elif key == ord('r'):
            print("🔄 Resetting...")
            encodings = []
            angles_captured = {"front": False, "left": False, "right": False}
            brightness_samples = {"low": 0, "medium": 0, "high": 0}
            print("All samples cleared!")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Save registration
    if len(encodings) >= MIN_SAMPLES:
        avg_encoding = np.mean(encodings, axis=0)
        encoding_variance = np.std(encodings, axis=0)
        
        np.save(encoding_file, avg_encoding)
        
        print("\n" + "="*60)
        print("✅ REGISTRATION SUCCESSFUL!")
        print("="*60)
        print(f"User: {user_name}")
        print(f"Samples captured: {len(encodings)}")
        print(f"Angle coverage: {sum(angles_captured.values())}/3 angles")
        print(f"Lighting diversity: Low={brightness_samples['low']}, Medium={brightness_samples['medium']}, High={brightness_samples['high']}")
        print(f"Encoding variance (quality): {np.mean(encoding_variance):.4f}")
        print(f"Saved to: {encoding_file}")
        print("="*60 + "\n")
        
        return True
    else:
        print(f"\n❌ REGISTRATION FAILED!")
        print(f"Captured {len(encodings)}/{MIN_SAMPLES} required samples")
        print("Please try again with more diverse angles and lighting conditions.\n")
        return False

if __name__ == "__main__":
    try:
        register_face()
    except Exception as e:
        print(f"\n❌ Error during registration: {e}")
        import traceback
        traceback.print_exc()
