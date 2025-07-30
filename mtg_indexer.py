from scryfall_bulk_loader import main as run_bulk_loader
from index_cards import main as run_indexing
import time
import tqdm


def main():
    run_bulk_loader()
    run_indexing()

if __name__ == "__main__":
    start_time = time.time()

    main()

    end_time = time.time()
    elapsed = end_time - start_time
    hours, rem = divmod(elapsed, 3600)
    mins, secs = divmod(rem, 60)
    tqdm.write(f"⏱️ Total time: {int(hours)}h {int(mins)}m {secs:.2f}s")