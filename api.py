import os
import sys
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from scraper import MyInstantsScraper
from audio_engine import AudioEngine

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = FastAPI(title="Q-Sound API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core components
scraper = MyInstantsScraper()
engine = AudioEngine()
FAVORITES_FILE = get_resource_path("favorites.json")

class Sound(BaseModel):
    name: str
    url: str

class PlayRequest(BaseModel):
    url: str
    device_ids: List[int]

class VolumeRequest(BaseModel):
    level: float

def load_favs():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return []
    return []

def save_favs(favs):
    with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(favs, f, indent=4)

@app.get("/sounds")
async def get_sounds(page: int = 1):
    try:
        return scraper.get_tr_trending(page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_sounds(q: str):
    try:
        return scraper.search(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/play")
async def play_sound(req: PlayRequest):
    try:
        # We start in a background thread within the engine
        engine.play_from_url(req.url, req.device_ids)
        return {"status": "playing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def stop_sound():
    engine.stop_all()
    return {"status": "stopped"}

@app.get("/devices")
async def get_devices():
    return {
        "output": engine.get_output_devices(),
        "input": engine.get_input_devices()
    }

@app.post("/volume")
async def set_volume(req: VolumeRequest):
    engine.volume = max(0.0, min(1.0, req.level))
    return {"volume": engine.volume}

@app.get("/favorites")
async def get_favorites():
    return load_favs()

@app.post("/favorites/toggle")
async def toggle_favorite(sound: Sound):
    favs = load_favs()
    found = next((f for f in favs if f['url'] == sound.url), None)
    if found:
        favs.remove(found)
    else:
        favs.append(sound.dict())
    save_favs(favs)
    return favs

@app.post("/mic/toggle")
async def toggle_mic(input_id: int, output_id: int, enable: bool):
    if enable:
        success = engine.start_passthrough(input_id, output_id)
        return {"status": "enabled" if success else "failed"}
    else:
        engine.stop_passthrough()
        return {"status": "disabled"}

@app.get("/mic/status")
async def get_mic_status():
    return {"enabled": engine.passthrough_stream is not None}

# Mount static files AFTER routes
web_dir = get_resource_path("web")
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
