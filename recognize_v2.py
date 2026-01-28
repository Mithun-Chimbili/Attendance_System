"""
Face Recognition Attendance System - Recognition Module.

Performs real-time face recognition with:
- Anti-spoofing detection (motion-based liveness)
- Lighting-aware recognition
- Attendance punch-in/out logging

Follows Google Python style guide and industry standards.
"""

import cv2
import face_recognition
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
import logging

from config import SystemConfig, DEFAULT_CONFIG
from logger_config import setup_logging, get_logger

logger = get_logger("recognize")


@dataclass
class RecognitionResult:
    """Data class for face recognition results."""
    name: Optional[str]
    distance: float
    is_alive: bool
    confidence: float
    timestamp: datetime


class LivenessDetector:
    """
    Detects spoofing attempts using motion-based liveness detection.
    
    A real face will show natural head movement; a photo/video will not.
    Uses optical flow and frame differencing to detect motion.
    
    Args:
        config: SystemConfig instance
    """
    
    def __init__(self, config: SystemConfig) -> None:
        """Initialize liveness detector."""
        self.config = config.liveness
        self.motion_history: list = []
        self.face_presence_count: int = 0
        self.is_alive: bool = False
        logger.debug("LivenessDetector initialized")
    
    def detect_motion(self, frame: np.ndarray, face_location: Optional[Tuple]) -> bool:
        """
        Detect motion in the face region.
        
        Args:
            frame: Input frame (BGR)
            face_location: Face bounding box (top, right, bottom, left)
        
        Returns:
            bool: True if face is detected as alive (has motion)
        """
        if face_location is None:
            self.face_presence_count = 0
            self.motion_history = []
            return False
        
        self.face_presence_count += 1
        top, right, bottom, left = face_location
        
        # Extract and validate face region
        face_region = frame[top:bottom, left:right]
        if face_region.size == 0:
            logger.warning("Invalid face region extracted")
            return False
        
        # Initialize motion history
        if len(self.motion_history) == 0:
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            self.motion_history.append(gray)
            return False
        
        # Convert to grayscale
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Get previous frame
        prev_gray = self.motion_history[-1]
        
        # Ensure frames have same size
        if prev_gray.shape != gray.shape:
            prev_gray = cv2.resize(prev_gray, (gray.shape[1], gray.shape[0]))
        
        # Calculate frame difference
        diff = cv2.absdiff(prev_gray, gray)
        motion_pixels = np.sum(diff > self.config.motion_pixel_threshold)
        
        # Update motion history
        self.motion_history.append(gray)
        if len(self.motion_history) > self.config.motion_history_size:
            self.motion_history.pop(0)
        
        # Determine liveness
        if len(self.motion_history) >= 3:
            total_motion = self._calculate_total_motion()
            avg_motion = total_motion / (len(self.motion_history) - 1)
            self.is_alive = avg_motion > self.config.liveness_threshold
            logger.debug(f"Motion detected: {avg_motion:.2f} (threshold: {self.config.liveness_threshold})")
        
        return self.is_alive
    
    def _calculate_total_motion(self) -> float:
        """Calculate total motion across motion history."""
        total_motion = 0.0
        for i in range(1, len(self.motion_history)):
            prev_frame = self.motion_history[i-1]
            curr_frame = self.motion_history[i]
            
            # Ensure frames have same size
            if prev_frame.shape != curr_frame.shape:
                curr_frame = cv2.resize(curr_frame, (prev_frame.shape[1], prev_frame.shape[0]))
            
            frame_diff = cv2.absdiff(prev_frame, curr_frame)
            total_motion += np.sum(frame_diff > self.config.motion_pixel_threshold)
        
        return total_motion
    
    def reset(self) -> None:
        """Reset detector state."""
        self.motion_history = []
        self.face_presence_count = 0
        self.is_alive = False
        logger.debug("LivenessDetector reset")


