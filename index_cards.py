import json
import os
import requests
import zipfile
import shutil
from dotenv import load_dotenv
from glob import glob
from elasticsearch import Elasticsearch
from tqdm import tqdm

# Load the environment variables from .env file
load_dotenv()

# Connect to local Elasticsearch instance using API key authentication
client = Elasticsearch("http://localhost:9200", api_key=os.getenv("ELASTIC_KEY"))


# Specify which fields should be included from each card/token document
CARD_FIELDS_TO_KEEP = {
    "artist": None,
    "artistIds": None,
    "cardParts": None,
    "colorIdentity": None,
    "colors": None,
    "defense": None,
    "edhrecRank": None,
    "edhrecSaltiness": None,
    "flavorName": None,
    "flavorText": None,
    "frameEffects": None,
    "identifiers": {
        "scryfallId": None,
        "scryfallOracleId": None,
        "tcgplayerProductId": None,
        "tcgplayerEtchedProductId": None,
    },
    "isFullArt": None,
    "isPromo": None,
    "isRebalanced": None,
    "isReprint": None,
    "isReserved": None,
    "isStarter": None,
    "isStorySpotlight": None,
    "isTextless": None,
    "keywords": None,
    "layout": None,
    "leadershipSkills": {"brawl": None, "commander": None, "oathbreaker": None},
    "legalities": None,
    "life": None,
    "loyalty": None,
    "manaCost": None,
    "manaValue": None,
    "name": None,
    "number": None,
    "otherFaceIds": None,
    "originalPrintings": None,
    "power": None,
    "printings": None,
    "promoTypes": None,
    "purchaseUrls": None,
    "rarity": None,
    "rebalancedPrintings": None,
    "relatedCards": None,
    "releaseDate": None,
    "rulings": None,
    "securityStamp": None,
    "setCode": None,
    "subtypes": None,
    "supertypes": None,
    "text": None,
    "toughness": None,
    "type": None,
    "types": None,
    "uuid": None,
    "variations": None,
}


# Checks if the MTGJSON directory exists, prompts user if so to redownload and overwrite
# Downloads and extracts normally otherwise
def download_mtgjson_all_sets():
    MTGJSON_ZIP_URL = "https://mtgjson.com/api/v5/AllSetFiles.zip"
    MTGJSON_ZIP_FILENAME = "AllSetFiles.zip"
    MTGJSON_EXTRACT_DIR = "AllSetFiles"

    if os.path.exists("AllSetFiles"):
        while True:
            user_response = input(
                "❗ AllSetFiles directory already exists. Redownload and overwrite? (y/N):"
            )
            if user_response.lower() == "y":
                download_and_extract_zip(
                    MTGJSON_ZIP_URL, MTGJSON_ZIP_FILENAME, MTGJSON_EXTRACT_DIR
                )
                break
            elif user_response.lower() == "n":
                print("✅ Skipping download.")
                break
            else:
                print("⚠️ Please enter 'y' or 'n'.")
    else:
        download_and_extract_zip(
            MTGJSON_ZIP_URL, MTGJSON_ZIP_FILENAME, MTGJSON_EXTRACT_DIR
        )


# Downloads and extracts MTGJSON AllSetFiles.zip then cleans up afterwards
def download_and_extract_zip(url, zip_filename, extract_dir):
    tqdm.write("⬇️  Downloading AllSetFiles.zip from MTGJSON...")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(zip_filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    tqdm.write("✅ Download complete.")

    # Delete old folder if it exists
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)

    # Extract zip file
    with zipfile.ZipFile(zip_filename, "R") as zip_ref:
        zip_ref.extractall(extract_dir)
    tqdm.write(f"🗂️ Extracted to {extract_dir}/.")

    # Remove zip file
    os.remove(zip_filename)
    tqdm.write("🧹 Cleaned up zip file.")


# Grabs set-level info from the JSON file, removing card, token and booster data
def get_set_info(set_data):
    set_info = set_data.copy()
    set_info.pop("cards", None)
    set_info.pop("tokens", None)
    set_info.pop("booster", None)
    return set_info


# Recursively filter the data to keep only the fields defined in fields_to_keep
def filter_fields(data, fields_to_keep):
    if isinstance(data, dict):
        return {
            key: (
                filter_fields(value, fields_to_keep[key])
                if isinstance(fields_to_keep.get(key), dict)
                else value
            )
            for key, value in data.items()
            if key in fields_to_keep
        }
    elif isinstance(data, list):
        return [filter_fields(item, fields_to_keep) for item in data]
    else:
        return data


# Load pre-cached image URL file
def load_cache(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    else:
        tqdm.write("⚠️ No image cache file found!")
        return {}


# Ingest cards and tokens from a single file into ELasticsearch
def index_set(filename, index_name, image_cache):
    tqdm.write(f"📄 Indexing {filename}...")

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Grab metadata about the set
    set_info = get_set_info(data["data"])

    bulk_operations = []
    success_count = 0
    fail_count = 0

    cards = data["data"].get("cards", [])
    tokens = data["data"].get("tokens", [])
    # Index all card and token documents into Elasticsearch
    for doc_type, items in [("🃏 Cards", cards), ("🪙 Tokens", tokens)]:
        for item in tqdm(items, desc=f"  {doc_type}", leave=True, ncols=60):
            try:
                document = filter_fields(item, CARD_FIELDS_TO_KEEP)
                scryfall_id = document.get("identifiers", {}).get("scryfallId")
                if scryfall_id:
                    image_url = image_cache.get(scryfall_id)
                    if image_url:
                        document["imageUrl"] = image_url
                document["set_info"] = set_info
                bulk_operations.append({"index": {"_index": index_name}})
                bulk_operations.append(document)
                success_count += 1
            except Exception:
                fail_count += 1

    CHUNK_SIZE = 100  # Document amount
    PAIR_SIZE = CHUNK_SIZE * 2  # Ingest pairs an action with each document
    if bulk_operations:
        for i in range(0, len(bulk_operations), PAIR_SIZE):
            chunk = bulk_operations[i : i + PAIR_SIZE]
            response = client.bulk(operations=chunk, params={"require_alias": False})
            if response.get("errors"):
                for item in response["items"]:
                    index_result = item.get("index", {})
                    if "error" in index_result:
                        fail_count += 1
                        success_count -= 1
                        error_info = index_result["error"]
                        doc_id = index_result.get("_id", "<no_id>")
                        tqdm.write(
                            f"❌ Error indexing doc {doc_id}: {error_info.get('type')} - {error_info.get('reason')}"
                        )

    tqdm.write(f"✅ {filename}: {success_count} indexed, {fail_count} failed.")
    return success_count, fail_count


# Main entry point
def main():
    index_name = "mtg_cards"
    image_cache_name = "image_cache.json"
    image_cache = load_cache(image_cache_name)

    # Create index if it doesn't already exist
    if not client.indices.exists(index=index_name):
        tqdm.write(f'📦 Index "{index_name}" does not exist. Creating it...')
        client.indices.create(index=index_name)

    total_success = 0
    total_fail = 0

    # Index all files with progress tracking
    # Grab all JSON files in the "AllSetFiles" directory
    filenames = glob("AllSetFiles/*.json")  # All set files
    for file in tqdm(filenames, desc="📁 Processing set files"):
        success, fail = index_set(file, index_name, image_cache)
        total_success += success
        total_fail += fail

    tqdm.write(
        f"🎉 Ingestion complete! {total_success} documents indexed, {total_fail} failed."
    )


# Run the main function
if __name__ == "__main__":
    main()
