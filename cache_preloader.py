import json
import os
import requests
from glob import glob
from tqdm import tqdm

# Grab all JSON files in the "AllSetFiles" directory
filenames = glob("AllSetFiles/*.json")

# User-Agent string for Scryfall API calls
HEADERS = {
    "User-Agent": "MTG-Elastic-Indexer (contact: leachda12@proton.me)",
    "Accept": "application/json",
}


def cache_ids(filename):
    unique_ids = set()

    # Load set file
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    # Collect all unique Scryfall IDs from cards
    cards = data["data"].get("cards", [])
    if cards:
        for card in cards:
            identifiers = card.get("identifiers", {})
            scryfall_id = identifiers.get("scryfallId")
            if scryfall_id:
                unique_ids.add(scryfall_id)
    
    # Collect all unique Scryfall IDs from tokens
    tokens = data["data"].get("tokens", [])
    if tokens:
        for token in tokens:
            identifiers = token.get("identifiers", {})
            scryfall_id = identifiers.get("scryfallId")
            if scryfall_id:
                unique_ids.add(scryfall_id)
    
    return unique_ids


# Load existing cache if it exists
def load_existing_cache(filename):
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            return json.load(f)
    
    return {}


# Get image URL, cache if needed
def get_or_fetch_image_url(scryfallId, image_cache):
    if scryfallId not in image_cache:
        try:
            response = requests.get(
                f"https://api.scryfall.com/cards/{scryfallId}", headers=HEADERS
            )
            response.raise_for_status()
            data = response.json()
            image_cache[scryfallId] = data["image_uris"]["normal"]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image for {scryfallId}: {e}")
            return None

    return image_cache[scryfallId]


def main():
    image_cache_name = "image_cache.json"
    all_ids = set()
    image_cache = load_existing_cache(image_cache_name)
    tqdm.write(f"🔍 Loaded {len(image_cache)} pre-cached image URLs.")
    remaining_ids = []

    for id_ in all_ids:
        if id_ not in image_cache:
            remaining_ids.append(id_)
    tqdm.write(f"📦 {len(remaining_ids)} Scryfall IDs to fetch.")

    for file in filenames:
        tqdm.write(f"🔍 Processing file: {file}")
        set_ids = cache_ids(file)
        tqdm.write(f"f"📁 Found {len(set_ids)} unique IDs in {file}"")
        all_ids.update(set_ids)

    tqdm.write(f"📦 Total unique Scryfall IDs collected: {len(all_ids)}")

    for scryfall_id in tqdm(remaining_ids, desc="🌐 Fetching new image URLs"):
        image_url = get_or_fetch_image_url(scryfall_id, image_cache)

        if image_url is None:
            tqdm.write(f"⚠️ Failed to fetch image for ID: {scryfall_id}")
