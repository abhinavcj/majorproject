"""
backend.py  –  SignBridge Text-to-Sign-Language API
Run: uvicorn backend:app --reload --port 8001
"""

import json
import os
import re
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
GLOSS_INDEX_PATH = BASE_DIR / "gloss_index.json"
VIDEOS_DIR = BASE_DIR / "videos"

# ── Load gloss index ───────────────────────────────────────────────────────────
if not GLOSS_INDEX_PATH.exists():
    raise RuntimeError(
        "gloss_index.json not found! Run: python build_gloss_index.py first."
    )

with open(GLOSS_INDEX_PATH) as f:
    GLOSS_INDEX: dict = json.load(f)

# Pre-build a set of available (downloaded) video IDs for fast lookup
def get_available_ids():
    if not VIDEOS_DIR.exists():
        return set()
    return {p.stem for p in VIDEOS_DIR.glob("*.mp4")}


def is_valid_mp4(video_id: str) -> bool:
    """Check if a downloaded .mp4 file is a real video (not an HTML error page)."""
    path = VIDEOS_DIR / f"{video_id}.mp4"
    if not path.exists():
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        # Real MP4/MOV files start with ftyp, moov, mdat, or free box
        # The box type is at bytes 4-7
        return len(header) >= 8 and header[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip")
    except Exception:
        return False

# ── Fingerspelling chart ───────────────────────────────────────────────────────
# Maps each letter to a Handspeak direct-download URL pattern
FINGERSPELL_BASE = "https://www.handspeak.com/spell/asl/"

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="SignBridge API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (videos folder)
VIDEOS_DIR.mkdir(exist_ok=True)
app.mount("/video-files", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")

# Serve frontend
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")


# ── Models ─────────────────────────────────────────────────────────────────────
class TranslateRequest(BaseModel):
    text: str


class SignResult(BaseModel):
    word: str
    gloss: Optional[str]
    video_id: Optional[str]
    local_url: Optional[str]      # /video/{video_id} if downloaded
    remote_url: Optional[str]     # original source URL
    found: bool
    fingerspell: Optional[List[str]]  # list of letters if not found
    source: Optional[str]


# ── Text processing ────────────────────────────────────────────────────────────
def tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, split to words."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s'-]", " ", text)
    words = text.split()
    # Remove empty or pure-punctuation tokens
    return [w.strip("'-") for w in words if w.strip("'-")]


def lookup_gloss(word: str, available_ids: set):
    """Try exact match, then some simple normalizations."""
    candidates = [word]

    # Try stripping possessives: "mother's" -> "mother"
    if word.endswith("'s"):
        candidates.append(word[:-2])

    # Try removing trailing 'ing' (walking -> walk)
    if word.endswith("ing") and len(word) > 5:
        candidates.append(word[:-3])
        candidates.append(word[:-3] + "e")  # taking -> take

    # Try removing trailing 'ed'
    if word.endswith("ed") and len(word) > 4:
        candidates.append(word[:-2])
        candidates.append(word[:-1])  # liked -> like

    # Try removing trailing 's' (plurals)
    if word.endswith("s") and len(word) > 3:
        candidates.append(word[:-1])

    for candidate in candidates:
        if candidate in GLOSS_INDEX:
            return candidate, GLOSS_INDEX[candidate]

    return None, []


def pick_best_instance(instances: list, available_ids: set):
    """Pick the best instance: prefer locally downloaded, then direct, then YouTube."""
    # First pass: prefer downloaded
    for inst in instances:
        if inst["video_id"] in available_ids:
            return inst
    # Second pass: prefer direct (non-YouTube)
    for inst in instances:
        if not inst["is_youtube"]:
            return inst
    # Fallback: first instance (YouTube)
    return instances[0] if instances else None


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root():
    html_path = BASE_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.post("/translate", response_model=List[SignResult])
def translate(req: TranslateRequest):
    available_ids = get_available_ids()
    words = tokenize(req.text)

    if not words:
        return []

    results = []
    for word in words:
        gloss, instances = lookup_gloss(word, available_ids)

        if gloss and instances:
            best = pick_best_instance(instances, available_ids)
            video_id = best["video_id"]
            is_local = video_id in available_ids and is_valid_mp4(video_id)
            
            if is_local:
                results.append(SignResult(
                    word=word,
                    gloss=gloss,
                    video_id=video_id,
                    local_url=f"/video/{video_id}",
                    remote_url=None,
                    found=True,
                    fingerspell=None,
                    source=best.get("source"),
                ))
                continue

        # Fingerspell: return individual letter signs + a spacer after each word
        for char in word:
            if not char.isalpha():
                continue
            char = char.lower()
            l_gloss, l_instances = lookup_gloss(char, available_ids)
            
            # Check for alphabet GIF fallback first
            gif_name = f"letter_{char}.gif"
            gif_path = VIDEOS_DIR / gif_name
            
            if l_gloss and l_instances:
                best = pick_best_instance(l_instances, available_ids)
                video_id = best["video_id"]
                is_local = video_id in available_ids and is_valid_mp4(video_id)
                
                if is_local:
                    results.append(SignResult(
                        word=char.upper(),
                        gloss=l_gloss,
                        video_id=video_id,
                        local_url=f"/video/{video_id}",
                        remote_url=None,
                        found=True,
                        fingerspell=None,
                        source=best.get("source"),
                    ))
                    continue
            
            if gif_path.exists():
                # Use Lifeprint alphabet GIF
                results.append(SignResult(
                    word=char.upper(),
                    gloss=f"Letter {char.upper()}",
                    video_id=f"letter_{char}",
                    local_url=f"/video/{gif_name}",
                    remote_url=None,
                    found=True,
                    fingerspell=None,
                    source="Lifeprint",
                ))
            else:
                # Final fallback (text-only marker if everything fails)
                results.append(SignResult(
                    word=char.upper(),
                    gloss=None,
                    video_id=None,
                    local_url=None,
                    remote_url=None,
                    found=False,
                    fingerspell=[char.upper()],
                    source=None,
                ))
            # Add a spacer between fingerspelled words
            results.append(SignResult(
                word="_SPACE_",
                gloss=None,
                video_id=None,
                local_url=None,
                remote_url=None,
                found=False,
                fingerspell=None,
                source="spacer",
            ))

    return results


@app.get("/video/{video_id}")
def serve_video(video_id: str):
    # Sanitize
    video_id = re.sub(r"[^a-zA-Z0-9._-]", "", video_id)
    
    # Try .mp4 first
    mp4_path = VIDEOS_DIR / f"{video_id}"
    if not mp4_path.suffix:
        mp4_path = VIDEOS_DIR / f"{video_id}.mp4"
    if mp4_path.exists():
        return FileResponse(str(mp4_path), media_type="video/mp4")
    
    # Try .gif for alphabet
    gif_path = VIDEOS_DIR / f"{video_id}"
    if not gif_path.suffix:
        gif_path = VIDEOS_DIR / f"{video_id}.gif"
    if gif_path.exists():
        return FileResponse(str(gif_path), media_type="image/gif")
        
    raise HTTPException(status_code=404, detail=f"Video {video_id} not found locally.")


import urllib.request as _urllib_req
from fastapi.responses import StreamingResponse

@app.get("/proxy-video")
def proxy_video(url: str):
    """Proxy a remote video URL through the server to avoid CORS issues."""
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    try:
        req_headers = {"User-Agent": "Mozilla/5.0", "Referer": url}
        req = _urllib_req.Request(url, headers=req_headers)
        resp = _urllib_req.urlopen(req, timeout=15)
        content_type = resp.headers.get("Content-Type", "video/mp4")
        
        def iter_content():
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                yield chunk
        
        return StreamingResponse(iter_content(), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy failed: {e}")



@app.get("/glosses")
def list_glosses():
    available_ids = get_available_ids()
    result = []
    for gloss, instances in GLOSS_INDEX.items():
        has_local = any(inst["video_id"] in available_ids for inst in instances)
        has_direct = any(not inst["is_youtube"] for inst in instances)
        result.append({
            "gloss": gloss,
            "local": has_local,
            "direct_available": has_direct,
            "instance_count": len(instances),
        })
    return result


@app.get("/stats")
def stats():
    available_ids = get_available_ids()
    total_glosses = len(GLOSS_INDEX)
    local_glosses = sum(
        1 for instances in GLOSS_INDEX.values()
        if any(inst["video_id"] in available_ids for inst in instances)
    )
    direct_glosses = sum(
        1 for instances in GLOSS_INDEX.values()
        if any(not inst["is_youtube"] for inst in instances)
    )
    return {
        "total_glosses": total_glosses,
        "local_glosses": local_glosses,
        "direct_link_glosses": direct_glosses,
        "downloaded_videos": len(available_ids),
    }
