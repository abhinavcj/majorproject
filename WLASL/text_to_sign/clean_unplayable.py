import os
import subprocess
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos"
GLOSS_INDEX_PATH = BASE_DIR / "gloss_index.json"

def check_video(file_path):
    """Checks if a video file has actual frames using ffprobe."""
    if file_path.suffix == '.gif':
        # Simple size check for gifs, or just assume valid if size > 100 bytes
        return file_path.stat().st_size > 100
        
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-select_streams", "v:0", 
        "-count_frames", 
        "-show_entries", "stream=nb_read_frames", 
        "-of", "default=nokey=1:noprint_wrappers=1", 
        str(file_path)
    ]
    try:
        # Run ffprobe with a timeout
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5).decode().strip()
        if output and output.isdigit():
            frames = int(output)
            if frames > 0:
                return True
        return False
    except Exception as e:
        return False

print("Scanning videos directory for unplayable files...")
bad_files = []
for file_path in VIDEOS_DIR.iterdir():
    if file_path.is_file() and file_path.suffix in ['.mp4', '.gif']:
        # First check size
        if file_path.stat().st_size < 1000:
            bad_files.append(file_path)
        # Then check if it actually has frames
        elif not check_video(file_path):
            bad_files.append(file_path)

print(f"Found {len(bad_files)} bad files.")

for bf in bad_files:
    print(f"Deleting unplayable file: {bf.name}")
    bf.unlink()

print("Updating gloss_index to remove instances without a local video (to force fingerspelling)...")
with open(GLOSS_INDEX_PATH, 'r') as f:
    glosses = json.load(f)

# Also load alphabet ids to keep them
ALPHABET_IDS = set()
for c in 'abcdefghijklmnopqrstuvwxyz':
    ALPHABET_IDS.add(c)

new_glosses = {}
removed_count = 0
for gloss, instances in glosses.items():
    valid_instances = []
    for inst in instances:
        vid = inst['video_id']
        if vid in ALPHABET_IDS:
            valid_instances.append(inst)
            continue
            
        mp4_path = VIDEOS_DIR / f"{vid}.mp4"
        gif_path = VIDEOS_DIR / f"{vid}.gif"
        
        # Only keep the instance if we actually have the video file
        # (Since remote videos are failing due to proxies/CORS/404s)
        if mp4_path.exists() or gif_path.exists():
            valid_instances.append(inst)
        else:
            removed_count += 1
            
    if valid_instances:
        new_glosses[gloss] = valid_instances

print(f"Removed {removed_count} missing remote references from index.")
print(f"Glosses remaining with local videos: {len(new_glosses)} (was {len(glosses)})")

with open(GLOSS_INDEX_PATH, 'w') as f:
    json.dump(new_glosses, f, indent=2)

print("Done. Restart the backend to apply changes.")
