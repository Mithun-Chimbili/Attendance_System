"""
Face Registration Module - Industry Standard Version.

Registers user faces by capturing multiple samples under varying conditions.
Implements face quality checks and stores averaged face encodings.

Follows Google Python style guide and AIML best practices.
"""

import cv2
import face_recognition
import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional
from dataclasses import dataclass
import logging

from config import SystemConfig, DEFAULT_CONFIG
from logger_config import setup_logging, get_logger

logger = get_logger("register")

# Registration thresholds
MIN_SAMPLES = 15
MAX_SAMPLES = 30
FACE_SIZE_MIN = 50
DUPLICATE_THRESHOLD = 0.15


@dataclass
class RegistrationStats:
    """Statistics for registration process."""
    total_samples: int = 0
    quality_samples: int = 0
    angles: dict = None
    brightness_levels: dict = None
    
    def __post_init__(self):
        """Initialize nested dicts."""
        if self.angles is None:
            self.angles = {"front": 0, "left": 0, "right": 0}
        if self.brightness_levels is None:
            self.brightness_levels = {"low": 0, "medium": 0, "high": 0}


class FaceQualityValidator:
    """Validates face sample quality."""
    
    def __init__(self, config: SystemConfig) -> None:
        """Initialize validator."""
        self.config = config
    
    def validate(
        self,
        frame: np.ndarray,
        face_location: Tuple[int, int, int, int],
        face_encoding: np.ndarray,
        previous_encodings: List[np.ndarray]
    ) -> Tuple[bool, str]:
        """
        Validate face sample quality.
        
        Args:
            frame: Input frame
            face_location: Face bounding box
            face_encoding: Face encoding vector
            previous_encodings: Previous good samples
        
        Returns:
            Tuple of (is_valid, message)
        """
        top, right, bottom, left = face_location
        face_width = right - left
        face_height = bottom - top
        
        # Check minimum face size
        if face_width < FACE_SIZE_MIN or face_height < FACE_SIZE_MIN:
            return False, f"Face too small ({face_width}x{face_height})"
        
        # Check for duplicates
        if previous_encodings:
            distances = face_recognition.face_distance(
                previous_encodings[-3:],
                face_encoding
            )
            if distances.size > 0 and np.min(distances) < DUPLICATE_THRESHOLD:
                return False, "Face too similar to recent sample"
        
        return True, "Quality sample accepted"
    
    def get_brightness_status(self, frame: np.ndarray) -> str:
        """Get brightness level of frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        if brightness < self.config.brightness.low_threshold:
            return "low"
        elif brightness < self.config.brightness.medium_threshold:
            return "medium"
        return "high"


def register_face(config: SystemConfig = DEFAULT_CONFIG) -> bool:
    """
    Main face registration process.
    
    Args:
        config: SystemConfig instance
    
    Returns:
        bool: True if registration successful, False otherwise
    """
    logger.info("Starting face registration process")
    print("\n" + "=" * 70)
    print("FACE REGISTRATION MODULE")
    print("=" * 70)
    
    # Get user name
    user_name = input("\nEnter user name: ").strip()
    if not user_name:
        logger.error("Empty user name provided")
        print("❌ Name cannot be empty!")
        return False
    
    # Check if already registered
    encoding_file = config.encoding_path / f"{user_name}.npy"
    if encoding_file.exists():
        response = input(f"⚠ {user_name} already registered. Re-register? (y/n): ")
        if response.lower() != 'y':
            logger.info(f"Registration cancelled for {user_name}")
            return False
        logger.info(f"Re-registering {user_name}")
    
    # Initialize camera
    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        logger.error("Could not open camera")
        print("❌ Could not open camera!")
        return False
    
    # Initialize components
    validator = FaceQualityValidator(config)
    stats = RegistrationStats()
    encodings: List[np.ndarray] = []
    
    print(f"\n📸 Starting registration for: {user_name}")
    print("-" * 70)
    print("Instructions:")
    print("• Move to different angles (front, left-45°, right-45°)")
    print("• Capture under varying lighting conditions")
    print(f"• Capture at least {MIN_SAMPLES} samples")
    print(f"• Maximum {MAX_SAMPLES} samples")
    print("• Press 's' to capture, 'q' to finish")
    print("-" * 70 + "\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read frame")
            break
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = face_recognition.face_locations(rgb_frame)
        
        # Display frame info
        cv2.putText(frame, f"Samples: {stats.quality_samples}/{MAX_SAMPLES}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "Press 's' to capture, 'q' to finish",
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if len(faces) == 0:
            cv2.putText(frame, "No face detected", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        elif len(faces) > 1:
            cv2.putText(frame, f"Multiple faces detected: {len(faces)}",
                       (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        else:
            top, right, bottom, left = faces[0]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        cv2.imshow("Face Registration", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('s'):
            if len(faces) != 1:
                print("⚠ Please ensure exactly one face is visible")
                continue
            
            if stats.quality_samples >= MAX_SAMPLES:
                print(f"⚠ Maximum samples ({MAX_SAMPLES}) reached")
                break
            
            try:
                # Extract face encoding
                face_encoding = face_recognition.face_encodings(rgb_frame, faces)[0]
                
                # Validate quality
                is_valid, message = validator.validate(
                    frame, faces[0], face_encoding, encodings
                )
                
                if is_valid:
                    encodings.append(face_encoding)
                    stats.quality_samples += 1
                    
                    # Track brightness
                    brightness_status = validator.get_brightness_status(frame)
                    stats.brightness_levels[brightness_status] += 1
                    
                    logger.info(f"Sample {stats.quality_samples} captured for {user_name}")
                    print(f"✅ Sample {stats.quality_samples} captured ({brightness_status} lighting)")
                else:
                    logger.warning(f"Rejected sample: {message}")
                    print(f"❌ {message}")
            
            except Exception as e:
                logger.error(f"Error capturing sample: {e}")
                print(f"❌ Error capturing sample: {e}")
        
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Validate sufficient samples
    if stats.quality_samples < MIN_SAMPLES:
        logger.warning(f"Insufficient samples: {stats.quality_samples}/{MIN_SAMPLES}")
        print(f"\n❌ Insufficient samples! Need at least {MIN_SAMPLES}, got {stats.quality_samples}")
        return False
    
    # Save encodings
    try:
        # Average all encodings
        avg_encoding = np.mean(encodings, axis=0)
        
        # Create encoding directory
        config.encoding_path.mkdir(exist_ok=True)
        
        # Save to file
        np.save(encoding_file, avg_encoding)
        
        logger.info(f"Registration successful for {user_name}: {stats.quality_samples} samples")
        print("\n" + "=" * 70)
        print(f"✅ Registration successful for: {user_name}")
        print(f"Samples captured: {stats.quality_samples}")
        print(f"Lighting conditions - Low: {stats.brightness_levels['low']}, "
              f"Medium: {stats.brightness_levels['medium']}, "
              f"High: {stats.brightness_levels['high']}")
        print(f"Encoding saved to: {encoding_file}")
        print("=" * 70 + "\n")
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving encoding: {e}")
        print(f"\n❌ Error saving encoding: {e}")
        return False


def main() -> None:
    """Main registration entry point."""
    setup_logging(log_level=logging.INFO)
    logger.info("Face Registration Module started")
    
    try:
        success = register_face(DEFAULT_CONFIG)
        if success:
            logger.info("Registration completed successfully")
        else:
            logger.warning("Registration failed or cancelled")
    except KeyboardInterrupt:
        logger.info("Registration interrupted by user")
        print("\n\n⚠ Registration cancelled by user")
    except Exception as e:
        logger.error(f"Fatal error during registration: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
