#!/usr/bin/env python3
"""Launcher for the GitMaze GUI frontend."""
import sys
import argparse
from gitmaze.gui import start_gui


def main():
    parser = argparse.ArgumentParser(description="GitMaze GUI - A NetHack-style Roguelike powered by Git maps.")
    parser.add_argument("--level", "-l", default="level_01", help="Starting level ID (default: level_01)")
    parser.add_argument("--levels-dir", "-d", default="levels", help="Directory containing map files")
    args = parser.parse_args()

    start_gui(levels_dir=args.levels_dir, start_level=args.level)


if __name__ == "__main__":
    main()
