#!/bin/bash

# setup.sh
# This script sets up the environment for the diarization application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Project configuration
VENV_NAME="venv"
PYTHON_MIN_VERSION="3.8"
REQUIREMENTS_FILE="requirements.txt"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}${BOLD}$1${NC}"
}

print_step() {
    echo -e "${BOLD}$1${NC}"
}

# Function to show script usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup script for $PROJECT_NAME

OPTIONS:
  --skip-models           Skip model download step
  --skip-venv             Skip virtual environment creation (use existing)
  --hf-token TOKEN        Provide HuggingFace token directly
  --python-cmd CMD        Use specific Python command (default: python3)
  --venv-path PATH        Use custom virtual environment path
  --models-dir DIR        Custom models directory (default: ./models)
  --whisper-model MODEL   Whisper model to download (default: turbo)
  --force                 Force reinstallation of dependencies
  -h, --help              Show this help message

Examples:
  $0                                    # Full setup with default options
  $0 --skip-models                      # Setup without downloading models
  $0 --hf-token hf_abc123               # Setup with HuggingFace token
  $0 --python-cmd python3.9             # Use specific Python version
  $0 --whisper-model base               # Use base Whisper model instead of turbo

EOF
}

# Parse command line arguments
SKIP_MODELS=false
SKIP_VENV=false
HF_TOKEN=""
PYTHON_CMD="python3"
VENV_PATH=""
MODELS_DIR="./models"
WHISPER_MODEL="turbo"
FORCE_INSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-models)
            SKIP_MODELS=true
            shift
            ;;
        --skip-venv)
            SKIP_VENV=true
            shift
            ;;
        --hf-token)
            HF_TOKEN="$2"
            shift 2
            ;;
        --python-cmd)
            PYTHON_CMD="$2"
            shift 2
            ;;
        --venv-path)
            VENV_PATH="$2"
            shift 2
            ;;
        --models-dir)
            MODELS_DIR="$2"
            shift 2
            ;;
        --whisper-model)
            WHISPER_MODEL="$2"
            shift 2
            ;;
        --force)
            FORCE_INSTALL=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set default venv path if not provided
if [[ -z "$VENV_PATH" ]]; then
    VENV_PATH="./$VENV_NAME"
fi

# Function to check system requirements
check_system_requirements() {
    print_step "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_info "Operating System: Linux ✓"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "Operating System: macOS ✓"
    else
        print_warning "Untested operating system: $OSTYPE"
    fi
    
    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "$PYTHON_CMD is not installed or not in PATH"
        print_info "Please install Python $PYTHON_MIN_VERSION or later"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    print_info "Python version: $PYTHON_VERSION"
    
    # Check if Python version meets minimum requirement
    if $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python version meets requirements ✓"
    else
        print_error "Python version $PYTHON_VERSION is below minimum required version $PYTHON_MIN_VERSION"
        exit 1
    fi
    
    # Check pip
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_error "pip is not available"
        print_info "Please install pip for $PYTHON_CMD"
        exit 1
    fi
    print_success "pip is available ✓"
    
    # Check for ffmpeg (required for audio processing)
    if command -v ffmpeg &> /dev/null; then
        print_success "ffmpeg is available ✓"
    else
        print_warning "ffmpeg not found - may be needed for audio processing"
        print_info "Install with: sudo apt install ffmpeg (Ubuntu/Debian) or brew install ffmpeg (macOS)"
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df . | awk 'NR==2 {print $4}')
    if [[ $AVAILABLE_SPACE -gt 5000000 ]]; then  # 5GB in KB
        print_success "Sufficient disk space available ✓"
    else
        print_warning "Low disk space - AI models require several GB"
    fi
    
    # Check memory
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
        if [[ $TOTAL_MEM -gt 4 ]]; then
            print_success "Sufficient memory available (${TOTAL_MEM}GB) ✓"
        else
            print_warning "Limited memory (${TOTAL_MEM}GB) - consider using smaller Whisper models"
        fi
    fi
}

# Function to create virtual environment
create_virtual_environment() {
    if [[ "$SKIP_VENV" == true ]]; then
        print_step "Skipping virtual environment creation"
        return
    fi
    
    print_step "Setting up Python virtual environment..."
    
    if [[ -d "$VENV_PATH" ]] && [[ "$FORCE_INSTALL" == false ]]; then
        print_info "Virtual environment already exists at $VENV_PATH"
        read -p "Do you want to recreate it? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing virtual environment..."
            rm -rf "$VENV_PATH"
        else
            print_info "Using existing virtual environment"
            return
        fi
    fi
    
    print_info "Creating virtual environment at $VENV_PATH..."
    $PYTHON_CMD -m venv "$VENV_PATH"
    
    if [[ ! -f "$VENV_PATH/bin/activate" ]]; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    
    print_success "Virtual environment created successfully ✓"
}

