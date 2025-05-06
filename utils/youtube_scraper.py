from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def scrape_youtube_links(start_url, max_links=50, headless=True, output_file="youtube_links.txt"):
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")  # Quiet mode

    driver = webdriver.Chrome(options=options)

    visited = set()
    to_visit = [start_url]

    while to_visit and len(visited) < max_links:
        url = to_visit.pop(0)
        if url in visited:
            continue

        try:
            driver.get(url)
            time.sleep(2)  # let page load

            links = driver.find_elements(By.XPATH, "//a[@href]")
            for link in links:
                href = link.get_attribute("href")
                if href and "youtube.com/watch?v=" in href:
                    if href not in visited and href not in to_visit:
                        to_visit.append(href)
        except Exception as e:
            print(f"Error loading {url}: {e}")

        visited.add(url)
        print(f"[{len(visited)}/{max_links}] Collected: {url}")

    driver.quit()

    # Save to file
    with open(output_file, "w") as f:
        for link in visited:
            f.write(link + "\n")
    print(f"\n✅ Saved {len(visited)} links to {output_file}")

    return list(visited)

if __name__ == "__main__":
    seed_url = "https://www.youtube.com/watch?v=n4OflWszcZ0"  # Replace this
    n_links = 25  # Number of unique links to collect

    scrape_youtube_links(seed_url, max_links=n_links)
