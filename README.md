# MTG Elasticsearch Indexer
This script indexes Magic: The Gathering card and token data into a local Elasticsearch instance using the [MTGJSON](https://mtgjson.com) dataset. It uses `tqdm` to display progress and filters fields for efficient ingestion and searching.

---

## 📦 Features

- Parses and filters MTGJSON AllSetFiles data
- Indexes cards and tokens into Elasticsearch
- Attaches set metadata to each document
- Shows clean CLI progress bars using `tqdm`

---

## 🚀To Run

1. **Clone this repo**
   ```bash
   git clone https://github.com/mononokai/mtg-elastic-indexer.git
   cd mtg-elastic-indexer
   ```
2. **Download [AllSetFiles](https://mtgjson.com/downloads/all-files/) from MTGJSON**
    → Extract the contents into the root of this repo (where index_cards.py is)
3. **Start a local Elasticsearch instance**
    → ([Elastic Docs: Run Elasticsearch Locally](https://www.elastic.co/docs/solutions/search/run-elasticsearch-locally))
4. **If you don't have your Elasticsearch API key, create a new one**
    → ([Elastic Docs: Create an API Key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys#create-api-key))
5. **Create a `.env` file in the root directory which your API key:**
   ```env
   ELASTIC_KEY="your_api_key_here"
   ```
6. **Make sure you have Python 3.8+ installed**
7. **Install dependencies:** 
   ```bash
   pip install -r requirements.txt
   ```
8. **Run the indexer script:** 
   ```bash
   python index_cards.py
   ```
9.  Done! Your MTG cards should now be indexed into Elasticsearch under the default index name `mtg_cards`