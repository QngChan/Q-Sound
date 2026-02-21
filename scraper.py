import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

class MyInstantsScraper:
    BASE_URL = "https://www.myinstants.com"
    SEARCH_URL = "https://www.myinstants.com/search/?name="

    @staticmethod
    def search(query):
        search_query = urllib.parse.quote(query)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(f"{MyInstantsScraper.SEARCH_URL}{search_query}", headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Search failed with status code: {response.status_code}")
                return []
        except Exception as e:
            print(f"Request error: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        instants = soup.find_all('div', class_='instant')
        
        results = []
        for instant in instants:
            try:
                name_link = instant.find('a', class_='instant-link')
                if not name_link: continue
                name = name_link.text.strip()
                
                button = instant.find('button', class_='small-button')
                if not button: button = instant.find('button')
                
                if button:
                    onclick_attr = button.get('onclick', '')
                    match = re.search(r"play\('([^']+)'", onclick_attr)
                    if match:
                        mp3_path = match.group(1)
                        full_url = mp3_path if mp3_path.startswith('http') else f"{MyInstantsScraper.BASE_URL}{mp3_path}"
                        results.append({"name": name, "url": full_url})
            except Exception as e:
                print(f"Error parsing instant: {e}")
                continue
        return results

    @staticmethod
    def get_tr_trending(page=1):
        url = f"https://www.myinstants.com/en/index/tr/?page={page}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"TR trending fetch failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"Request error: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        instants = soup.find_all('div', class_='instant')
        
        results = []
        for instant in instants:
            try:
                name_link = instant.find('a', class_='instant-link')
                if not name_link: continue
                name = name_link.text.strip()
                
                button = instant.find('button', class_='small-button')
                if not button: button = instant.find('button')
                
                if button:
                    onclick_attr = button.get('onclick', '')
                    match = re.search(r"play\('([^']+)'", onclick_attr)
                    if match:
                        mp3_path = match.group(1)
                        full_url = mp3_path if mp3_path.startswith('http') else f"{MyInstantsScraper.BASE_URL}{mp3_path}"
                        results.append({"name": name, "url": full_url})
            except Exception as e:
                print(f"Error parsing instant: {e}")
                continue
        return results

if __name__ == "__main__":
    scraper = MyInstantsScraper()
    print("Fetching TR trending page 1...")
    tr_sounds = scraper.get_tr_trending(page=1)
    print(f"Found {len(tr_sounds)} sounds.")
    
    print("\nFetching TR trending page 2...")
    tr_sounds2 = scraper.get_tr_trending(page=2)
    print(f"Found {len(tr_sounds2)} sounds.")
    for s in tr_sounds2[:3]:
        print(f"{s['name']}: {s['url']}")
