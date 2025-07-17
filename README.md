# Demo Cognitive Workflow

AI-powered audio transcription, summarization, and situation analysis system.

## What it does

1. **Transcribes** audio files using Whisper with speaker identification
2. **Summarizes** conversations using AI
3. **Judges** situations and recommends actions

## Quick Setup

### Prerequisites
- Python 3.8+
- 4GB+ RAM
- Internet connection


### Configure API Key

1. Copy the environment template:
```bash
cp env.template .env
```

2. Edit `.env` and add your API key:
```bash
API_KEY=your_imagine_api_key_here
ENDPOINT=https://aisuite.cirrascale.com/apis/v2
HUGGINGFACE_TOKEN=your_huggingface_token_here 
```

### Download Required Imagine SDK

Download and place the Imagine SDK in project directory (setup.sh script will install it for you):
https://aisuite.cirrascale.com/sdk/install.html

### Install

```bash
# Clone and enter the project
cd cognative_workflow

# Run setup script
chmod +x setup.sh
./setup.sh

# Activate environment
source venv/bin/activate
```


## Usage

### Configuration

Key settings can be adjusted in `config/settings.py`:


### Basic Usage

```bash
# Place audio files in audio_input/ folder
# Then run:
python main.py

# Or specify a file directly:
python main.py path/to/your/audio.wav
```


## Supported Audio Formats

WAV, MP3, M4A, FLAC, OGG, AAC

## Output

Results are saved in `outputs/run_<time_stamp>` folder:
- `transcription.txt` - Speaker-labeled transcript
- `summary.txt` - Conversation summary  
- `judgment.json` - Situation analysis and recommendations
- `performance_metrics.json` - models performance evaluation