"""Rebuild shared data; requires course CSV files and all referenced images."""
import _bootstrap
from cat_arena.data_preparation.prepare import main

if __name__ == '__main__':
    main()
