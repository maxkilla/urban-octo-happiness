import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging
import re
from cache import load_cache, save_cache
import os

BASE_URLS = {
    "Myrient": {
        "No-Intro": "https://myrient.erista.me/files/No-Intro/",
        "Redump": "https://myrient.erista.me/files/Redump/",
        "Internet Archive": "https://myrient.erista.me/files/Internet Archive/",
        "Miscellaneous": "https://myrient.erista.me/files/Miscellaneous/",
        "TOSEC": "https://myrient.erista.me/files/TOSEC/",
        "TOSEC-ISO": "https://myrient.erista.me/files/TOSEC-ISO/",
        "TOSEC-PIX": "https://myrient.erista.me/files/TOSEC-PIX/"
    },
    "hShop": {
        # Add hShop collections here if needed
        "3DS": "https://hshop.erista.me/"
    }
}

session = requests.Session()
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_systems(source, collection):
    if source == "Myrient":
        return get_systems_myrient(collection)
    elif source == "hShop":
        return get_systems_hshop(collection)
    return []

def fetch_games(source, collection, system, system_display):
    if source == "Myrient":
        return fetch_games_myrient(collection, system, system_display)
    elif source == "hShop":
        return fetch_games_hshop(collection, system, system_display)
    return []

# --- Myrient Scraper ---
def get_systems_myrient(collection):
    logging.info(f"get_systems_myrient called for collection: {collection}")
    url = BASE_URLS["Myrient"].get(collection)
    logging.info(f"Requesting systems URL: {url}")
    if not url:
        return []
    cache_file = os.path.join(CACHE_DIR, f"myrient_systems_{collection}.json")
    cached = load_cache(cache_file)
    if cached:
        return cached
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        systems = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if href.endswith("/") and href != "../":
                system_name = href.rstrip("/")
                systems.append(system_name)
        logging.info(f"Found systems: {systems}")
        save_cache(cache_file, systems)
        return systems
    except Exception as e:
        logging.error(f"Error fetching systems: {e}")
        return []

def fetch_games_myrient(collection, system, system_display):
    logging.info(f"fetch_games_myrient called for collection: {collection}, system: {system}")
    if not collection or not system:
        return []
    base_url = BASE_URLS["Myrient"].get(collection)
    if not base_url:
        return []
    url = urllib.parse.urljoin(base_url, system + "/")
    logging.info(f"Requesting games URL: {url}")
    cache_file = os.path.join(CACHE_DIR, f"myrient_games_{collection}_{system}.json")
    cached = load_cache(cache_file)
    if cached:
        return cached
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        html_snippet = resp.text[:500]
        logging.info(f"HTML response snippet: {html_snippet}")
        soup = BeautifulSoup(resp.text, "html.parser")
        games = []
        for link in soup.find_all("a"):
            href = link.get("href", "")
            logging.info(f"Found link: text={link.text}, href={href}")
            name = link.text
            region = ""
            year = ""
            size = "?"
            tr = link.find_parent("tr")
            if tr:
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    size = tds[1].text.strip()
            if "(USA" in name:
                region = "USA"
            elif "(JAP" in name:
                region = "JAP"
            elif "(EUR" in name:
                region = "EUR"
            else:
                region = "Other"
            year_match = re.search(r'\((19|20)\\d{2}\)', name)
            if year_match:
                year = year_match.group(0).strip("()")
            games.append({
                "name": name,
                "size": size,
                "region": region,
                "year": year,
                "system": system_display,
                "url": urllib.parse.urljoin(url, href)
            })
        logging.info(f"Fetched {len(games)} links for {system}")
        save_cache(cache_file, games)
        return games
    except Exception as e:
        logging.error(f"Error fetching games: {e}")
        return []

# --- hShop Scraper ---
def get_systems_hshop(collection):
    """
    Scrape hShop navigation bar to get categories (systems).
    """
    url = BASE_URLS["hShop"]["3DS"]
    logging.info(f"get_systems_hshop: Requesting {url}")
    cache_file = os.path.join(CACHE_DIR, "hshop_systems.json")
    cached = load_cache(cache_file)
    if cached:
        return cached
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        nav_links = []
        # Find navigation bar links (categories)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            # Only include main categories (not external, not home, not donate, etc.)
            if href.startswith("/") and len(href) > 1 and not href.startswith("/wiki") and not href.startswith("/discord") and not href.startswith("/donate"):
                # Remove leading slash and query params/fragments
                cat = href.split("?")[0].split("#")[0].lstrip("/")
                # Filter out home and extras
                if cat.lower() not in ["", "home", "extras", "themes", "videos"] and cat not in nav_links:
                    nav_links.append(cat)
        logging.info(f"hShop categories found: {nav_links}")
        save_cache(cache_file, nav_links)
        return nav_links
    except Exception as e:
        logging.error(f"Error fetching hShop systems: {e}")
        return ["games"]  # fallback

def fetch_games_hshop(collection, system, system_display):
    """
    Scrape hShop category page and extract game info.
    """
    base_url = BASE_URLS["hShop"]["3DS"]
    cat_url = urllib.parse.urljoin(base_url, system)
    logging.info(f"fetch_games_hshop: Requesting {cat_url}")
    cache_file = os.path.join(CACHE_DIR, f"hshop_games_{system}.json")
    cached = load_cache(cache_file)
    if cached:
        return cached
    try:
        resp = requests.get(cat_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        games = []
        # hShop uses cards or table rows for games
        # Try to find all game cards
        for card in soup.find_all("div", class_="card"):
            name = card.find("h5")
            name = name.get_text(strip=True) if name else "Unknown"
            region = "USA"  # hShop may not show region on main page
            size = "?"
            year = "?"
            # Try to extract more info from card body
            body = card.find("div", class_="card-body")
            if body:
                text = body.get_text(" ", strip=True)
                # Try to extract size and year from text
                size_match = re.search(r"Size: ([^\s]+)", text)
                if size_match:
                    size = size_match.group(1)
                year_match = re.search(r"(19|20)\d{2}", text)
                if year_match:
                    year = year_match.group(0)
            # Find download link (if available)
            download_url = None
            for a in card.find_all("a", href=True):
                if "download" in a.get_text(strip=True).lower():
                    download_url = urllib.parse.urljoin(cat_url, a["href"])
                    break
            games.append({
                "name": name,
                "size": size,
                "region": region,
                "year": year,
                "system": system_display,
                "url": download_url or cat_url
            })
        # Fallback: try table rows if no cards found
        if not games:
            for row in soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 2:
                    name = cols[0].get_text(strip=True)
                    size = cols[1].get_text(strip=True)
                    region = "USA"
                    year = "?"
                    games.append({
                        "name": name,
                        "size": size,
                        "region": region,
                        "year": year,
                        "system": system_display,
                        "url": cat_url
                    })
        logging.info(f"hShop: Fetched {len(games)} games for {system}")
        save_cache(cache_file, games)
        return games
    except Exception as e:
        logging.error(f"Error fetching hShop games: {e}")
        return [] 