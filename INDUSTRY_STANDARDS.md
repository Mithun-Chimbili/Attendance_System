# Face Recognition Attendance System - Industry Standard Edition

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.13%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Overview

A production-ready face recognition attendance system built following **Google's Python style guide** and **AIML industry standards**. Features real-time face recognition with motion-based liveness detection and anti-spoofing measures.

## ✨ Key Features

- **Type-Safe**: Full type hints throughout the codebase
- **Configurable**: Centralized configuration management via `config.py`
- **Logging**: Structured logging with file rotation support
- **Modular Design**: Clean separation of concerns with dedicated modules
- **Liveness Detection**: Motion-based anti-spoofing
- **Production-Ready**: Error handling, validation, and monitoring
- **Documentation**: Google-style docstrings for all functions

## 🏗️ Architecture

```
├── config.py              # Configuration management (dataclasses)
├── logger_config.py       # Logging setup and utilities
├── recognize_v2.py        # Industry-standard recognition module
├── register_v2.py         # Industry-standard registration module
├── attendance.py          # Reporting and analytics
└── encodings/             # Stored face encodings
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/SaiKamal-K/Attendance_System.git
cd Attendance_System

# Install dependencies
pip install -r requirements.txt
```

### 2. Register Faces

```bash
python register_v2.py
```

**Process:**
- Enter user name
- Capture 15-30 face samples from different angles and lighting
- Press 's' to capture, 'q' to finish
- Face encoding is automatically averaged and saved

### 3. Run Recognition System

```bash
python recognize_v2.py
```

**Controls:**
- `a` - Mark attendance (punch-in/out)
- `r` - Reset liveness detector
- `q` - Quit

### 4. View Reports

```bash
python attendance.py
```

## 🔧 Configuration

Edit `config.py` to customize thresholds:

```python
from config import SystemConfig, RecognitionConfig, LivenessConfig

config = SystemConfig(
    recognition=RecognitionConfig(
        recognition_threshold=0.6,      # Face matching threshold
        confidence_threshold=0.55,      # Confidence threshold
    ),
    liveness=LivenessConfig(
        motion_history_size=10,         # Motion tracking frames
        liveness_threshold=15,          # Motion pixel threshold
    ),
    camera_index=0,                     # Camera device index
    face_detection_model="hog"          # "hog" or "cnn"
)
```

## 📊 Code Quality Standards

### Type Hints
```python
def recognize_face(
    self, 
    frame: np.ndarray, 
    rgb_frame: np.ndarray
) -> RecognitionResult:
    """Recognize faces with type safety."""
```

### Dataclasses for Configuration
```python
@dataclass
class RecognitionConfig:
    recognition_threshold: float = 0.6
    confidence_threshold: float = 0.55
```

### Structured Logging
```python
logger.info(f"Punch-In recorded for {name} at {time_str}")
logger.error(f"Error during face recognition: {e}")
```

### Docstrings (Google Style)
```python
def mark_attendance(self, name: str, is_alive: bool) -> str:
    """
    Mark attendance with liveness verification.
    
    Args:
        name: User name
        is_alive: Liveness check result
    
    Returns:
        Status string ("PUNCH_IN", "PUNCH_OUT", "DUPLICATE", etc.)
    """
```

## 🛡️ Security & Anti-Spoofing

- **Motion-Based Liveness**: Detects if face is a real person or photo/video
- **Duplicate Prevention**: Prevents multiple punch-ins within 5 seconds
- **Multiple Face Detection**: Warns if multiple faces detected
- **Confidence Scoring**: Only accepts matches above confidence threshold

## 📈 Performance

- **Face Detection**: HOG (fast) or CNN (accurate)
- **Encoding Distance**: Uses dlib's ResNet-based CNN (128-d vectors)
- **Real-time Processing**: ~30 FPS on standard laptops
- **Low Latency**: Motion-based liveness check < 100ms

## 📝 Logging

Logs are saved to `logs/attendance_system.log`:

```
2026-01-28 19:27:43 - attendance_system.recognize - INFO - Punch-In recorded for saikamal
2026-01-28 19:27:45 - attendance_system.recognize - INFO - Punch-Out recorded for saikamal
```

## 🧪 Testing & Code Quality

```bash
# Run pytest
pytest tests/

# Type checking
mypy recognize_v2.py register_v2.py

# Code formatting
black . --line-length=100

# Linting
pylint *.py
```

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| opencv-python | >=4.13.0 | Computer vision |
| face-recognition | >=1.3.0 | Face encoding/detection |
| numpy | >=2.0.0 | Numerical computing |
| pandas | >=3.0.0 | Data handling |
| dlib | >=20.0.0 | CNN-based features |

## 🎯 Industry Standards Applied

✅ **PEP 8 Compliance** - Python style guide  
✅ **Type Hints** - For code clarity and IDE support  
✅ **Docstrings** - Google style format  
✅ **Configuration Management** - Centralized config via dataclasses  
✅ **Error Handling** - Try-except with logging  
✅ **Logging** - Structured logging with levels  
✅ **Modularity** - Clear separation of concerns  
✅ **Documentation** - Comprehensive inline and file docs  
✅ **Data Validation** - Input validation in config classes  
✅ **Performance** - Optimized for real-time processing  

## 🔍 File Structure

```
project/
├── config.py                 # 🎯 Configuration (dataclasses)
├── logger_config.py          # 📝 Logging setup
├── recognize_v2.py           # 👁️ Recognition (type-safe)
├── register_v2.py            # ✍️ Registration (type-safe)
├── attendance.py             # 📊 Reports
├── requirements.txt          # 📦 Dependencies
├── encodings/                # 🗂️ Face encodings
│   ├── saikamal.npy
│   └── user2.npy
├── attendance.csv            # 📋 Attendance records
└── logs/                      # 📄 Application logs
    └── attendance_system.log
```

## 📚 API Reference

### `recognize_v2.RecognitionResult`
Data class for recognition output:
- `name`: Recognized user name
- `distance`: Face encoding distance
- `is_alive`: Liveness check result
- `confidence`: Match confidence (0-1)
- `timestamp`: Detection timestamp

### `recognize_v2.AttendanceSystem`
Main recognition system:
```python
system = AttendanceSystem(config)
result = system.recognize_face(frame, rgb_frame)
status = system.mark_attendance(name, is_alive)
```

### `register_v2.FaceQualityValidator`
Validates face sample quality:
```python
validator = FaceQualityValidator(config)
is_valid, message = validator.validate(frame, location, encoding, history)
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not detected | Check camera permissions, try camera index 1 |
| Low liveness score | Move head more, ensure good lighting |
| Face not recognized | Ensure at least 15 samples registered from different angles |
| CMake errors | Install CMake from cmake.org |

## 📄 License

MIT License - See LICENSE file

## 👨‍💻 Author

**Sai Kamal K**  
AIML Engineer | Software Developer  
[GitHub](https://github.com/SaiKamal-K) | [Attendance_System](https://github.com/SaiKamal-K/Attendance_System)

## 🙏 Acknowledgments

- Google Python Style Guide
- dlib Face Recognition
- OpenCV Community

---

**Version**: 2.0 (Industry Standard Edition)  
**Last Updated**: January 28, 2026  
**Status**: ✅ Production Ready
