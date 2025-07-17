#!/bin/bash

# download_models.sh
# Script to download AI models using download_models.py
# Usage: ./scripts/download_models.sh [options]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root directory (parent of scripts)
PROJECT_ROOT="."

# Python script path
PYTHON_SCRIPT="$PROJECT_ROOT/utils/download_models.py"

# Default values
WHISPER_MODEL="turbo"
MODELS_DIR="$PROJECT_ROOT/models"
SKIP_WHISPER=false
SKIP_PYANNOTE=false
VIRTUAL_ENV_PATH="$PROJECT_ROOT/venv"

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Download AI models for diarization application"
    echo ""
    echo "OPTIONS:"
    echo "  -w, --whisper-model MODEL    Whisper model to download (default: turbo)"
    echo "                               Options: tiny, base, small, medium, large, large-v2, large-v3, turbo"
    echo "  -d, --models-dir DIR         Directory to store models (default: ./models)"
    echo "  --skip-whisper              Skip Whisper model download"
    echo "  --skip-pyannote             Skip pyannote model download"
    echo "  --venv PATH                 Path to virtual environment (default: ./venv)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Download default models"
    echo "  $0 -w base                  # Download base Whisper model"
    echo "  $0 --skip-whisper           # Only download pyannote model"
    echo "  $0 -d /custom/models        # Use custom models directory"
}

# Function to check if Python script exists
check_python_script() {
    if [[ ! -f "$PYTHON_SCRIPT" ]]; then
        print_error "Python script not found: $PYTHON_SCRIPT"
        print_info "Make sure the utils.download_models module exists"
        exit 1
    fi
    print_info "Found download_models.py script"
}

# Function to check and activate virtual environment
setup_python_env() {
    if [[ -d "$VIRTUAL_ENV_PATH" ]]; then
        print_info "Activating virtual environment: $VIRTUAL_ENV_PATH"
        source "$VIRTUAL_ENV_PATH/bin/activate"
    else
        print_warning "Virtual environment not found at $VIRTUAL_ENV_PATH"
        print_info "Using system Python environment"
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is not installed or not in PATH"
        exit 1
    fi
    
    print_info "Using Python: $(which python3)"
    print_info "Python version: $(python3 --version)"
    
    # Set PYTHONPATH to include project root to resolve app module imports
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    print_info "Set PYTHONPATH: $PYTHONPATH"
}

# Function to check .env file for HuggingFace token
check_env_file() {
    ENV_FILE="$PROJECT_ROOT/.env"
    if [[ ! -f "$ENV_FILE" ]]; then
        print_warning ".env file not found at $ENV_FILE"
        print_info "You may need to create .env file with HUGGINGFACE_TOKEN for pyannote models"
        print_info "See env.template for reference"
    else
        if grep -q "HUGGINGFACE_TOKEN=" "$ENV_FILE"; then
            if grep -q "HUGGINGFACE_TOKEN=your_huggingface_token_here" "$ENV_FILE"; then
                print_warning "Default HuggingFace token found in .env"
                print_info "Update .env with your actual token for pyannote models"
            else
                print_success "HuggingFace token configured in .env"
            fi
        else
            print_warning "HUGGINGFACE_TOKEN not found in .env file"
            print_info "Add HUGGINGFACE_TOKEN=your_token_here to .env for pyannote models"
        fi
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--whisper-model)
            WHISPER_MODEL="$2"
            shift 2
            ;;
        -d|--models-dir)
            MODELS_DIR="$2"
            shift 2
            ;;
        --skip-whisper)
            SKIP_WHISPER=true
            shift
            ;;
        --skip-pyannote)
            SKIP_PYANNOTE=true
            shift
            ;;
        --venv)
            VIRTUAL_ENV_PATH="$2"
            shift 2
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

# Main execution
main() {
    print_info "Starting AI model download process..."
    print_info "Project root: $PROJECT_ROOT"
    print_info "Models directory: $MODELS_DIR"
    print_info "Whisper model: $WHISPER_MODEL"
    
    # Checks
    check_python_script
    setup_python_env
    check_env_file
    
    # Create models directory if it doesn't exist
    mkdir -p "$MODELS_DIR"
    
    # Build Python command
    # Run as module to avoid import conflicts with local logging.py
    PYTHON_CMD="python3 -m utils.download_models --whisper-model $WHISPER_MODEL --models-dir $MODELS_DIR"
    
    if [[ "$SKIP_WHISPER" == true ]]; then
        PYTHON_CMD="$PYTHON_CMD --skip-whisper"
    fi
    
    if [[ "$SKIP_PYANNOTE" == true ]]; then
        PYTHON_CMD="$PYTHON_CMD --skip-pyannote"
    fi
    
    print_info "Executing: $PYTHON_CMD"
    echo ""
    
    # Change to project root and run the Python script
    cd "$PROJECT_ROOT"
    
    if eval "$PYTHON_CMD"; then
        print_success "Model download completed successfully!"
        
        # Show cache information
        if [[ -d "$MODELS_DIR" ]]; then
            CACHE_SIZE=$(du -sh "$MODELS_DIR" 2>/dev/null | cut -f1 || echo "unknown")
            print_info "Total cache size: $CACHE_SIZE"
            print_info "Cache location: $(realpath "$MODELS_DIR")"
        fi
        
    else
        print_error "Model download failed!"
        exit 1
    fi
}

# Run main function
main "$@" 