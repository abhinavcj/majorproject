"""
build_gloss_index.py
Parses WLASL_v0.3.json and creates a fast gloss_index.json for the Text-to-Sign app.
Each gloss maps to a prioritised list of video instances.
"""

import json
import os

JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'start_kit', 'WLASL_v0.3.json')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'gloss_index.json')

# Source priority: prefer direct-download sources first (no yt-dlp needed)
DIRECT_SOURCES = {'aslbricks', 'aslsignbank', 'handspeak', 'signingsavvy',
                  'startasl', 'asldeafined', 'aslsearch', 'signschool', 'asllex'}

def source_priority(inst):
    """Lower = better. Direct sources first, then YouTube."""
    source = inst.get('source', '')
    if source in DIRECT_SOURCES:
        return 0
    elif 'youtube' in inst.get('url', '') or 'youtu.be' in inst.get('url', ''):
        return 1
    else:
        return 2


def is_youtube(url):
    return 'youtube.com' in url or 'youtu.be' in url


def build_index():
    print(f"Loading {JSON_PATH}...")
    with open(JSON_PATH) as f:
        data = json.load(f)

    index = {}

    for entry in data:
        gloss = entry['gloss'].lower().strip()
        instances = entry['instances']

        # Sort: direct-download sources first, then YouTube
        sorted_instances = sorted(instances, key=source_priority)

        processed = []
        for inst in sorted_instances:
            processed.append({
                'video_id': inst['video_id'],
                'url': inst['url'],
                'source': inst.get('source', ''),
                'frame_start': inst.get('frame_start', 1),
                'frame_end': inst.get('frame_end', -1),
                'split': inst.get('split', 'train'),
                'is_youtube': is_youtube(inst.get('url', '')),
            })

        index[gloss] = processed

    print(f"Indexed {len(index)} glosses.")

    with open(OUTPUT_PATH, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"Saved → {OUTPUT_PATH}")

    # Print stats
    direct_count = sum(
        1 for instances in index.values()
        if any(not inst['is_youtube'] for inst in instances)
    )
    print(f"  Glosses with at least one direct-download video: {direct_count}/{len(index)}")


if __name__ == '__main__':
    build_index()
