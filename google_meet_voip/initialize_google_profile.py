import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def create_profile(profile_dir):
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--disable-blink-features=AutomationControlled")


    print(f"[INFO] Launching Chrome with profile: {profile_dir}")
    driver = webdriver.Chrome(options=options)

    driver.get("https://meet.google.com")
    print("[INFO] Please log in to your Google account manually...")
    print("[INFO] Press Ctrl+C when you're done to close the browser and save the profile.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Closing Chrome and saving profile.")
        driver.quit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python initialize_google_profile.py /path/to/profile_dir")
        sys.exit(1)

    create_profile(sys.argv[1])
