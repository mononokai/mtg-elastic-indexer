# MTG Elasticsearch Indexer
This script indexes Magic: The Gathering card and token data into a local Elasticsearch instance using the [MTGJSON](https://mtgjson.com) dataset and image URLs from [Scryfall](https://scryfall.com). It uses `tqdm` to display progress, filters fields for efficient ingestion and searching, and uses the Scryfall bulk data API for fast, reliable image caching.

---

## 📦 Features

- Downloads and parses Scryfall's bulk `default_cards` data
- Caches card image URLs for faster indexing
- Downloads and extracts MTGJSON AllSetFiles data
- Parses and filters MTGJSON AllSetFiles data
- Attaches set metadata to each document
- Indexes cards and tokens into Elasticsearch
- Shows clean CLI progress bars using `tqdm`

---

## 🚀To Run

1. **Clone this repo**
   ```bash
   git clone https://github.com/mononokai/mtg-elastic-indexer.git
   cd mtg-elastic-indexer
   ```
2. **Start a local Elasticsearch instance**
    → ([Elastic Docs: Run Elasticsearch Locally](https://www.elastic.co/docs/solutions/search/run-elasticsearch-locally))
3. **If you don't have your Elasticsearch API key, create a new one**
    → ([Elastic Docs: Create an API Key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys#create-api-key))
4. **Create a `.env` file in the root directory and store your API key:**
   ```env
   ELASTIC_KEY="your_api_key_here"
   ```
5. **Add your email to the `.env` file as well for the Scryfall API call:**
   ```env
   USER_EMAIL="your_email_here"
   ```
6. **Make sure you have Python 3.8+ installed**
7. **Install dependencies:** 
   ```bash
   pip install -r requirements.txt
   ```
8. **Run the indexer script:** 
   ```bash
   python mtg_indexer.py
   ```
9.  Done! Your MTG cards should now be indexed into Elasticsearch under the default index name `mtg_cards`