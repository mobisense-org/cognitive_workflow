@echo off
setlocal enabledelayedexpansion

REM setup.bat
REM This script sets up the environment for the cognitive workflow application on Windows

REM Project configuration
set VENV_NAME=venv
set PYTHON_MIN_VERSION=3.8
set REQUIREMENTS_FILE=requirements.txt

REM Default values
set SKIP_MODELS=false
set SKIP_VENV=false
set HF_TOKEN=
set PYTHON_CMD=python
set VENV_PATH=
set MODELS_DIR=.\models
set WHISPER_MODEL=turbo
set FORCE_INSTALL=false

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="--skip-models" set SKIP_MODELS=true
if "%~1"=="--skip-venv" set SKIP_VENV=true
if "%~1"=="--hf-token" (
    set HF_TOKEN=%~2
    shift
)
if "%~1"=="--python-cmd" (
    set PYTHON_CMD=%~2
    shift
)
if "%~1"=="--venv-path" (
    set VENV_PATH=%~2
    shift
)
if "%~1"=="--models-dir" (
    set MODELS_DIR=%~2
    shift
)
if "%~1"=="--whisper-model" (
    set WHISPER_MODEL=%~2
    shift
)
if "%~1"=="--force" set FORCE_INSTALL=true
if "%~1"=="-h" goto :show_usage
if "%~1"=="--help" goto :show_usage
shift
goto :parse_args
:end_parse

REM Set default venv path if not provided
if "%VENV_PATH%"=="" set VENV_PATH=.\%VENV_NAME%

REM Function to print colored output
:print_info
echo [INFO] %~1
goto :eof

:print_success
echo [SUCCESS] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

:print_header
echo %~1
goto :eof

:print_step
echo %~1
goto :eof

REM Function to show script usage
:show_usage
echo Usage: setup.bat [OPTIONS]
echo.
echo Setup script for cognitive workflow
echo.
echo OPTIONS:
echo   --skip-models           Skip model download step
echo   --skip-venv             Skip virtual environment creation (use existing)
echo   --hf-token TOKEN        Provide HuggingFace token directly
echo   --python-cmd CMD        Use specific Python command (default: python)
echo   --venv-path PATH        Use custom virtual environment path
echo   --models-dir DIR        Custom models directory (default: .\models)
echo   --whisper-model MODEL   Whisper model to download (default: turbo)
echo   --force                 Force reinstallation of dependencies
echo   -h, --help              Show this help message
echo.
echo Examples:
echo   setup.bat                                    # Full setup with default options
echo   setup.bat --skip-models                      # Setup without downloading models
echo   setup.bat --hf-token hf_abc123               # Setup with HuggingFace token
echo   setup.bat --python-cmd python3.9             # Use specific Python version
echo   setup.bat --whisper-model base               # Use base Whisper model instead of turbo
echo.
exit /b 0

REM Function to check system requirements
:check_system_requirements
call :print_step "Checking system requirements..."

call :print_info "Operating System: Windows ✓"

REM Check Python
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    call :print_error "%PYTHON_CMD% is not installed or not in PATH"
    call :print_info "Please install Python %PYTHON_MIN_VERSION% or later from https://python.org"
    exit /b 1
)

REM Check Python version
for /f "tokens=*" %%i in ('%PYTHON_CMD% -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2^>nul') do set PYTHON_VERSION=%%i
call :print_info "Python version: %PYTHON_VERSION%"

%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 (
    call :print_error "Python version %PYTHON_VERSION% is below minimum required version %PYTHON_MIN_VERSION%"
    exit /b 1
)
call :print_success "Python version meets requirements ✓"

REM Check pip
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    call :print_error "pip is not available"
    call :print_info "Please install pip for %PYTHON_CMD%"
    exit /b 1
)
call :print_success "pip is available ✓"

REM Check for ffmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    call :print_warning "ffmpeg not found - may be needed for audio processing"
    call :print_info "Install with: winget install ffmpeg or download from https://ffmpeg.org"
) else (
    call :print_success "ffmpeg is available ✓"
)

REM Check available disk space (simplified check)
for /f "tokens=3" %%i in ('dir /-c 2^>nul ^| find "bytes free"') do set FREE_SPACE=%%i
if defined FREE_SPACE (
    call :print_info "Disk space check completed"
) else (
    call :print_warning "Could not check disk space"
)

goto :eof

REM Function to create virtual environment
:create_virtual_environment
if "%SKIP_VENV%"=="true" (
    call :print_step "Skipping virtual environment creation"
    goto :eof
)

call :print_step "Setting up Python virtual environment..."

if exist "%VENV_PATH%" (
    if "%FORCE_INSTALL%"=="false" (
        call :print_info "Virtual environment already exists at %VENV_PATH%"
        set /p response="Do you want to recreate it? (y/N): "
        if /i "!response!"=="y" (
            call :print_info "Removing existing virtual environment..."
            rmdir /s /q "%VENV_PATH%" 2>nul
        ) else (
            call :print_info "Using existing virtual environment"
            goto :eof
        )
    )
)

call :print_info "Creating virtual environment at %VENV_PATH%..."
%PYTHON_CMD% -m venv "%VENV_PATH%"

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    call :print_error "Failed to create virtual environment"
    exit /b 1
)

call :print_success "Virtual environment created successfully ✓"
goto :eof

