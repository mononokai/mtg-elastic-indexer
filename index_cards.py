import json
import os
from dotenv import load_dotenv
from glob import glob
from elasticsearch import Elasticsearch

# load the environment variables
load_dotenv()

client = Elasticsearch("http://localhost:9200", api_key=os.getenv("ELASTIC_KEY"))

filenames = glob("AllSetFiles/*.json")

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


def get_set_info(set_data):
    set_info = set_data.copy()
    set_info.pop("cards", None)
    set_info.pop("tokens", None)
    set_info.pop("booster", None)
    return set_info

# function for filtering out unnecessary fields
def filter_fields(data, fields_to_keep):
    # if the data is a dictionary
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

# function for indexing every card in a file
def index_set(filename, index_name):
    print(f"Indexing {filename}...")

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    # set info
    set_info = get_set_info(data["data"])

    # ingest cards
    for card in data["data"].get("cards", []):
        document = filter_fields(card, fields_to_keep)
        document["set_info"] = set_info
        client.index(index=index_name, document=document)

    # ingest tokens
    for token in data["data"].get("tokens", []):
        document = filter_fields(token, fields_to_keep)
        document["set_info"] = set_info
        client.index(index=index_name, document=document)


def main():
    filename = "AllSetFiles/AMH1.json"
    index_name = "mtg_cards"

    # ? Does this check really need to be here?
    # check if index exists
    if not client.indices.exists(index=index_name):
        # if not, create index
        print(f'Index does not exist, creating index "{index_name}"')
        client.indices.create(index=index_name)

    # iterate through files and ingest all of them
    for file in filenames:
        index_set(file, index_name)

    print("Done!")


if __name__ == "__main__":
    main()
