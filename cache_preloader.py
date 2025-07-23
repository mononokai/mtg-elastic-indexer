import json
import os
import requests
import aiohttp
import asyncio
from glob import glob
from tqdm import tqdm

# Grab all JSON files in the "AllSetFiles" directory
filenames = glob("AllSetFiles/*.json")

# User-Agent string for Scryfall API calls
HEADERS = {
    "User-Agent": "MTG-Elastic-Indexer (contact: leachda12@proton.me)",
    "Accept": "application/json",
}


# Collect all unique Scryfall IDs from a file
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
def get_or_fetch_image_url(scryfall_id, image_cache):
    if scryfall_id not in image_cache:
        try:
            response = requests.get(
                f"https://api.scryfall.com/cards/{scryfall_id}", headers=HEADERS
            )
            response.raise_for_status()
            data = response.json()

            if "image_uris" in data:
                image_cache[scryfall_id] = data["image_uris"]["normal"]
            elif "card_faces" in data and isinstance(data["card_faces"], list):
                front_face = data["card_faces"][0]
                if "image_uris" in front_face:
                    image_cache[scryfall_id] = front_face["image_uris"]["normal"]
                else:
                    tqdm.write(f"❌ No image_uris in card_faces for ID: {scryfall_id}")
                    return None
            else:
                tqdm.write(f"❌ No image_uris found for ID: {scryfall_id}")
                return None

        except requests.exceptions.RequestException as e:
            tqdm.write(f"⚠️ Error fetching image for {scryfall_id}: {e}")
            return None

    return image_cache[scryfall_id]


# Write image URL cache to file
def save_cache(image_cache_filename, cache_dict):
    with open(image_cache_filename, "w") as f:
        json.dump(cache_dict, f, indent=2)
        tqdm.write("💾 Image cache saved.")


def main():
    image_cache_name = "image_cache.json"
    all_ids = set()
    image_cache = load_existing_cache(image_cache_name)
    tqdm.write(f"🔍 Loaded {len(image_cache)} pre-cached image URLs.")
    remaining_ids = []

    # Collect unique Scryfall IDs from all sets
    for file in tqdm(filenames, desc="Scanning set files", leave=True, ncols=80):
        set_ids = cache_ids(file)
        all_ids.update(set_ids)
    tqdm.write(f"📦 Total unique Scryfall IDs collected: {len(all_ids)}")

    # Filter out IDs with images already cached
    for id_ in all_ids:
        if id_ not in image_cache:
            remaining_ids.append(id_)
    tqdm.write(f"📦 {len(remaining_ids)} Scryfall IDs to fetch.")

    # Fetch image URLs for the remaining IDs
    for i, scryfall_id in enumerate(
        tqdm(remaining_ids, desc="🌐 Fetching new image URLs")
    ):
        image_url = get_or_fetch_image_url(scryfall_id, image_cache)

        if image_url is None:
            tqdm.write(f"⚠️ Failed to fetch image for ID: {scryfall_id}")

        if i % 100 == 0 and i != 0:
            save_cache(image_cache_name, image_cache)

    # Final save
    save_cache(image_cache_name, image_cache)
    tqdm.write("🎉 Finished caching image URLs.")


# Run the main function
if __name__ == "__main__":
    main()
