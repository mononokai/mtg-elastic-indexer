import requests
import json
import os
from tqdm import tqdm
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
USER_EMAIL = os.getenv("USER_EMAIL")
if USER_EMAIL is None:
    raise ValueError("USER_EMAIL is not set in the .env file.")


BULK_LIST_URL = "https://api.scryfall.com/bulk-data"
LOCAL_FILENAME = "scryfall_bulk.json"
# User-Agent string for Scryfall API calls (per their API etiquette guidelines)
HEADERS = {
    "User-Agent": f"MTG-Elastic-Indexer (contact: {USER_EMAIL})",
    "Accept": "application/json",
}


# Retrieves the download URL for the "default_cards" bulk data file from Scryfall
def fetch_default_cards_url():
    response = requests.get(url=BULK_LIST_URL, headers=HEADERS)
    data = response.json()
    bulk_data_types = data["data"]

    tqdm.write("🌐 Fetching bulk data metadata from Scryfall...")
    for item in bulk_data_types:
        if item["type"] == "default_cards":
            return item["download_uri"]


# Downloads the Scryfall bulk data JSON file and saves it
def download_bulk_data(download_url):
    response = requests.get(url=download_url, headers=HEADERS, stream=True)
    response.raise_for_status()

    tqdm.write("⬇️ Downloading bulk card data...")
    with open("scryfall_bulk.json", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    tqdm.write(f"📁 Bulk data saved to {LOCAL_FILENAME}")


# Parses the bulk JSON file and extracts image URLs for all valid cards
def build_image_cache():
    image_cache = {}

    with open("scryfall_bulk.json", "r", encoding="utf-8") as f:
        cards = json.load(f)
    
    for card in tqdm(cards, desc="🧱 Building image cache", leave=True, ncols=80):
        scryfall_id = card["id"]
        if card.get("layout") == "art_series": # Skip art cards
            continue
        if "image_uris" in card:
            image_url = card["image_uris"]["normal"]
        # Fallback to front face image from double-faced cards
        elif "card_faces" in card and isinstance(card["card_faces"], list):
            front_face = card["card_faces"][0]
            if "image_uris" in front_face:
                image_url = front_face["image_uris"]["normal"]
            else:
                tqdm.write(f"⚠️ Layout: {card.get('layout')}, Name: {card.get('name')}")
                tqdm.write(json.dumps(front_face, indent=2))
                msg = f"No image_uris in card_faces for ID: {scryfall_id}"
                tqdm.write(f"❌ {msg}")
                with open("missing_image_uris.log", "a") as log_file:
                    log_file.write(f"[{datetime.now().isoformat()}] {msg}\n")
                continue
        else:
            msg = f"No image_uris found for ID: {scryfall_id}"
            tqdm.write(f"❌ {msg}")
            with open("missing_image_uris.log", "a") as log_file:
                log_file.write(f"[{datetime.now().isoformat()}] {msg}\n")
            continue
        
        image_cache[scryfall_id] = image_url
    
    return image_cache


def main():
    default_cards_url = fetch_default_cards_url()
    download_bulk_data(default_cards_url)

    image_cache = build_image_cache()

    with open("image_cache.json", "w", encoding="utf-8") as f:
        json.dump(image_cache, f, indent=2)
        tqdm.write("💾 Image cache saved.")


if __name__ == "__main__":
    main()