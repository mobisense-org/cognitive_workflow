# Cognitive Workflow - Windows Setup Guide

This guide provides instructions for setting up the cognitive workflow application on Windows systems.

## Prerequisites

Before running the setup scripts, ensure you have the following installed:

### Required Software

1. **Python 3.8 or later**
   - Download from [python.org](https://python.org)
   - Make sure to check "Add Python to PATH" during installation
   - Verify installation: `python --version`

2. **Git** (optional but recommended)
   - Download from [git-scm.com](https://git-scm.com)
   - Used for cloning the repository

3. **FFmpeg** (recommended for audio processing)
   - Install via winget: `winget install ffmpeg`
   - Or download from [ffmpeg.org](https://ffmpeg.org)
   - Add to PATH if downloaded manually

### System Requirements

- **Operating System**: Windows 10 or later
- **Memory**: At least 4GB RAM (8GB+ recommended)
- **Storage**: At least 5GB free space for models
- **Internet**: Required for downloading AI models

## Setup Options

We provide three different setup scripts for Windows users:

### 1. PowerShell Script (Recommended)
- **File**: `setup.ps1`
- **Best for**: Modern Windows systems with PowerShell 5.1+
- **Features**: Full colored output, better error handling, more robust

### 2. Batch File
- **File**: `setup.bat`
- **Best for**: Legacy systems or Command Prompt users
- **Features**: Compatible with older Windows versions

### 3. Original Bash Script
- **File**: `setup.sh`
- **Best for**: WSL (Windows Subsystem for Linux) users
- **Features**: Full Linux compatibility when using WSL

## Quick Start

### Option 1: PowerShell (Recommended)

1. **Open PowerShell as Administrator**
   ```powershell
   # Navigate to project directory
   cd C:\path\to\cognitive_workflow
   
   # Run setup script
   .\setup.ps1
   ```

2. **If you get execution policy errors**:
   ```powershell
   # Set execution policy (run as Administrator)
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   
   # Then run the setup
   .\setup.ps1
   ```

### Option 2: Command Prompt

1. **Open Command Prompt as Administrator**
   ```cmd
   # Navigate to project directory
   cd C:\path\to\cognitive_workflow
   
   # Run setup script
   setup.bat
   ```

### Option 3: WSL (Windows Subsystem for Linux)

1. **Install WSL if not already installed**:
   ```powershell
   wsl --install
   ```

2. **Run the original bash script**:
   ```bash
   # Navigate to project directory
   cd /mnt/c/path/to/cognitive_workflow
   
   # Make script executable and run
   chmod +x setup.sh
   ./setup.sh
   ```

## Setup Script Options

All setup scripts support the following command-line options:

### Basic Options
```powershell
# Full setup with default options
.\setup.ps1

# Skip model download (faster setup)
.\setup.ps1 -SkipModels

# Skip virtual environment creation
.\setup.ps1 -SkipVenv

# Force reinstallation of dependencies
.\setup.ps1 -Force
```

### Advanced Options
```powershell
# Use specific Python version
.\setup.ps1 -PythonCmd python3.9

# Custom virtual environment path
.\setup.ps1 -VenvPath C:\custom\venv

# Custom models directory
.\setup.ps1 -ModelsDir C:\custom\models

# Use different Whisper model
.\setup.ps1 -WhisperModel base

# Provide HuggingFace token
.\setup.ps1 -HfToken hf_your_token_here
```

## Model Download Scripts

Separate scripts are available for downloading AI models:

### PowerShell Version
```powershell
# Download default models
.\download_models.ps1

# Download specific Whisper model
.\download_models.ps1 -WhisperModel base

# Skip Whisper, only download pyannote
.\download_models.ps1 -SkipWhisper

# Use custom models directory
.\download_models.ps1 -ModelsDir C:\custom\models
```

### Batch File Version
```cmd
# Download default models
download_models.bat

# Download specific Whisper model
download_models.bat -w base

# Skip Whisper, only download pyannote
download_models.bat --skip-whisper
```

## Post-Setup Usage

After successful setup:

### 1. Activate Virtual Environment

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

### 2. Run the Application

```powershell
# Process first audio file found
python main.py

# Process specific file
python main.py audio.wav

# List available audio files
python main.py --list-files

# Run only transcription step
python main.py --step transcribe
```

## Troubleshooting

### Common Issues

#### 1. PowerShell Execution Policy Error
```
File C:\path\to\setup.ps1 cannot be loaded because running scripts is disabled on this system.
```

**Solution:**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. Python Not Found
```
[ERROR] python is not installed or not in PATH
```

**Solutions:**
- Reinstall Python and check "Add to PATH"
- Add Python manually to PATH environment variable
- Use `-PythonCmd` option to specify Python path

#### 3. Virtual Environment Activation Fails
```
[ERROR] Failed to activate virtual environment
```

**Solutions:**
- Run as Administrator
- Check if antivirus is blocking the script
- Try recreating the virtual environment with `-Force` option

#### 4. Model Download Fails
```
[ERROR] Model download failed!
```

**Solutions:**
- Check internet connection
- Verify HuggingFace token in `.env` file
- Try downloading models separately with `download_models.ps1`
- Check available disk space

#### 5. FFmpeg Not Found
```
[WARNING] ffmpeg not found - may be needed for audio processing
```

**Solutions:**
```powershell
# Install via winget
winget install ffmpeg

# Or download manually from https://ffmpeg.org
# Add to PATH environment variable
```

#### 6. Insufficient Disk Space
```
[WARNING] Low disk space - AI models require several GB
```

**Solutions:**
- Free up disk space (at least 5GB recommended)
- Use smaller Whisper models (tiny, base, small)
- Use custom models directory on different drive

### Environment Variables

The setup scripts set these environment variables:

- `PYTHONPATH`: Includes project root for module imports
- `WHISPER_CACHE_DIR`: Directory for Whisper model cache
- `HF_HOME`: Directory for HuggingFace model cache

### File Structure After Setup

```
cognitive_workflow/
├── venv/                    # Virtual environment
├── models/                  # AI models cache
│   ├── whisper/            # Whisper models
│   └── pyannote/           # Pyannote models
├── audio_input/            # Place audio files here
├── outputs/                # Generated outputs
├── config/                 # Configuration files
├── modules/                # Application modules
├── utils/                  # Utility scripts
├── setup.ps1              # PowerShell setup script
├── setup.bat              # Batch setup script
├── download_models.ps1    # PowerShell model download
├── download_models.bat    # Batch model download
└── requirements.txt       # Python dependencies
```

## Getting Help

### Script Help
```powershell
# Show setup script help
.\setup.ps1 -Help

# Show model download help
.\download_models.ps1 -Help
```

### Manual Setup
If scripts fail, you can perform setup manually:

1. **Create virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. **Download models:**
   ```powershell
   python -m utils.download_models
   ```

### Support
- Check the main README.md for general information
- Review error messages carefully for specific issues
- Ensure all prerequisites are properly installed
- Try running scripts as Administrator if permission issues occur

## Performance Tips

### For Better Performance:
- Use SSD storage for models directory
- Ensure sufficient RAM (8GB+ recommended)
- Use smaller Whisper models for faster processing
- Close unnecessary applications during model downloads

### For Limited Resources:
- Use `tiny` or `base` Whisper models
- Skip model download initially with `-SkipModels`
- Use system Python instead of virtual environment with `-SkipVenv`
- Download models separately when convenient 