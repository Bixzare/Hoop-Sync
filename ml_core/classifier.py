import time

def score_clip(clip_path: str) -> dict:
    """
    Dummy scoring function for the R(2+1)D model.
    TODO: Teammate to drop in their PyTorch logic here!
    
    Expected logic:
    1. Load R(2+1)D model (ensure device matches, e.g., 'cuda')
    2. Read frames from clip_path
    3. Run inference
    4. Free VRAM when done processing all clips if necessary
    5. Return a dictionary with 'shot_result' and 'shot_value'
    """
    
    # Simulate processing time
    time.sleep(1)
    
    # Dummy results
    return {
        "shot_result": "Make",
        "shot_value": "3pt"
    }
