import webview
import threading
import uvicorn
import sys
import os
import time
from api import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    # 1. Start FastAPI in a daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 2. Wait a bit for server to warm up
    time.sleep(1)
    
    # 3. Create and launch a professional webview window
    print("Launching Q-Sound Web UI...")
    window = webview.create_window(
        'Q-Sound - Premium Audio Hub', 
        'http://127.0.0.1:8000',
        width=1200,
        height=900,
        background_color='#050505'
    )
    
    webview.start()
