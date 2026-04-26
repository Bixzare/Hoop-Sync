import streamlit as st
import requests
import time
import os

st.set_page_config(
    page_title="Hoop Synch",
    page_icon="icons/hoop_sync_H.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Streamlit Native Logo (Sidebar + Collapsed Sidebar)
st.logo("icons/hoop_sync_full.svg", icon_image="icons/hoop_sync_H.svg")

# Custom CSS for UI Aesthetics
st.markdown("""
<style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    h1, h2, h3, h4 { color: #FF7F50 !important; font-family: 'Inter', sans-serif; }
    .stButton>button {
        background-color: #FF7F50; color: #121212;
        border-radius: 8px; border: none; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #FF9F7A; box-shadow: 0 4px 12px rgba(255, 127, 80, 0.4);
    }
    .clip-card {
        background-color: #1e1e1e; border-radius: 10px; padding: 15px;
        margin-bottom: 20px; border-left: 4px solid #FF7F50; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-align: center;
    }
    .tag {
        display: inline-block; padding: 4px 10px; border-radius: 15px;
        background-color: #2d2d2d; color: #FF7F50; font-size: 14px; font-weight: bold; margin: 4px;
    }
    .stat-box {
        background-color: #1e1e1e; border: 2px solid #FF7F50; border-radius: 10px;
        padding: 20px; text-align: center; margin-bottom: 30px;
    }
    .stat-number { font-size: 48px; font-weight: bold; color: #FF7F50; line-height: 1; }
    .stat-label { font-size: 18px; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .svg-container { display: flex; justify-content: center; align-items: center; margin-bottom: 20px; }
    .svg-container svg { max-width: 400px; width: 100%; height: auto; }
    
    /* Override native Streamlit logo size restrictions to make it 2.5x larger */
    [data-testid="stLogo"] { height: 3.5rem !important; }
    [data-testid="stIconLogo"] { height: 3.5rem !important; }
    img[data-testid="stLogo"] { height: 3.5rem !important; max-height: 4rem !important; }
</style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000"

if "selected_session_id" not in st.session_state:
    st.session_state.selected_session_id = None

@st.dialog("Play Highlight", width="large")
def play_clip_modal(clip_path):
    if os.path.exists(clip_path):
        with open(clip_path, "rb") as video_file:
            video_bytes = video_file.read()
        st.video(video_bytes)
    else:
        st.error("Video file not found.")

def render_dashboard(data):
    st.markdown("---")
    filename = data.get("filename", "Unknown Video")
    st.subheader(f"Instance: {filename}")
    
    status = data.get("status")
    
    if status == "completed":
        total_points = data.get("total_points", 0)
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">Total Points Expected</div>
            <div class="stat-number">{total_points}</div>
        </div>
        """, unsafe_allow_html=True)
        
        results = data.get("results", [])
        if not results:
            st.warning("No highlights detected.")
        else:
            st.markdown("### 🎥 Carousel Showcase")
            
            # Use columns as a responsive grid carousel
            cols = st.columns(4)
            for idx, res in enumerate(results):
                col = cols[idx % 4]
                with col:
                    st.markdown('<div class="clip-card">', unsafe_allow_html=True)
                    
                    # Show thumbnail
                    thumb_path = res.get("thumbnail_path")
                    if thumb_path and os.path.exists(thumb_path):
                        st.image(thumb_path, use_container_width=True)
                    else:
                        st.info("No Thumbnail")
                    
                    score = res["score"]
                    st.markdown(f"""
                    <div>
                        <span class="tag">{score['shot_result']}</span>
                        <span class="tag">{score['shot_value']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Trigger Modal
                    if st.button("Play Clip", key=f"play_{idx}"):
                        play_clip_modal(res["clip_path"])
                        
    elif status == "failed":
        st.error(f"Processing failed: {data.get('error')}")
    else:
        st.info(f"Status: {status.capitalize()}")
        p = data.get("progress", 0)
        st.progress(p)

# --- Sidebar Menu ---
st.sidebar.title("🏀 Sessions")
try:
    sessions_res = requests.get(f"{API_URL}/sessions")
    if sessions_res.status_code == 200:
        sessions = sessions_res.json()
    else:
        sessions = []
except Exception:
    sessions = []

if sessions:
    st.sidebar.markdown("### History")
    for s in reversed(sessions):
        icon = "✅" if s["status"] == "completed" else "⏳" if s["status"] in ["pending", "extracting", "classifying"] else "❌"
        if st.sidebar.button(f"{icon} {s.get('filename', 'Video')}", key=f"btn_{s['id']}"):
            st.session_state.selected_session_id = s["id"]
else:
    st.sidebar.info("No previous sessions found.")

# --- Main Page ---
# Render Full SVG for the main header instead of text
import base64
try:
    with open("icons/hoop_sync_full.svg", "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    st.markdown(f'<div class="svg-container"><img src="data:image/svg+xml;base64,{b64}"/></div>', unsafe_allow_html=True)
except Exception:
    st.title("Hoop Synch Dashboard")

st.markdown("<h4 style='text-align: center; color: #888;'>Upload a stream and automatically sync your highlights</h4>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Upload UI
uploaded_file = st.file_uploader("Upload Basketball Video (.mp4)", type=["mp4", "mov", "avi"])
if uploaded_file is not None:
    if st.button("Process New Video"):
        with st.spinner("Uploading video..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
            try:
                response = requests.post(f"{API_URL}/upload", files=files)
                response.raise_for_status()
                if response.status_code == 200:
                    st.session_state.selected_session_id = response.json()["task_id"]
                    st.success("Upload complete! Processing video...")
                    time.sleep(1) # Let the state register before rerun
                    st.rerun()
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend. Make sure it is running.")
            except Exception as e:
                st.error(f"Upload failed: {e}")

# Dashboard View
if st.session_state.selected_session_id:
    placeholder = st.empty()
    while True:
        try:
            status_res = requests.get(f"{API_URL}/status/{st.session_state.selected_session_id}")
            if status_res.status_code == 200:
                data = status_res.json()
                status = data.get("status")
                
                if status in ["completed", "failed"]:
                    with placeholder.container():
                        render_dashboard(data)
                    break
                else:
                    with placeholder.container():
                        st.subheader(f"Instance: {data.get('filename', 'Video')}")
                        if status == "extracting":
                            st.info(f"⛹️‍♂️ Extracting plays with YOLOv8... ({data.get('progress', 0)}%)")
                        elif status == "classifying":
                            st.info("🧠 Classifying shots with R(2+1)D...")
                        else:
                            st.info(f"Status: {status.capitalize()}")
                        st.progress(data.get("progress", 0))
                    time.sleep(2)
            else:
                st.error("Failed to fetch status.")
                break
        except requests.exceptions.ConnectionError:
            st.error("Backend connection lost.")
            break
