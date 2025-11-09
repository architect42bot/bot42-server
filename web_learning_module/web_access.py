
import requests
from bs4 import BeautifulSoup
from reflection import generate_reflection
from memory import save_memory

def fetch_page_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()
    except Exception as e:
        return f"[ERROR] Failed to fetch content: {e}"

def learn_from_url(url):
    print(f"🌐 Fetching and learning from: {url}")
    page_text = fetch_page_text(url)
    if "[ERROR]" in page_text:
        return page_text
    reflection = generate_reflection(page_text[:3000])  # Truncate to avoid overload
    save_memory("learned_from_web", page_text[:2000])
    return reflection

def search_and_learn(query):
    print(f"🔍 Web search not implemented yet, but placeholder for: '{query}'")
    # Future implementation using real API (e.g. SerpAPI, DuckDuckGo)
    return f"[MOCK SEARCH] Would search for: {query}"
