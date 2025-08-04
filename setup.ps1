# setup.ps1
# This script sets up the environment for the cognitive workflow application on Windows

param(
    [switch]$SkipModels,
    [switch]$SkipVenv,
    [string]$HfToken = "",
    [string]$PythonCmd = "python",
    [string]$VenvPath = "",
    [string]$ModelsDir = ".\models",
    [string]$WhisperModel = "turbo",
    [switch]$Force,
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Project configuration
$VENV_NAME = "venv"
$PYTHON_MIN_VERSION = "3.8"
$REQUIREMENTS_FILE = "requirements.txt"

# Function to print colored output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Header {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host $Message -ForegroundColor White
}

# Function to show script usage
function Show-Usage {
    Write-Host @"
Usage: .\setup.ps1 [OPTIONS]

Setup script for cognitive workflow

OPTIONS:
  -SkipModels           Skip model download step
  -SkipVenv             Skip virtual environment creation (use existing)
  -HfToken TOKEN        Provide HuggingFace token directly
  -PythonCmd CMD        Use specific Python command (default: python)
  -VenvPath PATH        Use custom virtual environment path
  -ModelsDir DIR        Custom models directory (default: .\models)
  -WhisperModel MODEL   Whisper model to download (default: turbo)
  -Force                Force reinstallation of dependencies
  -Help                 Show this help message

Examples:
  .\setup.ps1                                    # Full setup with default options
  .\setup.ps1 -SkipModels                        # Setup without downloading models
  .\setup.ps1 -HfToken hf_abc123                 # Setup with HuggingFace token
  .\setup.ps1 -PythonCmd python3.9               # Use specific Python version
  .\setup.ps1 -WhisperModel base                 # Use base Whisper model instead of turbo

"@
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

# Set default venv path if not provided
if ([string]::IsNullOrEmpty($VenvPath)) {
    $VenvPath = ".\$VENV_NAME"
}

# Function to check system requirements
function Check-SystemRequirements {
    Write-Step "Checking system requirements..."
    
    # Check OS
    Write-Info "Operating System: Windows ✓"
    
    # Check Python
    try {
        $pythonVersion = & $PythonCmd --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python not found"
        }
        Write-Info "Python found: $pythonVersion"
    }
    catch {
        Write-Error "$PythonCmd is not installed or not in PATH"
        Write-Info "Please install Python $PYTHON_MIN_VERSION or later from https://python.org"
        exit 1
    }
    
    # Check Python version
    try {
        $versionOutput = & $PythonCmd -c 'import sys; print(".".join([str(x) for x in sys.version_info[:2]]))' 2>&1
        Write-Info "Python version: $versionOutput"
        
        # Check if Python version meets minimum requirement
        $versionCheck = & $PythonCmd -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)' 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Python version meets requirements ✓"
        } else {
            Write-Error "Python version $versionOutput is below minimum required version $PYTHON_MIN_VERSION"
            exit 1
        }
    }
    catch {
        Write-Error "Failed to check Python version"
        exit 1
    }
    
    # Check pip
    try {
        $pipVersion = & $PythonCmd -m pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "pip is available ✓"
        } else {
            throw "pip not available"
        }
    }
    catch {
        Write-Error "pip is not available"
        Write-Info "Please install pip for $PythonCmd"
        exit 1
    }
    
    # Check for ffmpeg (required for audio processing)
    try {
        $ffmpegVersion = & ffmpeg -version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "ffmpeg is available ✓"
        } else {
            throw "ffmpeg not found"
        }
    }
    catch {
        Write-Warning "ffmpeg not found - may be needed for audio processing"
        Write-Info "Install with: winget install ffmpeg or download from https://ffmpeg.org"
    }
    
    # Check available disk space
    try {
        $drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$((Get-Location).Drive.Name):'"
        $availableSpaceGB = [math]::Round($drive.FreeSpace / 1GB, 2)
        if ($availableSpaceGB -gt 5) {
            Write-Success "Sufficient disk space available ($availableSpaceGB GB) ✓"
        } else {
            Write-Warning "Low disk space ($availableSpaceGB GB) - AI models require several GB"
        }
    }
    catch {
        Write-Warning "Could not check disk space"
    }
    
    # Check memory
    try {
        $memory = Get-WmiObject -Class Win32_ComputerSystem
        $totalMemoryGB = [math]::Round($memory.TotalPhysicalMemory / 1GB, 2)
        if ($totalMemoryGB -gt 4) {
            Write-Success "Sufficient memory available ($totalMemoryGB GB) ✓"
        } else {
            Write-Warning "Limited memory ($totalMemoryGB GB) - consider using smaller Whisper models"
        }
    }
    catch {
        Write-Warning "Could not check memory"
    }
}

# Function to create virtual environment
function Create-VirtualEnvironment {
    if ($SkipVenv) {
        Write-Step "Skipping virtual environment creation"
        return
    }
    
    Write-Step "Setting up Python virtual environment..."
    
    if ((Test-Path $VenvPath) -and -not $Force) {
        Write-Info "Virtual environment already exists at $VenvPath"
        $response = Read-Host "Do you want to recreate it? (y/N)"
        if ($response -match "^[Yy]$") {
            Write-Info "Removing existing virtual environment..."
            Remove-Item -Path $VenvPath -Recurse -Force
        } else {
            Write-Info "Using existing virtual environment"
            return
        }
    }
    
    Write-Info "Creating virtual environment at $VenvPath..."
    & $PythonCmd -m venv $VenvPath
    
    if (-not (Test-Path "$VenvPath\Scripts\Activate.ps1")) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    
    Write-Success "Virtual environment created successfully ✓"
}

