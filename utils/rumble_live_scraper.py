import requests
from bs4 import BeautifulSoup

BASE_URL = "https://rumble.com"
LIVE_BROWSE_URL = f"{BASE_URL}/browse/live?page=4"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_live_video_links():
    response = requests.get(LIVE_BROWSE_URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ Failed to fetch live browse page: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/v") and len(href) > 10:
            full_url = BASE_URL + href.split("?")[0]
            links.add(full_url)

    return sorted(links)

if __name__ == "__main__":
    live_links = get_live_video_links()
    print(f"✅ Found {len(live_links)} live links:")
    for link in live_links:
        print(link)