# Function to activate virtual environment
activate_virtual_environment() {
    if [[ "$SKIP_VENV" == true ]]; then
        print_info "Using system Python environment"
        return
    fi
    
    print_info "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
    
    # Verify activation
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "Virtual environment activated ✓"
        print_info "Using Python: $(which python)"
    else
        print_error "Failed to activate virtual environment"
        exit 1
    fi
}

# Function to upgrade pip and install wheel
upgrade_pip() {
    print_step "Upgrading pip and installing build tools..."
    
    python -m pip install --upgrade pip
    python -m pip install wheel setuptools
    
    print_success "pip and build tools updated ✓"
}

# Function to install Python dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."
    
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        print_error "Requirements file not found: $REQUIREMENTS_FILE"
        exit 1
    fi
    
    print_info "Installing packages from $REQUIREMENTS_FILE..."
    
    if [[ "$FORCE_INSTALL" == true ]]; then
        python -m pip install --force-reinstall -r "$REQUIREMENTS_FILE"
    else
        python -m pip install -r "$REQUIREMENTS_FILE"
    fi
    
    # Install the imagine SDK wheel if it exists
    if [[ -f "imagine_sdk-0.4.2-py3-none-any.whl" ]]; then
        print_info "Installing imagine SDK from local wheel..."
        python -m pip install imagine_sdk-0.4.2-py3-none-any.whl
    fi
    
    print_success "Dependencies installed successfully ✓"
}

# Function to create project directories
create_directories() {
    print_step "Creating project directories..."
    
    directories=(
        "$MODELS_DIR"
        "$MODELS_DIR/whisper"
        "$MODELS_DIR/pyannote"
        "audio_input"
        "outputs"
        "config"
        "modules"
        "utils"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            print_info "Created directory: $dir"
        fi
    done
    
    print_success "Project directories ready ✓"
}


# Function to download AI models
download_models() {
    if [[ "$SKIP_MODELS" == true ]]; then
        print_step "Skipping model download"
        return
    fi
    
    print_step "Downloading AI models..."
    
    # Check if download_models.sh exists
    if [[ -f "download_models.sh" ]]; then
        print_info "Using existing download_models.sh script..."
        chmod +x download_models.sh
        
        # Build download command
        DOWNLOAD_CMD="./download_models.sh --whisper-model $WHISPER_MODEL --models-dir $MODELS_DIR"
        
        if [[ "$SKIP_VENV" == false ]]; then
            DOWNLOAD_CMD="$DOWNLOAD_CMD --venv $VENV_PATH"
        fi
        
        print_info "Executing: $DOWNLOAD_CMD"
        $DOWNLOAD_CMD
    else
        print_warning "download_models.sh not found, downloading models directly..."
        
        # Set environment variables for model caching
        export PYTHONPATH=".:$PYTHONPATH"
        export WHISPER_CACHE_DIR="$MODELS_DIR/whisper"
        export HF_HOME="$MODELS_DIR/pyannote"
        
        # Download using Python module
        python -m utils.download_models --whisper-model "$WHISPER_MODEL" --models-dir "$MODELS_DIR"
    fi
    
    print_success "Model download completed ✓"
}


# Function to display final setup summary
show_setup_summary() {
    print_header "
╔══════════════════════════════════════════════════════════════╗
║                    SETUP COMPLETED SUCCESSFULLY!             ║
╚══════════════════════════════════════════════════════════════╝
"
    
    echo -e "${BOLD}Workflow is ready to use!${NC}"
    echo ""
    
    echo -e "${BOLD}Quick Start:${NC}"
    if [[ "$SKIP_VENV" == false ]]; then
        echo "  1. Activate virtual environment: source $VENV_PATH/bin/activate"
    fi
    echo "  2. Place audio files in: ./audio_input/"
    echo "  3. Run workflow: python main.py"
    echo ""
    
    echo -e "${BOLD}Usage Examples:${NC}"
    echo "  python main.py                    # Process first audio file found"
    echo "  python main.py audio.wav          # Process specific file"
    echo "  python main.py --list-files       # List available audio files"
    echo "  python main.py --step transcribe  # Run only transcription"
    echo ""
}

# Main execution function
main() {
    print_header "
╔══════════════════════════════════════════════════════════════╗
║  This script will set up your complete development           ║
║  environment for cognitive workflow                          ║
╚══════════════════════════════════════════════════════════════╝
"
    
    print_info "Starting setup process..."
    print_info "Virtual environment: $VENV_PATH"
    print_info "Models directory: $MODELS_DIR"
    print_info "Whisper model: $WHISPER_MODEL"
    echo ""
    
    # Execute setup steps
    check_system_requirements
    echo ""
    
    create_virtual_environment
    echo ""
    
    activate_virtual_environment
    echo ""
    
    upgrade_pip
    echo ""
    
    install_dependencies
    echo ""
    
    create_directories
    echo ""
        
    download_models
    echo ""
    
    show_setup_summary

    
}

# Check if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 