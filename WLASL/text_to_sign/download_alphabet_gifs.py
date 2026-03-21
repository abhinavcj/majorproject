import urllib.request
import os
import time

VIDEOS_DIR = 'videos'
ALPHABET = "abcdefghijklmnopqrstuvwxyz"
BASE_URL = "https://www.lifeprint.com/asl101/fingerspelling/abc-gifs/"

def main():
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    print("Downloading Lifeprint ASL alphabet GIFs...")
    
    for char in ALPHABET:
        url = f"{BASE_URL}{char}.gif"
        saveto = os.path.join(VIDEOS_DIR, f"letter_{char}.gif")
        
        if os.path.exists(saveto):
            print(f"  Letter '{char}' already exists.")
            continue
            
        print(f"  Downloading '{char}'...", end=' ', flush=True)
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            with open(saveto, 'wb') as f:
                f.write(data)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
