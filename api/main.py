import os
import sys
import uuid
import asyncio
import json
import cv2
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from typing import Dict
import shutil

# Add the parent directory to sys.path to allow imports from ml_core
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ml_core.extractor import extract_highlights
from ml_core.classifier import score_clip

app = FastAPI(title="Basketball CV Pipeline")

# Directories
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
CLIPS_DIR = os.path.join(BASE_DIR, "data", "pending_clips")
SESSIONS_FILE = os.path.join(BASE_DIR, "data", "sessions.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

# Path to the YOLO trigger model. This must be present for extract_highlights to work.
MODEL_PATH = os.path.join(BASE_DIR, "basketball_trigger_nano.pt") 

def load_tasks() -> Dict[str, dict]:
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tasks(tasks_dict):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(tasks_dict, f, indent=4)

# In-memory task store synced with disk
tasks: Dict[str, dict] = load_tasks()

def extract_thumbnail(video_path: str, thumbnail_path: str):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(thumbnail_path, frame)
    cap.release()

def process_video_task(task_id: str, video_path: str):
    try:
        tasks[task_id]["status"] = "extracting"
        save_tasks(tasks)
        
        # 1. Extract clips (YOLO extraction)
        out_dir = os.path.join(CLIPS_DIR, task_id)
        os.makedirs(out_dir, exist_ok=True)
        
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"YOLO model not found at {MODEL_PATH}. Please provide the correct model file.")

        def update_progress(current, total):
            if total > 0:
                p = int((current / total) * 100)
                tasks[task_id]["progress"] = p
                print(f"Extraction Progress: {p}% ({current}/{total} frames)\r", end="")

        clips = extract_highlights(video_path, MODEL_PATH, out_dir, progress_callback=update_progress)
        
        tasks[task_id]["status"] = "classifying"
        save_tasks(tasks)
        
        results = []
        total_points = 0
        
        # 2. Classify each clip (R(2+1)D classification)
        for clip in clips:
            # Generate thumbnail
            thumbnail_path = clip.replace(".mp4", ".jpg")
            extract_thumbnail(clip, thumbnail_path)
            
            score = score_clip(clip)
            
            # Placeholder point aggregation
            if score["shot_result"] == "Make":
                if score["shot_value"] == "3pt":
                    total_points += 3
                elif score["shot_value"] == "2pt":
                    total_points += 2
            
            results.append({
                "clip_path": clip,
                "thumbnail_path": thumbnail_path,
                "score": score
            })
            
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["results"] = results
        tasks[task_id]["total_points"] = total_points
        save_tasks(tasks)
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        save_tasks(tasks)
        import traceback
        traceback.print_exc()

@app.post("/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    video_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    tasks[task_id] = {
        "id": task_id,
        "filename": file.filename,
        "status": "pending",
        "progress": 0,
        "results": [],
        "total_points": 0
    }
    save_tasks(tasks)
    
    background_tasks.add_task(process_video_task, task_id, video_path)
    return {"task_id": task_id, "message": "Video uploaded successfully. Processing started."}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        return {"status": "not_found"}
    return tasks[task_id]

@app.get("/sessions")
async def get_sessions():
    return list(tasks.values())