class AttendanceSystem:
    """
    Manages attendance logging and face recognition.
    
    Args:
        config: SystemConfig instance
    """
    
    def __init__(self, config: SystemConfig = DEFAULT_CONFIG) -> None:
        """Initialize attendance system."""
        self.config = config
        self.known_encodings: list = []
        self.known_names: list = []
        self.liveness_detector = LivenessDetector(config)
        self.last_marked: Dict[str, datetime] = {}
        
        self.load_known_faces()
        self.create_attendance_file()
        logger.info("AttendanceSystem initialized")
    
    def load_known_faces(self) -> None:
        """
        Load all registered face encodings from disk.
        
        Raises:
            FileNotFoundError: If encoding path doesn't exist
        """
        if not self.config.encoding_path.exists():
            logger.warning(f"Encodings directory not found: {self.config.encoding_path}")
            return
        
        for file in self.config.encoding_path.glob("*.npy"):
            try:
                encoding = np.load(file)
                name = file.stem
                self.known_encodings.append(encoding)
                self.known_names.append(name)
                logger.info(f"Loaded encoding for: {name}")
            except Exception as e:
                logger.error(f"Error loading {file.name}: {e}")
        
        if not self.known_encodings:
            logger.warning("No registered faces found!")
    
    def create_attendance_file(self) -> None:
        """Create attendance CSV if it doesn't exist."""
        if not self.config.attendance_file.exists():
            df = pd.DataFrame(
                columns=["Name", "Date", "Punch_In", "Punch_Out", "Confidence", "Liveness_Check"]
            )
            df.to_csv(self.config.attendance_file, index=False)
            logger.info(f"Created attendance file: {self.config.attendance_file}")
    
    def get_brightness_level(self, frame: np.ndarray) -> float:
        """
        Calculate frame brightness.
        
        Args:
            frame: Input frame (BGR)
        
        Returns:
            float: Average brightness level (0-255)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))
    
    def get_brightness_status(self, brightness: float) -> str:
        """
        Get brightness status based on threshold.
        
        Args:
            brightness: Brightness value
        
        Returns:
            str: "Low", "Medium", or "High"
        """
        if brightness < self.config.brightness.low_threshold:
            return "Low"
        elif brightness < self.config.brightness.medium_threshold:
            return "Medium"
        return "High"
    
    def recognize_face(self, frame: np.ndarray, rgb_frame: np.ndarray) -> RecognitionResult:
        """
        Recognize faces in frame with spoof detection.
        
        Args:
            frame: Input frame (BGR)
            rgb_frame: Input frame (RGB)
        
        Returns:
            RecognitionResult: Recognition result
        """
        try:
            faces = face_recognition.face_locations(
                rgb_frame,
                model=self.config.face_detection_model
            )
            
            if len(faces) == 0:
                return RecognitionResult(None, 1.0, False, 0.0, datetime.now())
            
            if len(faces) > 1:
                logger.warning(f"Multiple faces detected: {len(faces)}")
                return RecognitionResult("MULTIPLE_FACES", 1.0, False, 0.0, datetime.now())
            
            face_location = faces[0]
            
            # Check liveness
            is_alive = self.liveness_detector.detect_motion(frame, face_location)
            
            # Get face encoding
            face_encodings = face_recognition.face_encodings(rgb_frame, faces)
            if not face_encodings:
                return RecognitionResult(None, 1.0, is_alive, 0.0, datetime.now())
            
            face_encoding = face_encodings[0]
            
            # Compare with known faces
            if not self.known_encodings:
                logger.warning("No known faces loaded")
                return RecognitionResult("UNKNOWN", 1.0, is_alive, 0.0, datetime.now())
            
            distances = face_recognition.face_distance(self.known_encodings, face_encoding)
            min_distance = float(np.min(distances))
            min_index = int(np.argmin(distances))
            
            # Calculate confidence
            confidence = 1.0 - min_distance
            
            # Recognize if within thresholds
            if (min_distance < self.config.recognition.recognition_threshold and
                confidence > self.config.recognition.confidence_threshold):
                name = self.known_names[min_index]
            else:
                name = "UNKNOWN"
            
            return RecognitionResult(name, min_distance, is_alive, confidence, datetime.now())
        
        except Exception as e:
            logger.error(f"Error during face recognition: {e}")
            return RecognitionResult(None, 1.0, False, 0.0, datetime.now())
    
    def mark_attendance(self, name: str, is_alive: bool) -> str:
        """
        Mark attendance with liveness verification.
        
        Args:
            name: User name
            is_alive: Liveness check result
        
        Returns:
            str: Status ("PUNCH_IN", "PUNCH_OUT", "DUPLICATE", "ALREADY_MARKED", "REJECTED_SPOOF")
        """
        if not is_alive:
            logger.warning(f"Spoof detected for {name}")
            return "REJECTED_SPOOF"
        
        try:
            now = datetime.now()
            date = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            # Read CSV with all columns as string type
            df = pd.read_csv(self.config.attendance_file, dtype=str)
            
            record = df[(df["Name"] == name) & (df["Date"] == date)]
            
            if record.empty:
                # New punch-in - prevent duplicate within time window
                key = f"{name}_{date}"
                if key in self.last_marked:
                    time_diff = (datetime.now() - self.last_marked[key]).total_seconds()
                    if time_diff < self.config.recognition.duplicate_detection_window:
                        logger.info(f"Duplicate punch-in prevented for {name}")
                        return "DUPLICATE"
                
                # Create new punch-in record
                new_record = pd.DataFrame([{
                    "Name": name,
                    "Date": date,
                    "Punch_In": time_str,
                    "Punch_Out": "",
                    "Confidence": "HIGH",
                    "Liveness_Check": "VERIFIED"
                }])
                df = pd.concat([df, new_record], ignore_index=True)
                status = "PUNCH_IN"
                self.last_marked[key] = datetime.now()
                logger.info(f"Punch-In recorded for {name} at {time_str}")
            
            else:
                # Punch-out logic
                punch_out_val = str(record.iloc[0]["Punch_Out"]).strip()
                if punch_out_val == "" or punch_out_val == "nan":
                    df.loc[record.index[0], "Punch_Out"] = time_str
                    df.loc[record.index[0], "Liveness_Check"] = "VERIFIED"
                    status = "PUNCH_OUT"
                    logger.info(f"Punch-Out recorded for {name} at {time_str}")
                    
                    # Clear duplicate timer
                    key = f"{name}_{date}"
                    if key in self.last_marked:
                        del self.last_marked[key]
                else:
                    logger.info(f"Attendance already marked for {name} on {date}")
                    return "ALREADY_MARKED"
            
            df.to_csv(self.config.attendance_file, index=False)
            return status
        
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")
            return "ERROR"


def main() -> None:
    """Main recognition loop."""
    # Setup logging
    setup_logging(log_level=logging.INFO)
    
    logger.info("Starting Face Recognition Attendance System")
    logger.info("=" * 70)
    
    system = AttendanceSystem(DEFAULT_CONFIG)
    
    if not system.known_encodings:
        logger.error("No registered faces found!")
        logger.info("Please run register.py first to register users.")
        return
    
    cap = cv2.VideoCapture(DEFAULT_CONFIG.camera_index)
    if not cap.isOpened():
        logger.error("Could not open camera!")
        return
    
    logger.info("Camera initialized")
    logger.info("-" * 70)
    logger.info("Controls:")
    logger.info("  'a' - Mark attendance (punch-in/out)")
    logger.info("  'q' - Quit")
    logger.info("  'r' - Reset liveness detector")
    logger.info("-" * 70)
    
    print("\n📸 Camera initialized")
    print("-" * 70)
    print("Controls:")
    print("  'a' - Mark attendance (punch-in/out)")
    print("  'q' - Quit")
    print("  'r' - Reset liveness detector")
    print("-" * 70 + "\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read frame")
            break
        
        # Mirror effect
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get brightness
        brightness = system.get_brightness_level(frame)
        brightness_status = system.get_brightness_status(brightness)
        
        # Recognize face
        result = system.recognize_face(frame, rgb_frame)
        
        # Draw information
        cv2.putText(frame, f"Brightness: {brightness_status} ({brightness:.0f})",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f"Liveness: {'VERIFIED' if result.is_alive else 'CHECKING'}",
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                   (0, 255, 0) if result.is_alive else (0, 165, 255), 2)
        
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
            if result.name == "UNKNOWN":
                color = (0, 0, 255)  # Red
            elif result.name == "MULTIPLE_FACES":
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 0)  # Green
            
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Show recognition result
            if result.name and result.name not in ["UNKNOWN", "MULTIPLE_FACES"]:
                label = f"{result.name} ({result.confidence:.2f})"
                cv2.putText(frame, label, (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(frame, f"Distance: {result.distance:.3f}", (left, bottom + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                cv2.putText(frame, "UNKNOWN", (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Instructions
        cv2.putText(frame, "Press 'a' to mark attendance, 'q' to quit",
                   (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                   (255, 255, 255), 2)
        
        cv2.imshow("Face Recognition Attendance System", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('a'):
            if (result.name and result.name not in ["UNKNOWN", "MULTIPLE_FACES"]
                and result.is_alive):
                status = system.mark_attendance(result.name, result.is_alive)
                
                if status == "PUNCH_IN":
                    print(f"✅ Punch-In marked for {result.name} at {datetime.now().strftime('%H:%M:%S')}")
                elif status == "PUNCH_OUT":
                    print(f"✅ Punch-Out marked for {result.name} at {datetime.now().strftime('%H:%M:%S')}")
                elif status == "DUPLICATE":
                    print(f"⚠ Duplicate marking ignored for {result.name}")
                elif status == "ALREADY_MARKED":
                    print(f"⚠ Attendance already marked for {result.name} today")
                elif status == "REJECTED_SPOOF":
                    print(f"❌ Spoof detected! Attendance rejected.")
            else:
                reason = "unknown"
                if result.name == "UNKNOWN":
                    reason = "face not recognized"
                elif result.name == "MULTIPLE_FACES":
                    reason = "multiple faces detected"
                elif not result.is_alive:
                    reason = "liveness check failed"
                print(f"❌ Cannot mark attendance: {reason}")
        
        elif key == ord('r'):
            print("🔄 Resetting liveness detector...")
            system.liveness_detector.reset()
        
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    logger.info("Attendance system closed.")
    print("\n" + "=" * 70)
    print("Attendance system closed.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
