@echo off
setlocal enabledelayedexpansion

REM download_models.bat
REM Script to download AI models using download_models.py
REM Usage: download_models.bat [options]

REM Default values
set WHISPER_MODEL=turbo
set MODELS_DIR=.\models
set SKIP_WHISPER=false
set SKIP_PYANNOTE=false
set VIRTUAL_ENV_PATH=.\venv

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse
if "%~1"=="-w" (
    set WHISPER_MODEL=%~2
    shift
)
if "%~1"=="--whisper-model" (
    set WHISPER_MODEL=%~2
    shift
)
if "%~1"=="-d" (
    set MODELS_DIR=%~2
    shift
)
if "%~1"=="--models-dir" (
    set MODELS_DIR=%~2
    shift
)
if "%~1"=="--skip-whisper" set SKIP_WHISPER=true
if "%~1"=="--skip-pyannote" set SKIP_PYANNOTE=true
if "%~1"=="--venv" (
    set VIRTUAL_ENV_PATH=%~2
    shift
)
if "%~1"=="-h" goto :show_usage
if "%~1"=="--help" goto :show_usage
shift
goto :parse_args
:end_parse

REM Project root directory
set PROJECT_ROOT=.

REM Python script path
set PYTHON_SCRIPT=%PROJECT_ROOT%\utils\download_models.py

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

REM Function to show usage
:show_usage
echo Usage: download_models.bat [OPTIONS]
echo.
echo Download AI models for cognitive workflow application
echo.
echo OPTIONS:
echo   -w, --whisper-model MODEL    Whisper model to download (default: turbo)
echo                                Options: tiny, base, small, medium, large, large-v2, large-v3, turbo
echo   -d, --models-dir DIR         Directory to store models (default: .\models)
echo   --skip-whisper               Skip Whisper model download
echo   --skip-pyannote              Skip pyannote model download
echo   --venv PATH                  Path to virtual environment (default: .\venv)
echo   -h, --help                   Show this help message
echo.
echo Examples:
echo   download_models.bat                          # Download default models
echo   download_models.bat -w base                  # Download base Whisper model
echo   download_models.bat --skip-whisper           # Only download pyannote model
echo   download_models.bat -d C:\custom\models     # Use custom models directory
echo.
exit /b 0

REM Function to check if Python script exists
:check_python_script
if not exist "%PYTHON_SCRIPT%" (
    call :print_error "Python script not found: %PYTHON_SCRIPT%"
    call :print_info "Make sure the utils.download_models module exists"
    exit /b 1
)
call :print_info "Found download_models.py script"
goto :eof

REM Function to check and activate virtual environment
:setup_python_env
if exist "%VIRTUAL_ENV_PATH%" (
    call :print_info "Activating virtual environment: %VIRTUAL_ENV_PATH%"
    call "%VIRTUAL_ENV_PATH%\Scripts\activate.bat"
) else (
    call :print_warning "Virtual environment not found at %VIRTUAL_ENV_PATH%"
    call :print_info "Using system Python environment"
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python is not installed or not in PATH"
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>nul') do set PYTHON_VERSION=%%i
call :print_info "Using Python: %PYTHON_VERSION%"

REM Set PYTHONPATH to include project root to resolve app module imports
set PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%
call :print_info "Set PYTHONPATH: %PYTHONPATH%"
goto :eof

REM Function to check .env file for HuggingFace token
:check_env_file
set ENV_FILE=%PROJECT_ROOT%\.env
if not exist "%ENV_FILE%" (
    call :print_warning ".env file not found at %ENV_FILE%"
    call :print_info "You may need to create .env file with HUGGINGFACE_TOKEN for pyannote models"
    call :print_info "See env.template for reference"
    goto :eof
)

findstr "HUGGINGFACE_TOKEN=" "%ENV_FILE%" >nul
if errorlevel 1 (
    call :print_warning "HUGGINGFACE_TOKEN not found in .env file"
    call :print_info "Add HUGGINGFACE_TOKEN=your_token_here to .env for pyannote models"
    goto :eof
)

findstr "HUGGINGFACE_TOKEN=your_huggingface_token_here" "%ENV_FILE%" >nul
if not errorlevel 1 (
    call :print_warning "Default HuggingFace token found in .env"
    call :print_info "Update .env with your actual token for pyannote models"
) else (
    call :print_success "HuggingFace token configured in .env"
)
goto :eof

REM Main execution
:main
call :print_info "Starting AI model download process..."
call :print_info "Project root: %PROJECT_ROOT%"
call :print_info "Models directory: %MODELS_DIR%"
call :print_info "Whisper model: %WHISPER_MODEL%"

REM Checks
call :check_python_script
call :setup_python_env
call :check_env_file

REM Create models directory if it doesn't exist
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

REM Build Python command
REM Run as module to avoid import conflicts with local logging.py
set PYTHON_CMD=python -m utils.download_models --whisper-model %WHISPER_MODEL% --models-dir %MODELS_DIR%

if "%SKIP_WHISPER%"=="true" (
    set PYTHON_CMD=%PYTHON_CMD% --skip-whisper
)

if "%SKIP_PYANNOTE%"=="true" (
    set PYTHON_CMD=%PYTHON_CMD% --skip-pyannote
)

call :print_info "Executing: %PYTHON_CMD%"
echo.

REM Change to project root and run the Python script
cd /d "%PROJECT_ROOT%"

%PYTHON_CMD%
if errorlevel 1 (
    call :print_error "Model download failed!"
    exit /b 1
)

call :print_success "Model download completed successfully!"

REM Show cache information
if exist "%MODELS_DIR%" (
    call :print_info "Cache location: %MODELS_DIR%"
)

goto :eof

REM Execute main function
call :main 