# Function to activate virtual environment
function Activate-VirtualEnvironment {
    if ($SkipVenv) {
        Write-Info "Using system Python environment"
        return
    }
    
    Write-Info "Activating virtual environment..."
    & "$VenvPath\Scripts\Activate.ps1"
    
    # Verify activation
    if ($env:VIRTUAL_ENV) {
        Write-Success "Virtual environment activated ✓"
        Write-Info "Using Python: $(Get-Command python | Select-Object -ExpandProperty Source)"
    } else {
        Write-Error "Failed to activate virtual environment"
        exit 1
    }
}

# Function to upgrade pip and install wheel
function Upgrade-Pip {
    Write-Step "Upgrading pip and installing build tools..."
    
    & python -m pip install --upgrade pip
    & python -m pip install wheel setuptools
    
    Write-Success "pip and build tools updated ✓"
}

# Function to install Python dependencies
function Install-Dependencies {
    Write-Step "Installing Python dependencies..."
    
    if (-not (Test-Path $REQUIREMENTS_FILE)) {
        Write-Error "Requirements file not found: $REQUIREMENTS_FILE"
        exit 1
    }
    
    Write-Info "Installing packages from $REQUIREMENTS_FILE..."
    
    if ($Force) {
        & python -m pip install --force-reinstall -r $REQUIREMENTS_FILE
    } else {
        & python -m pip install -r $REQUIREMENTS_FILE
    }
    
    # Install the imagine SDK wheel if it exists
    if (Test-Path "imagine_sdk-0.4.2-py3-none-any.whl") {
        Write-Info "Installing imagine SDK from local wheel..."
        & python -m pip install imagine_sdk-0.4.2-py3-none-any.whl
    }
    
    Write-Success "Dependencies installed successfully ✓"
}

# Function to create project directories
function Create-Directories {
    Write-Step "Creating project directories..."
    
    $directories = @(
        $ModelsDir,
        "$ModelsDir\whisper",
        "$ModelsDir\pyannote",
        "audio_input",
        "outputs",
        "config",
        "modules",
        "utils"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Info "Created directory: $dir"
        }
    }
    
    Write-Success "Project directories ready ✓"
}

# Function to download AI models
function Download-Models {
    if ($SkipModels) {
        Write-Step "Skipping model download"
        return
    }
    
    Write-Step "Downloading AI models..."
    
    # Check if download_models.ps1 exists
    if (Test-Path "download_models.ps1") {
        Write-Info "Using existing download_models.ps1 script..."
        
        # Build download command
        $downloadCmd = ".\download_models.ps1 -WhisperModel $WhisperModel -ModelsDir $ModelsDir"
        
        if (-not $SkipVenv) {
            $downloadCmd += " -VenvPath $VenvPath"
        }
        
        Write-Info "Executing: $downloadCmd"
        Invoke-Expression $downloadCmd
    } else {
        Write-Warning "download_models.ps1 not found, downloading models directly..."
        
        # Set environment variables for model caching
        $env:PYTHONPATH = ".;$env:PYTHONPATH"
        $env:WHISPER_CACHE_DIR = "$ModelsDir\whisper"
        $env:HF_HOME = "$ModelsDir\pyannote"
        
        # Download using Python module
        & python -m utils.download_models --whisper-model $WhisperModel --models-dir $ModelsDir
    }
    
    Write-Success "Model download completed ✓"
}

# Function to display final setup summary
function Show-SetupSummary {
    Write-Header @"

╔══════════════════════════════════════════════════════════════╗
║                    SETUP COMPLETED SUCCESSFULLY!             ║
╚══════════════════════════════════════════════════════════════╝
"@
    
    Write-Host "Workflow is ready to use!" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Quick Start:" -ForegroundColor White
    if (-not $SkipVenv) {
        Write-Host "  1. Activate virtual environment: $VenvPath\Scripts\Activate.ps1"
    }
    Write-Host "  2. Place audio files in: .\audio_input\"
    Write-Host "  3. Run workflow: python main.py"
    Write-Host ""
    
    Write-Host "Usage Examples:" -ForegroundColor White
    Write-Host "  python main.py                    # Process first audio file found"
    Write-Host "  python main.py audio.wav          # Process specific file"
    Write-Host "  python main.py --list-files       # List available audio files"
    Write-Host "  python main.py --step transcribe  # Run only transcription"
    Write-Host ""
}

# Main execution function
function Main {
    Write-Header @"

╔══════════════════════════════════════════════════════════════╗
║  This script will set up your complete development           ║
║  environment for cognitive workflow                          ║
╚══════════════════════════════════════════════════════════════╝
"@
    
    Write-Info "Starting setup process..."
    Write-Info "Virtual environment: $VenvPath"
    Write-Info "Models directory: $ModelsDir"
    Write-Info "Whisper model: $WhisperModel"
    Write-Host ""
    
    # Execute setup steps
    Check-SystemRequirements
    Write-Host ""
    
    Create-VirtualEnvironment
    Write-Host ""
    
    Activate-VirtualEnvironment
    Write-Host ""
    
    Upgrade-Pip
    Write-Host ""
    
    Install-Dependencies
    Write-Host ""
    
    Create-Directories
    Write-Host ""
        
    Download-Models
    Write-Host ""
    
    Show-SetupSummary
}

# Execute main function
Main 