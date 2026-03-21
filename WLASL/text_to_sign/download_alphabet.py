import json
import os
import urllib.request
import time

GLOSS_INDEX_PATH = 'gloss_index.json'
VIDEOS_DIR = 'videos'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

ALPHABET = "abcdefghijklmnopqrstuvwxyz"

def try_download(url, saveto):
    headers = {'User-Agent': UA}
    if 'aslpro' in url:
        headers['Referer'] = 'http://www.aslpro.com/cgi-bin/aslpro/aslpro.cgi'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        if len(data) < 500: return False
        with open(saveto, 'wb') as f:
            f.write(data)
        return True
    except:
        return False

def main():
    if not os.path.exists(GLOSS_INDEX_PATH):
        print("Error: gloss_index.json not found")
        return
    
    with open(GLOSS_INDEX_PATH) as f:
        index = json.load(f)
    
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    print("Checking alphabet videos...")
    missing = []
    for char in ALPHABET:
        # Check if we have any video for this letter in our index
        instances = index.get(char, [])
        found_local = False
        for inst in instances:
            vid = inst['video_id']
            if os.path.exists(os.path.join(VIDEOS_DIR, f"{vid}.mp4")):
                found_local = True
                break
        
        if not found_local:
            print(f"  Letter '{char}' missing locally. Trying to download...")
            success = False
            for inst in instances:
                if inst['is_youtube']: continue
                vid = inst['video_id']
                url = inst['url']
                saveto = os.path.join(VIDEOS_DIR, f"{vid}.mp4")
                if try_download(url, saveto):
                    print(f"    → Got '{char}' ({vid})")
                    success = True
                    break
                time.sleep(0.5)
            
            if not success:
                # Last resort: try Handspeak common URL format for alphabet
                # Example: https://www.handspeak.com/word/a/a-abc.mp4
                url = f"https://www.handspeak.com/word/{char}/{char}-abc.mp4"
                saveto = os.path.join(VIDEOS_DIR, f"letter_{char}.mp4")
                if try_download(url, saveto):
                    print(f"    → Got '{char}' from Handspeak ABC")
                    # We should probably add this to indices as well, but for now just having the file is good
                else:
                    print(f"    → FAILED letters '{char}' completely")
                    missing.append(char)
        else:
            print(f"  Letter '{char}' already exists.")

    if missing:
        print(f"\nRemaining missing letters: {', '.join(missing)}")
    else:
        print("\nAll 26 alphabet letters are now available locally!")

if __name__ == "__main__":
    main()
