"""
download_starter_videos.py
Downloads non-YouTube sign videos for the top N glosses (default: all available direct links).
Run this after build_gloss_index.py.
Usage:
    python download_starter_videos.py          # downloads top 100 glosses
    python download_starter_videos.py --all    # downloads all direct-link videos
"""

import json
import os
import sys
import time
import random
import urllib.request
import argparse

GLOSS_INDEX_PATH = os.path.join(os.path.dirname(__file__), 'gloss_index.json')
VIDEOS_DIR = os.path.join(os.path.dirname(__file__), 'videos')

USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/120.0.0.0 Safari/537.36')


def download_video(url, saveto, referer=''):
    headers = {'User-Agent': USER_AGENT}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(saveto, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        return False


def get_referer(url):
    if 'aslpro' in url:
        return 'http://www.aslpro.com/cgi-bin/aslpro/aslpro.cgi'
    return ''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='Download all direct-link videos')
    parser.add_argument('--top', type=int, default=100, help='Download top N glosses (default: 100)')
    args = parser.parse_args()

    os.makedirs(VIDEOS_DIR, exist_ok=True)

    with open(GLOSS_INDEX_PATH) as f:
        index = json.load(f)

    glosses = list(index.keys())
    if not args.all:
        glosses = glosses[:args.top]

    print(f"Downloading direct-link videos for {len(glosses)} glosses...")

    total = 0
    downloaded = 0
    skipped = 0
    failed = 0

    for i, gloss in enumerate(glosses):
        instances = index[gloss]
        
        # Check if we already have any video for this gloss
        already_have = False
        for inst in instances:
            if not inst['is_youtube'] and os.path.exists(os.path.join(VIDEOS_DIR, f"{inst['video_id']}.mp4")):
                already_have = True
                break
        
        if already_have:
            skipped += 1
            print(f"[{i+1}/{len(glosses)}] {gloss} ... ✓ (already have)", flush=True)
            continue

        # Try downloading each non-YouTube instance until one works
        success = False
        for inst in instances:
            if inst['is_youtube']:
                continue

            video_id = inst['video_id']
            url = inst['url']
            saveto = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")

            total += 1
            referer = get_referer(url)
            print(f"[{i+1}/{len(glosses)}] {gloss} → {video_id}", end=' ... ', flush=True)
            
            ok = download_video(url, saveto, referer)
            if ok:
                # Check if it was a small/error file
                if os.path.exists(saveto) and os.path.getsize(saveto) < 1000:
                    os.remove(saveto)
                    print("✗ (file too small)")
                else:
                    print("✓")
                    downloaded += 1
                    success = True
                    time.sleep(random.uniform(0.3, 0.8))
                    break
            else:
                print("✗ (failed)")
                if os.path.exists(saveto):
                    os.remove(saveto)
            
            time.sleep(0.3) # Short cooldown between source attempts

        if not success:
            failed += 1

    print(f"\nDone! Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")
    print(f"Videos saved in: {VIDEOS_DIR}")


if __name__ == '__main__':
    main()
