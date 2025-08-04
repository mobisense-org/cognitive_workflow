# download_models.ps1
# Script to download AI models using download_models.py
# Usage: .\download_models.ps1 [options]

param(
    [string]$WhisperModel = "turbo",
    [string]$ModelsDir = ".\models",
    [switch]$SkipWhisper,
    [switch]$SkipPyannote,
    [string]$VenvPath = ".\venv",
    [switch]$Help
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Red = 'Red'
$Green = 'Green'
$Yellow = 'Yellow'
$Blue = 'Blue'

# Script directory (where this script is located)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Project root directory
$ProjectRoot = "."

# Python script path
$PythonScript = "$ProjectRoot\utils\download_models.py"

# Function to print colored output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

# Function to show usage
function Show-Usage {
    Write-Host @"
Usage: .\download_models.ps1 [OPTIONS]

Download AI models for cognitive workflow application

OPTIONS:
  -WhisperModel MODEL    Whisper model to download (default: turbo)
                        Options: tiny, base, small, medium, large, large-v2, large-v3, turbo
  -ModelsDir DIR         Directory to store models (default: .\models)
  -SkipWhisper           Skip Whisper model download
  -SkipPyannote          Skip pyannote model download
  -VenvPath PATH         Path to virtual environment (default: .\venv)
  -Help                  Show this help message

Examples:
  .\download_models.ps1                          # Download default models
  .\download_models.ps1 -WhisperModel base       # Download base Whisper model
  .\download_models.ps1 -SkipWhisper             # Only download pyannote model
  .\download_models.ps1 -ModelsDir C:\custom\models  # Use custom models directory
"@
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

# Function to check if Python script exists
function Check-PythonScript {
    if (-not (Test-Path $PythonScript)) {
        Write-Error "Python script not found: $PythonScript"
        Write-Info "Make sure the utils.download_models module exists"
        exit 1
    }
    Write-Info "Found download_models.py script"
}

# Function to check and activate virtual environment
function Setup-PythonEnv {
    if (Test-Path $VenvPath) {
        Write-Info "Activating virtual environment: $VenvPath"
        & "$VenvPath\Scripts\Activate.ps1"
    } else {
        Write-Warning "Virtual environment not found at $VenvPath"
        Write-Info "Using system Python environment"
    }
    
    # Check if Python is available
    try {
        $pythonVersion = & python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python not found"
        }
    }
    catch {
        Write-Error "Python is not installed or not in PATH"
        exit 1
    }
    
    Write-Info "Using Python: $(Get-Command python | Select-Object -ExpandProperty Source)"
    Write-Info "Python version: $pythonVersion"
    
    # Set PYTHONPATH to include project root to resolve app module imports
    $env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"
    Write-Info "Set PYTHONPATH: $env:PYTHONPATH"
}

# Function to check .env file for HuggingFace token
function Check-EnvFile {
    $EnvFile = "$ProjectRoot\.env"
    if (-not (Test-Path $EnvFile)) {
        Write-Warning ".env file not found at $EnvFile"
        Write-Info "You may need to create .env file with HUGGINGFACE_TOKEN for pyannote models"
        Write-Info "See env.template for reference"
    } else {
        $envContent = Get-Content $EnvFile -Raw
        if ($envContent -match "HUGGINGFACE_TOKEN=") {
            if ($envContent -match "HUGGINGFACE_TOKEN=your_huggingface_token_here") {
                Write-Warning "Default HuggingFace token found in .env"
                Write-Info "Update .env with your actual token for pyannote models"
            } else {
                Write-Success "HuggingFace token configured in .env"
            }
        } else {
            Write-Warning "HUGGINGFACE_TOKEN not found in .env file"
            Write-Info "Add HUGGINGFACE_TOKEN=your_token_here to .env for pyannote models"
        }
    }
}

# Main execution
function Main {
    Write-Info "Starting AI model download process..."
    Write-Info "Project root: $ProjectRoot"
    Write-Info "Models directory: $ModelsDir"
    Write-Info "Whisper model: $WhisperModel"
    
    # Checks
    Check-PythonScript
    Setup-PythonEnv
    Check-EnvFile
    
    # Create models directory if it doesn't exist
    if (-not (Test-Path $ModelsDir)) {
        New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null
    }
    
    # Build Python command
    # Run as module to avoid import conflicts with local logging.py
    $PythonCmd = "python -m utils.download_models --whisper-model $WhisperModel --models-dir $ModelsDir"
    
    if ($SkipWhisper) {
        $PythonCmd += " --skip-whisper"
    }
    
    if ($SkipPyannote) {
        $PythonCmd += " --skip-pyannote"
    }
    
    Write-Info "Executing: $PythonCmd"
    Write-Host ""
    
    # Change to project root and run the Python script
    Set-Location $ProjectRoot
    
    try {
        Invoke-Expression $PythonCmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Model download completed successfully!"
            
            # Show cache information
            if (Test-Path $ModelsDir) {
                $cacheSize = (Get-ChildItem $ModelsDir -Recurse | Measure-Object -Property Length -Sum).Sum
                $cacheSizeMB = [math]::Round($cacheSize / 1MB, 2)
                Write-Info "Total cache size: $cacheSizeMB MB"
                Write-Info "Cache location: $(Resolve-Path $ModelsDir)"
            }
        } else {
            Write-Error "Model download failed!"
            exit 1
        }
    }
    catch {
        Write-Error "Model download failed with error: $_"
        exit 1
    }
}

# Run main function
Main 