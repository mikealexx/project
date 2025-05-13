import os
import json

# Path to Preferences file (adjust for Chromium or other profile paths if needed)
prefs_path = os.path.expanduser("~/.config/google-chrome/Default/Preferences")

# Backup first
backup_path = prefs_path + ".bak"
if not os.path.exists(backup_path):
    with open(prefs_path, "r") as original, open(backup_path, "w") as backup:
        backup.write(original.read())
    print(f"✅ Backup created at {backup_path}")

# Load the Preferences file as raw text (to replace even nested incognito:false safely)
with open(prefs_path, "r", encoding="utf-8") as f:
    prefs_text = f.read()

# Replace all exact matches of "incognito": false with "incognito": true
updated_text = prefs_text.replace('"incognito":false', '"incognito":true')

# Save the updated Preferences
with open(prefs_path, "w", encoding="utf-8") as f:
    f.write(updated_text)

print(f"✅ Updated {prefs_path} to enable all extensions in incognito mode.")