REM Function to activate virtual environment
:activate_virtual_environment
if "%SKIP_VENV%"=="true" (
    call :print_info "Using system Python environment"
    goto :eof
)

call :print_info "Activating virtual environment..."
call "%VENV_PATH%\Scripts\activate.bat"

REM Verify activation
if defined VIRTUAL_ENV (
    call :print_success "Virtual environment activated ✓"
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('where python') do (
            call :print_info "Using Python: %%i"
            goto :found_python
        )
    )
    :found_python
) else (
    call :print_error "Failed to activate virtual environment"
    exit /b 1
)
goto :eof

REM Function to upgrade pip and install wheel
:upgrade_pip
call :print_step "Upgrading pip and installing build tools..."

python -m pip install --upgrade pip
python -m pip install wheel setuptools

call :print_success "pip and build tools updated ✓"
goto :eof

REM Function to install Python dependencies
:install_dependencies
call :print_step "Installing Python dependencies..."

if not exist "%REQUIREMENTS_FILE%" (
    call :print_error "Requirements file not found: %REQUIREMENTS_FILE%"
    exit /b 1
)

call :print_info "Installing packages from %REQUIREMENTS_FILE%..."

if "%FORCE_INSTALL%"=="true" (
    python -m pip install --force-reinstall -r "%REQUIREMENTS_FILE%"
) else (
    python -m pip install -r "%REQUIREMENTS_FILE%"
)

REM Install the imagine SDK wheel if it exists
if exist "imagine_sdk-0.4.2-py3-none-any.whl" (
    call :print_info "Installing imagine SDK from local wheel..."
    python -m pip install imagine_sdk-0.4.2-py3-none-any.whl
)

call :print_success "Dependencies installed successfully ✓"
goto :eof

REM Function to create project directories
:create_directories
call :print_step "Creating project directories..."

if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"
if not exist "%MODELS_DIR%\whisper" mkdir "%MODELS_DIR%\whisper"
if not exist "%MODELS_DIR%\pyannote" mkdir "%MODELS_DIR%\pyannote"
if not exist "audio_input" mkdir "audio_input"
if not exist "outputs" mkdir "outputs"
if not exist "config" mkdir "config"
if not exist "modules" mkdir "modules"
if not exist "utils" mkdir "utils"

call :print_success "Project directories ready ✓"
goto :eof

REM Function to download AI models
:download_models
if "%SKIP_MODELS%"=="true" (
    call :print_step "Skipping model download"
    goto :eof
)

call :print_step "Downloading AI models..."

REM Check if download_models.bat exists
if exist "download_models.bat" (
    call :print_info "Using existing download_models.bat script..."
    
    REM Build download command
    set DOWNLOAD_CMD=download_models.bat --whisper-model %WHISPER_MODEL% --models-dir %MODELS_DIR%
    
    if not "%SKIP_VENV%"=="true" (
        set DOWNLOAD_CMD=%DOWNLOAD_CMD% --venv %VENV_PATH%
    )
    
    call :print_info "Executing: %DOWNLOAD_CMD%"
    call %DOWNLOAD_CMD%
) else (
    call :print_warning "download_models.bat not found, downloading models directly..."
    
    REM Set environment variables for model caching
    set PYTHONPATH=.;%PYTHONPATH%
    set WHISPER_CACHE_DIR=%MODELS_DIR%\whisper
    set HF_HOME=%MODELS_DIR%\pyannote
    
    REM Download using Python module
    python -m utils.download_models --whisper-model %WHISPER_MODEL% --models-dir %MODELS_DIR%
)

call :print_success "Model download completed ✓"
goto :eof

REM Function to display final setup summary
:show_setup_summary
call :print_header ""
call :print_header "╔══════════════════════════════════════════════════════════════╗"
call :print_header "║                    SETUP COMPLETED SUCCESSFULLY!             ║"
call :print_header "╚══════════════════════════════════════════════════════════════╝"
call :print_header ""

echo Workflow is ready to use!
echo.

echo Quick Start:
if not "%SKIP_VENV%"=="true" (
    echo   1. Activate virtual environment: %VENV_PATH%\Scripts\activate.bat
)
echo   2. Place audio files in: .\audio_input\
echo   3. Run workflow: python main.py
echo.

echo Usage Examples:
echo   python main.py                    # Process first audio file found
echo   python main.py audio.wav          # Process specific file
echo   python main.py --list-files       # List available audio files
echo   python main.py --step transcribe  # Run only transcription
echo.
goto :eof

REM Main execution function
:main
call :print_header ""
call :print_header "╔══════════════════════════════════════════════════════════════╗"
call :print_header "║  This script will set up your complete development           ║"
call :print_header "║  environment for cognitive workflow                          ║"
call :print_header "╚══════════════════════════════════════════════════════════════╝"
call :print_header ""

call :print_info "Starting setup process..."
call :print_info "Virtual environment: %VENV_PATH%"
call :print_info "Models directory: %MODELS_DIR%"
call :print_info "Whisper model: %WHISPER_MODEL%"
echo.

REM Execute setup steps
call :check_system_requirements
echo.

call :create_virtual_environment
echo.

call :activate_virtual_environment
echo.

call :upgrade_pip
echo.

call :install_dependencies
echo.

call :create_directories
echo.

call :download_models
echo.

call :show_setup_summary
goto :eof

REM Execute main function
call :main 