# Hoop Synch Pipeline

**Hoop Synch** is a decoupled, asynchronous Computer Vision pipeline using Streamlit (Frontend) and FastAPI (Backend) for automatically extracting and classifying basketball highlights.

## Features & Architecture

1. **Extraction (YOLOv8)**: Scans a video stream to extract short highlight clips based on a state-machine that detects shooter, ball, and rim interactions.
2. **Classification (R(2+1)D / Video Swin)**: Scores each extracted clip (e.g., "Make/Miss", "3pt/2pt") to automatically tally points for the session.
3. **Instance History**: All processed sessions are persisted locally (`data/sessions.json`). You can revisit any previous upload via the Streamlit sidebar.
4. **Carousel Showcase**: Extracted highlights are rendered in a sleek responsive grid with generated thumbnail previews. Click any clip to watch it in a cinematic pop-up modal.
5. **Live Progress Tracking**: The pipeline features asynchronous task queuing. Streamlit polls the backend and dynamically updates a progress bar and status indicator as YOLO and Swin models run.

### GPU Memory Management (VRAM)
To support running this on local GPUs with limited VRAM (e.g., RTX 2050), the pipeline is strictly compartmentalized. VRAM is forcibly cleared (`del model`, `torch.cuda.empty_cache()`) between the YOLO extraction phase and the Classification phase.

## File Structure

```text
/basketball_cv_pipeline/
├── api/
│   └── main.py              # FastAPI app (handles async tasks, sessions, & endpoints)
├── ui/
│   └── app.py               # Streamlit frontend (Dashboard, Carousel, Modals)
├── ml_core/
│   ├── extractor.py         # YOLO state machine logic & frame extraction
│   └── classifier.py        # R(2+1)D dummy logic for classification
├── data/
│   ├── uploads/             # Raw user video uploads
│   ├── pending_clips/       # Output from YOLO, input for Classifier
│   └── sessions.json        # Persistent instance history
├── icons/                   # Custom SVG branding assets
├── requirements.txt         # Dependencies
├── run_pipeline.py          # Unified startup and logging script
└── README.md
```

## Setup & Execution

### 1. Environment Setup (Python 3.12)
This project requires a **Python 3.12 virtual environment**.

```bash
# Create and activate a Python 3.12 virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Model Files
Ensure that your YOLO model (`basketball_trigger_nano.pt`) is placed in the root `basketball_cv_pipeline/` directory before running the pipeline.

### 3. Run the Pipeline
We provide a unified launch script that starts both the FastAPI backend and Streamlit frontend concurrently while streaming their logs to your terminal:

```bash
python run_pipeline.py
```

- The **Hoop Synch UI** will be available at: `http://localhost:8501`
- The **FastAPI Backend** will be available at: `http://localhost:8000`
