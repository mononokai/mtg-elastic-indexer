import json
import os
from dotenv import load_dotenv
from glob import glob
from elasticsearch import Elasticsearch

# Load the environment variables from .env file
load_dotenv()

# Connect to local Elasticsearch instance using API key authentication
client = Elasticsearch("http://localhost:9200", api_key=os.getenv("ELASTIC_KEY"))

# Grab all JSON files in the "AllSetFiles" directory
filenames = glob("AllSetFiles/*.json")

# Specify which fields should be included from each card/token document
fields_to_keep = {
    "borderColor": None,
    "cardParts": None,
    "colorIdentity": None,
    "colors": None,
    "convertedManaCost": None,
    "defense": None,
    "flavorName": None,
    "flavorText": None,
    "identifiers": {
        "scryfallId": None,
        "scryfallIllustrationId": None,
        "tcgplayerProductId": None,
    },
    "keywords": None,
    "leadershipSkills": {"brawl": None, "commander": None, "oathbreaker": None},
    "legalities": None,
    "life": None,
    "loyalty": None,
    "manaCost": None,
    "name": None,
    "number": None,
    "otherFaceIds": None,
    "power": None,
    "rarity": None,
    "releaseDate": None,
    "setCode": None,
    "subtypes": None,
    "supertypes": None,
    "text": None,
    "toughness": None,
    "type": None,
    "types": None,
    "uuid": None,
}

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

# Ingest cards and tokens from a single file into ELasticsearch
def index_set(filename, index_name):
    print(f"Indexing {filename}...")

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Grab metadata about the set
    set_info = get_set_info(data["data"])

    # Index each card document into Elasticsearch
    for card in data["data"].get("cards", []):
        document = filter_fields(card, fields_to_keep)
        document["set_info"] = set_info
        client.index(index=index_name, document=document)

    # Index each token document into Elasticsearch
    for token in data["data"].get("tokens", []):
        document = filter_fields(token, fields_to_keep)
        document["set_info"] = set_info
        client.index(index=index_name, document=document)


# Main entry point
def main():
    filename = "AllSetFiles/AMH1.json"
    index_name = "mtg_cards"

    # Create index if it doesn't already exist
    if not client.indices.exists(index=index_name):
        print(f'Index does not exist, creating index "{index_name}"')
        client.indices.create(index=index_name)

    # Process and index every set file found
    for file in filenames:
        index_set(file, index_name)

    print("Done!")


# Run the main function
if __name__ == "__main__":
    main()
