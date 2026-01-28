# Installation & Setup Guide

## Problem: CMake Dependency
The `face_recognition` library requires CMake to compile on Windows. If you see import errors, follow these steps:

## Solution 1: Install CMake (Recommended for Windows)
1. Download CMake from: https://cmake.org/download/
2. Download the Windows x64 installer
3. Run the installer and **IMPORTANT**: Check "Add CMake to system PATH" during installation
4. Restart your terminal/Python environment
5. Then install the packages:
```bash
pip install -r requirements.txt
```

## Solution 2: Install Visual Studio C++ Build Tools
1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run the installer and select "Desktop development with C++"
3. Complete the installation
4. Then install the packages:
```bash
pip install -r requirements.txt
```

## Solution 3: Use Anaconda/Miniconda (Easiest on Windows)
Anaconda provides pre-built wheels for most packages:
```bash
conda install -c conda-forge face_recognition opencv
```

## After Installation
Once all dependencies are installed:

### Register a new face:
```bash
python register.py
```

### Run attendance system:
```bash
python recognize.py
```

## Files
- `register.py` - Register new faces for the attendance system
- `recognize.py` - Run the face recognition attendance system
- `attendance.py` - Additional utility (if needed)
- `encodings/` - Directory where face encodings are stored
- `attendance.csv` - CSV file where attendance records are saved

## Troubleshooting
- If you still get import errors after installing dependencies, verify with:
  ```bash
  python -c "import cv2; import face_recognition; print('✅ All imports successful!')"
  ```
- Make sure CMake was added to PATH (restart terminal after installing)
- Check that you're using the correct Python environment (the .venv folder)
