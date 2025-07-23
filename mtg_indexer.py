from cache_preloader import main as run_cache_preloader
from index_cards import main as run_indexing


def main():
    run_cache_preloader()
    run_indexing()

if __name__ == "__main__":
    main()