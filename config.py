"""
Configuration module for Face Recognition Attendance System.

Follows Google style guide for Python code and AIML best practices.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class LivenessConfig:
    """Configuration for liveness detection."""
    motion_history_size: int = 10
    liveness_threshold: int = 15
    min_face_presence: int = 5
    motion_pixel_threshold: int = 10


@dataclass
class RecognitionConfig:
    """Configuration for face recognition thresholds."""
    recognition_threshold: float = 0.6  # Lower = stricter
    confidence_threshold: float = 0.55
    duplicate_detection_window: int = 5  # seconds
    
    def __post_init__(self):
        """Validate configuration values."""
        if not 0 <= self.recognition_threshold <= 1:
            raise ValueError(f"recognition_threshold must be between 0-1, got {self.recognition_threshold}")
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError(f"confidence_threshold must be between 0-1, got {self.confidence_threshold}")


@dataclass
class BrightnessConfig:
    """Configuration for brightness/lighting detection."""
    low_threshold: int = 85
    medium_threshold: int = 170
    
    def __post_init__(self):
        """Validate brightness thresholds."""
        if self.low_threshold >= self.medium_threshold:
            raise ValueError("low_threshold must be less than medium_threshold")


@dataclass
class SystemConfig:
    """Main system configuration."""
    # Paths
    encoding_path: Path = Path("encodings")
    attendance_file: Path = Path("attendance.csv")
    
    # Feature configs
    liveness: LivenessConfig = None
    recognition: RecognitionConfig = None
    brightness: BrightnessConfig = None
    
    # Camera settings
    camera_index: int = 0
    face_detection_model: str = "hog"  # or "cnn" for GPU
    
    # Logging
    log_level: int = logging.INFO
    log_file: Optional[Path] = None
    
    def __post_init__(self):
        """Initialize nested configs if not provided."""
        if self.liveness is None:
            self.liveness = LivenessConfig()
        if self.recognition is None:
            self.recognition = RecognitionConfig()
        if self.brightness is None:
            self.brightness = BrightnessConfig()
        
        # Create directories if they don't exist
        self.encoding_path.mkdir(exist_ok=True)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "SystemConfig":
        """Create config from dictionary."""
        return cls(
            encoding_path=Path(config_dict.get("encoding_path", "encodings")),
            attendance_file=Path(config_dict.get("attendance_file", "attendance.csv")),
            liveness=LivenessConfig(**config_dict.get("liveness", {})),
            recognition=RecognitionConfig(**config_dict.get("recognition", {})),
            brightness=BrightnessConfig(**config_dict.get("brightness", {})),
            camera_index=config_dict.get("camera_index", 0),
            face_detection_model=config_dict.get("face_detection_model", "hog"),
            log_level=config_dict.get("log_level", logging.INFO),
            log_file=Path(config_dict.get("log_file")) if config_dict.get("log_file") else None,
        )


# Default configuration
DEFAULT_CONFIG = SystemConfig()
