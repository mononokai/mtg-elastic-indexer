import json
import os
import aiohttp
import asyncio
from glob import glob
from tqdm import tqdm
from datetime import datetime

# User-Agent string for Scryfall API calls (per their API etiquette guidelines)
HEADERS = {
    "User-Agent": "MTG-Elastic-Indexer (contact: leachda12@proton.me)",
    "Accept": "application/json",
}


# Collect all unique Scryfall IDs from an MTGJSON set file
def cache_ids(filename):
    unique_ids = set()

    # Load set file
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Collect all unique Scryfall IDs from cards and tokens
    for card_type in ("cards", "tokens"):
        for item in data["data"].get(card_type, []):
            scryfall_id = item.get("identifiers", {}).get("scryfallId")
            if scryfall_id:
                unique_ids.add(scryfall_id)

    return unique_ids


# Load existing image URL cache if it exists
def load_existing_cache(filename):
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            return json.load(f)

    return {}


# Write image URL cache to file
def save_cache(image_cache_filename, image_cache):
    with open(image_cache_filename, "w") as f:
        json.dump(image_cache, f, indent=2)
        tqdm.write("💾 Image cache saved.")


# Asynchronously fetch the image URL for a Scryfall ID with rate limiting
async def fetch_image_url(scryfall_id, session, semaphore):
    async with semaphore:
        try:
            url = f"https://api.scryfall.com/cards/{scryfall_id}"

            async with session.get(url, headers=HEADERS) as response:
                response.raise_for_status()
                data = await response.json()

                # Handle single-faced vs double-faced cards
                if "image_uris" in data:
                    image_url = data["image_uris"]["normal"]
                elif "card_faces" in data and isinstance(data["card_faces"], list):
                    front_face = data["card_faces"][0]
                    if "image_uris" in front_face:
                        image_url = front_face["image_uris"]["normal"]
                    else:
                        msg = f"No image_uris in card_faces for ID: {scryfall_id}"
                        tqdm.write(f"❌ {msg}")
                        with open("missing_image_uris.log", "a") as log_file:
                            log_file.write(f"[{datetime.now().isoformat()}] {msg}\n")
                        return (scryfall_id, None)
                else:
                    msg = f"No image_uris found for ID: {scryfall_id}"
                    tqdm.write(f"❌ {msg}")
                    with open("missing_image_uris.log", "a") as log_file:
                        log_file.write(f"[{datetime.now().isoformat()}] {msg}\n")
                    return (scryfall_id, None)

                return (scryfall_id, image_url)
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                tqdm.write(f"🚫 Rate limit hit for {scryfall_id}. Backing off.")
                await asyncio.sleep(5)  # Crude backoff
            else:
                msg = f"{e.status} {e.request_info.method} {e.request_info.url} — {scryfall_id}"
                tqdm.write(f"⚠️ {msg}")
                with open("fetch_errors.log", "a") as log_file:
                    log_file.write(f"[{datetime.now().isoformat()}] {msg}\n")

        return (scryfall_id, None)


# Retry failed Scryfall image fetches once and log any that still fail
async def retry_failed_fetches(failed_ids, image_cache, session, semaphore):
    if not failed_ids:
        return

    await asyncio.sleep(2) # Brief pause before retry

    retry_tasks = []
    for scryfall_id in failed_ids:
        task = fetch_image_url(scryfall_id, session, semaphore)
        retry_tasks.append(task)
    
    for completed_retry in tqdm(
        asyncio.as_completed(retry_tasks),
        total=len(retry_tasks),
        desc=f"🔁 Retrying {len(failed_ids)} failed requests...",
        leave=True,
        ncols=80
    ):
        scryfall_id, retry_url = await completed_retry
        if retry_url:
            image_cache[scryfall_id] = retry_url
        else:
            tqdm.write(f"❌ Still failed after retry: {scryfall_id}")
    
    with open("permanent_failures.log", "a") as f:
        for scryfall_id in failed_ids:
            if scryfall_id not in image_cache:
                f.write(scryfall_id + "\n")


# Asynchronously fetch all missing image URLs and update the cache
async def fetch_all_images(remaining_ids, image_cache, image_cache_name):
    # Clear log files
    open("fetch_errors.log", "w").close()
    open("missing_image_uris.log", "w").close()
    open("permanent_failures.log", "w").close()

    # Limit concurrency and request timeout
    connector = aiohttp.TCPConnector(limit=5)
    timeout = aiohttp.ClientTimeout(total=60)
    semaphore = asyncio.Semaphore(1)  # Allow only 1 request at a time to avoid 429s

    tasks = []
    failed_ids = []
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for scryfall_id in tqdm(
            remaining_ids, desc="🌐 Fetching new image URLs", leave=True, ncols=80
        ):
            task = fetch_image_url(scryfall_id, session, semaphore)
            tasks.append(task)

        for i, completed_task in enumerate(
            tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc="📡 Processing API calls",
                leave=True,
                ncols=80,
            ),
            1,
        ):
            scryfall_id, image_url = await completed_task

            if image_url:
                image_cache[scryfall_id] = image_url
            else:
                failed_ids.append(scryfall_id)

            await asyncio.sleep(0.11)  # Keep requests under 10/sec (Scryfall's limit)

            if i % 100 == 0 and i != 0:
                save_cache(image_cache_name, image_cache)
        
        
        await retry_failed_fetches(failed_ids, image_cache, session, semaphore)


def main():
    image_cache_name = "image_cache.json"
    all_ids = set()
    image_cache = load_existing_cache(image_cache_name)
    tqdm.write(f"💾 Loaded {len(image_cache)} pre-cached image URLs.")

    # Collect unique Scryfall IDs from all sets
    filenames = glob("AllSetFiles/*.json")  # All set files
    for file in tqdm(filenames, desc="🔍 Scanning set files", leave=True, ncols=90):
        set_ids = cache_ids(file)
        all_ids.update(set_ids)
    tqdm.write(f"📦 Total unique Scryfall IDs collected: {len(all_ids)}")

    # Filter out IDs with images already cached
    remaining_ids = []
    for id_ in all_ids:
        if id_ not in image_cache:
            remaining_ids.append(id_)
    tqdm.write(f"📦 {len(remaining_ids)} Scryfall IDs to fetch.")

    asyncio.run(fetch_all_images(remaining_ids, image_cache, image_cache_name))

    # Final save
    save_cache(image_cache_name, image_cache)
    tqdm.write("🎉 Finished caching image URLs.")


# Run the main function
if __name__ == "__main__":
    main()
