#!/usr/bin/env python3
"""Launcher for the GitMaze Map Editor."""
import sys
import argparse
from gitmaze.editor import start_editor


def main():
    parser = argparse.ArgumentParser(description="GitMaze Map Editor - Create and edit roguelike dungeon maps.")
    parser.add_argument("map_file", nargs="?", default=None, help="Optional path to a .map file to open")
    args = parser.parse_args()

    start_editor(file_path=args.map_file)


if __name__ == "__main__":
    main()
