import pygetwindow as gw
from fuzzywuzzy import process

def check_windows():
    print("--- RAW WINDOW LIST ---")
    windows = gw.getAllWindows()
    titles = [w.title for w in windows if w.title.strip()]
    
    for t in titles:
        print(f"Title: '{t}'")
        
    print("\n--- TEST MATCHING ---")
    target = "antigravity"
    print(f"Searching for: '{target}'")
    
    # Fuzzy match logic clone
    match_title, match_score = process.extractOne(target, titles)
    print(f"Best Fuzzy Match: '{match_title}' (Score: {match_score})")
    
    # Substring logic clone
    for t in titles:
        if target.lower() in t.lower():
            print(f"Substring Match Found: '{t}'")

if __name__ == "__main__":
    check_windows()
