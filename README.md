# Setup Instructions

This guide will walk you through setting up the Demo Cognitive Workflow system on your machine.

## Prerequisites

- Python 3.11+ installed
- Git installed
- PowerShell (for Windows users)
- Internet connection for downloading models

## Step-by-Step Setup

### 1. Clone the Main Repository

```bash
git clone https://github.com/mobisense-org/cognitive_workflow
cd cognitive_workflow
```

### 2. Clone AI Hub Apps Submodule

```bash
git clone https://github.com/quic/ai-hub-apps/
```

### 3. Create Python Virtual Environment

```bash
python -m venv .venv
```

### 4. Activate Virtual Environment

**Linux/macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 6. Setup Environment Variables

Copy the environment template and configure:

```bash
cp env.template .env
```

Edit `.env` file with your:
- `API_KEY`: Your Imagine API key
- `ENDPOINT`: API endpoint URL
- `HUGGINGFACE_TOKEN`: HuggingFace token for pyannote models

### 7. Configure QAI Hub Token

Sign in to Qualcomm AI Hub with your Qualcomm® ID. After signing in, navigate to [your Qualcomm ID] → Settings → API Token. This should provide an API token that you can use to configure your client:

```bash
qai-hub configure --api_token API_TOKEN
```

**Note:** The QAI Hub client is already included in the requirements.txt installation from step 5.

### 8. Setup AI Hub Whisper Models

Navigate to the Whisper application directory:

```bash
cd ./ai-hub-apps/apps/windows/python/Whisper/
```

### 7. Install FFmpeg

Run the platform dependencies installer (only accept ffmpeg when prompted):

```powershell
..\install_platform_deps.ps1 -extra_pkgs ffmpeg
```

**Important:** When prompted, only say "yes" to ffmpeg installation.

### 8. Verify FFmpeg Installation

After installation, check if ffmpeg is properly installed:

```bash
ffmpeg -version
```

**If ffmpeg is not recognized:**
- **Windows users:** Restart your terminal or open a new PowerShell/Command Prompt window
- The installer may require a fresh terminal session to update the PATH environment variable
- If the issue persists, you may need to restart your computer

**Expected output:** You should see ffmpeg version information and configuration details.

### 9. Export Whisper Model

Export the Whisper model for ONNX runtime:

```bash
python -m qai_hub_models.models.whisper_base_en.export --target-runtime onnx --device "Snapdragon X Elite CRD" --skip-profiling --skip-inferencing
```

### 10. Setup Model Files

Extract and organize the exported model files:

```powershell
# Extract WhisperEncoderInf
Expand-Archive -Path .\build\whisper_base_en\WhisperEncoderInf.onnx.zip -DestinationPath .\build\whisper_base_en\
mv .\build\whisper_base_en\model.onnx .\build\whisper_base_en\WhisperEncoderInf

# Extract WhisperDecoderInf
Expand-Archive -Path .\build\whisper_base_en\WhisperDecoderInf.onnx.zip -DestinationPath .\build\whisper_base_en\
mv .\build\whisper_base_en\model.onnx .\build\whisper_base_en\WhisperDecoderInf
```

### 11. Return to Main Directory

```bash
cd ../../../../../
```

You should now be back in the `cognitive_workflow` directory.

### 12. Configure Settings

Edit the configuration file for your use case:

```bash
# Open config/settings.py and adjust parameters as needed
```

### 13. Setup Environment Variables

Copy the environment template and configure:

```bash
cp env.template .env
```

Edit `.env` file with your:
- `API_KEY`: Your Imagine API key
- `ENDPOINT`: API endpoint URL
- `HUGGINGFACE_TOKEN`: HuggingFace token for pyannote models

### 14. Test the Installation

Run the test script:

```bash
python main.py
```

### 15. Check Results

Results will be saved in the `outputs` folder with timestamped directories containing:
- `transcription.txt` - Speaker-labeled transcript
- `summary.txt` - Conversation summary
- `judgment.json` - Situation analysis and recommendations
- `performance_metrics.json` - Processing performance data


## Usage

Once setup is complete, you can:

- Process audio files: `python main.py`
- Process specific files: `python main.py path/to/audio.wav`
- Run individual steps: `python main.py --step transcribe audio.wav`
- View available files: `python main.py --list-files`

For more usage options, see the main README.md file.