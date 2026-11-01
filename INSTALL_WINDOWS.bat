@echo off
rem One-time setup: Python environment, PyTorch (GPU when available), packages, face model.
cd /d "%~dp0"
set CUDA_INDEX=https://download.pytorch.org/whl/cu132

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Could not create a Python environment. Install Python 3.11+ 64-bit and retry.
    pause
    exit /b 1
  )
)
set PY=.venv\Scripts\python.exe
"%PY%" -m pip install --upgrade pip

where nvidia-smi >nul 2>nul && nvidia-smi >nul 2>nul
if errorlevel 1 (
  echo No NVIDIA GPU found - installing CPU PyTorch.
  "%PY%" -m pip install torch torchvision
) else (
  echo NVIDIA GPU found - installing GPU ^(CUDA^) PyTorch. This is a large download.
  "%PY%" -m pip install torch torchvision --index-url %CUDA_INDEX% || "%PY%" -m pip install torch torchvision
)
"%PY%" -m pip install -r requirements.txt
"%PY%" scripts\download_models.py
if errorlevel 1 (
  echo Model download failed. Check the internet connection and run this file again.
  pause
  exit /b 1
)
echo.
echo Setup complete. Double-click MoodCafe.exe to start.
pause
