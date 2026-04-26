import subprocess
import sys
import os
import signal

def main():
    print("=========================================")
    print("Starting Basketball CV Pipeline...")
    print("=========================================\n")
    
    # Ensure we are in the correct directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    # Start FastAPI Backend
    print("-> Starting FastAPI Backend on port 8000...")
    fastapi_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    # Start Streamlit Frontend
    print("-> Starting Streamlit Frontend on port 8501...")
    # Streamlit output is also piped to stdout/stderr
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "ui/app.py"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    def cleanup(signum=None, frame=None):
        print("\n=========================================")
        print("Shutting down pipeline components...")
        print("=========================================")
        fastapi_process.terminate()
        streamlit_process.terminate()
        fastapi_process.wait()
        streamlit_process.wait()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        fastapi_process.wait()
        streamlit_process.wait()
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
