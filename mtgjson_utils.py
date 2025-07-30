import os
import shutil
import requests
import zipfile
from tqdm import tqdm


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


def download_mtgjson_all_sets():
    """
    Checks if the MTGJSON directory exists.
    If so, prompts the user to redownload and overwrite.
    If not, continues to download and extract the zip file as normal.
    """
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