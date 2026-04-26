import cv2
import os
import torch
from collections import deque
from ultralytics import YOLO

def is_rim_event(ball_box, rim_box, margin=15):
    """Checks if ball intersects rim OR is directly above and aligned with it."""
    # Intersection Check
    x1 = max(ball_box[0] - margin, rim_box[0] - margin)
    y1 = max(ball_box[1] - margin, rim_box[1] - margin)
    x2 = min(ball_box[2] + margin, rim_box[2] + margin)
    y2 = min(ball_box[3] + margin, rim_box[3] + margin)
    if x1 < x2 and y1 < y2:
        return True

    # Ball Above Rim & Horizontally Aligned
    # y-axis increases from top to bottom in OpenCV
    ball_above = ball_box[3] < rim_box[1]
    horizontally_aligned = (ball_box[2] >= rim_box[0] - margin) and (ball_box[0] <= rim_box[2] + margin)

    return ball_above and horizontally_aligned

def extract_highlights(video_path, model_path, out_dir, progress_callback=None):
    os.makedirs(out_dir, exist_ok=True)
    
    # Load model (if missing, this will fail gracefully or we can add check, but we assume it's downloaded)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"YOLO model not found at {model_path}")
        
    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError("Failed to open video stream.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    shooter_pre, shooter_post = int(1 * fps), int(5 * fps)
    rim_pre, rim_post = int(3 * fps), int(3 * fps)

    max_pre_frames = max(shooter_pre, rim_pre)
    ring_buffer = deque(maxlen=max_pre_frames)
    shooter_history = deque([0]*5, maxlen=5)
    rim_history = deque([0]*5, maxlen=5)

    recording = False
    frames_left = 0
    clip_idx = 0
    writer = None

    generated_clips = []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    current_frame = 0

    while True:
        ret, frame = cap.read()
        if not ret: break

        current_frame += 1
        if progress_callback and current_frame % 5 == 0:
            progress_callback(current_frame, total_frames)

        ring_buffer.append(frame)

        # Use GPU if available
        device = 0 if torch.cuda.is_available() else 'cpu'
        results = model.predict(frame, conf=0.5, verbose=False, device=device)

        boxes = results[0].boxes.xyxy.cpu().numpy() if len(results[0].boxes) else []
        classes = results[0].boxes.cls.cpu().numpy() if len(results[0].boxes) else []

        has_shooter, has_rim_event = 0, 0
        balls, rims = [], []

        for box, cls_id in zip(boxes, classes):
            if int(cls_id) == 0: has_shooter = 1
            elif int(cls_id) == 1: balls.append(box)
            elif int(cls_id) == 2: rims.append(box)

        if balls and rims:
            for b in balls:
                for r in rims:
                    if is_rim_event(b, r):
                        has_rim_event = 1
                        break
                if has_rim_event: break

        shooter_history.append(has_shooter)
        rim_history.append(has_rim_event)

        shooter_trigger = sum(shooter_history) >= 3
        rim_trigger = sum(rim_history) >= 3

        # Only start a new clip if we are not already recording
        if (shooter_trigger or rim_trigger) and not recording:
            recording = True

            # Determine clip type bounds based on your rules
            if rim_trigger:
                pre_needed = rim_pre
                frames_left = rim_post
            else:
                pre_needed = shooter_pre
                frames_left = shooter_post

            clip_path = os.path.join(out_dir, f"highlight_{clip_idx:04d}.mp4")
            writer = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
            clip_idx += 1

            for buf_frame in list(ring_buffer)[-pre_needed:]:
                writer.write(buf_frame)

            shooter_history.clear(); shooter_history.extend([0]*5)
            rim_history.clear(); rim_history.extend([0]*5)

        if recording:
            writer.write(frame)
            frames_left -= 1
            if frames_left <= 0:
                recording = False
                writer.release()
                writer = None
                generated_clips.append(clip_path)

    if writer: 
        writer.release()
        generated_clips.append(clip_path)
    cap.release()
    
    # Critical step: free GPU memory to allow R(2+1)D model to run
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return generated_clips
