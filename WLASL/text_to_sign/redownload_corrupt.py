"""Re-download corrupt/missing videos by fetching from direct URLs."""
import json, os, urllib.request, time
from pathlib import Path

BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos"
GLOSS_INDEX_PATH = BASE_DIR / "gloss_index.json"

# IDs that were deleted (corrupt files)
CORRUPT_IDS = {
    "00639","02003","05644","08929","09869","10166",
    "13337","17097","22130","24660","25339","27221",
    "28125","30849","31767","32337","33285","34746",
    "36946","42977","56852","57647","62175","63242",
    "63679","63806"
}

with open(GLOSS_INDEX_PATH) as f:
    gloss_index = json.load(f)

# Build a mapping from video_id => url
id_to_url = {}
for gloss, instances in gloss_index.items():
    for inst in instances:
        vid = inst["video_id"]
        if vid in CORRUPT_IDS and not inst["is_youtube"] and inst.get("url"):
            id_to_url[vid] = inst["url"]

print(f"Found {len(id_to_url)} URLs to re-download")

headers = {"User-Agent": "Mozilla/5.0"}
for vid, url in id_to_url.items():
    dest = VIDEOS_DIR / f"{vid}.mp4"
    print(f"Downloading {vid} from {url[:60]}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp, open(dest, "wb") as f:
            data = resp.read()
        # Validate
        if len(data) > 1000 and data[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide"):
            print(f"  ✓ Saved {len(data)//1024}KB")
        else:
            dest.unlink(missing_ok=True)
            print(f"  ✗ Invalid file, skipped")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
    time.sleep(0.2)

print("Done!")
