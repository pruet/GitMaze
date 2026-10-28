"""Map loader and Git provenance parser for GitMaze."""
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import yaml
from .items import Item, create_item_from_char
from .entities import Monster, create_monster_from_char


@dataclass
class Tile:
    char: str
    walkable: bool
    transparent: bool
    color: str = "white"
    is_door: bool = False
    door_open: bool = False


@dataclass
class Exit:
    x: int
    y: int
    char: str  # '>', '<', '}', '{'
    direction: str  # 'down' or 'up'
    target_level: Optional[str] = None
    target_pos: Optional[Tuple[int, int]] = None
    label: str = ""


@dataclass
class MapData:
    id: str
    name: str
    depth: int
    author: str
    description: str
    next_level: Optional[str]
    prev_level: Optional[str]
    width: int
    height: int
    grid: List[List[Tile]]
    player_start: Tuple[int, int]
    stairs_down: Optional[Tuple[int, int]]
    stairs_up: Optional[Tuple[int, int]]
    items: Dict[Tuple[int, int], List[Item]] = field(default_factory=dict)
    monsters: List[Monster] = field(default_factory=list)
    exits: List[Exit] = field(default_factory=list)
    exits_by_pos: Dict[Tuple[int, int], Exit] = field(default_factory=dict)
    git_sha: str = "local"
    git_last_author: str = "unknown"
    git_commit_msg: str = "uncommitted"
    file_path: str = ""


class MapLoader:
    """Loads map files from repository and parses frontmatter + ASCII grid."""

    @staticmethod
    def get_git_info(file_path: str) -> Dict[str, str]:
        """Query Git for the last commit details on this map file."""
        info = {
            "git_sha": "local",
            "git_last_author": "working-tree",
            "git_commit_msg": "uncommitted changes",
        }
        try:
            abs_path = os.path.abspath(file_path)
            file_dir = os.path.dirname(abs_path) or "."
            file_name = os.path.basename(abs_path)
            res = subprocess.run(
                ["git", "log", "-1", "--format=%h|%an|%s", "--", file_name],
                capture_output=True,
                text=True,
                cwd=file_dir,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("|", 2)
                if len(parts) >= 1:
                    info["git_sha"] = parts[0]
                if len(parts) >= 2:
                    info["git_last_author"] = parts[1]
                if len(parts) >= 3:
                    info["git_commit_msg"] = parts[2]
        except Exception:
            pass
        return info

    @classmethod
    def load_from_file(cls, file_path: str) -> MapData:
        """Parse a .map file into MapData."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return cls.load_from_string(content, file_path=file_path)

    @classmethod
    def load_from_string(cls, content: str, file_path: str = "") -> MapData:
        """Parse frontmatter and ASCII grid from text."""
        metadata = {}
        ascii_grid = ""

        # Check for YAML frontmatter between ---
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if frontmatter_match:
            yaml_text = frontmatter_match.group(1)
            ascii_grid = frontmatter_match.group(2)
            try:
                metadata = yaml.safe_load(yaml_text) or {}
            except Exception as e:
                raise ValueError(f"Invalid YAML frontmatter: {e}")
        else:
            ascii_grid = content

        level_id = str(metadata.get("id", "custom_level"))
        name = str(metadata.get("name", "Unknown Dungeon"))
        depth = int(metadata.get("depth", 1))
        author = str(metadata.get("author", "anonymous"))
        description = str(metadata.get("description", ""))
        next_level = metadata.get("next_level")
        prev_level = metadata.get("prev_level")

        # Parse ASCII grid
        lines = [line.rstrip("\r\n") for line in ascii_grid.splitlines()]
        # Strip potential leading blank lines
        while lines and not lines[0].strip():
            lines.pop(0)

        if not lines:
            raise ValueError("Map ASCII grid is empty!")

        height = len(lines)
        width = max(len(line) for line in lines)

        # Pad lines so every row has length = width
        normalized_lines = [line.ljust(width) for line in lines]

        grid: List[List[Tile]] = []
        player_start: Optional[Tuple[int, int]] = None
        stairs_down: Optional[Tuple[int, int]] = None
        stairs_up: Optional[Tuple[int, int]] = None
        items: Dict[Tuple[int, int], List[Item]] = {}
        monsters: List[Monster] = []

        monster_chars = set("dkgzoD")
        item_chars = set("$!?)[%/")

        for y, row in enumerate(normalized_lines):
            tile_row: List[Tile] = []
            for x, char in enumerate(row):
                # Default tile assumptions
                if char in ("#", "-", "|"):
                    # Wall
                    tile = Tile(char=char, walkable=False, transparent=False, color="bright_blue")
                elif char == ".":
                    # Floor
                    tile = Tile(char=".", walkable=True, transparent=True, color="dark_gray")
                elif char == "+":
                    # Closed door
                    tile = Tile(char="+", walkable=True, transparent=False, color="yellow", is_door=True, door_open=False)
                elif char == "/":
                    # Open door
                    tile = Tile(char="/", walkable=True, transparent=True, color="yellow", is_door=True, door_open=True)
                elif char == " ":
                    # Empty rock / void
                    tile = Tile(char=" ", walkable=False, transparent=False, color="black")
                elif char in (">", "}"):
                    # Stairs down (>) or Ladder down (})
                    color = "bright_white" if char == ">" else "bright_yellow"
                    tile = Tile(char=char, walkable=True, transparent=True, color=color)
                    if stairs_down is None:
                        stairs_down = (x, y)
                elif char in ("<", "{"):
                    # Stairs up (<) or Ladder up ({)
                    color = "bright_white" if char == "<" else "bright_yellow"
                    tile = Tile(char=char, walkable=True, transparent=True, color=color)
                    if stairs_up is None:
                        stairs_up = (x, y)
                elif char == "@":
                    # Player spawn
                    tile = Tile(char=".", walkable=True, transparent=True, color="dark_gray")
                    player_start = (x, y)
                elif char in item_chars:
                    # Item on floor
                    tile = Tile(char=".", walkable=True, transparent=True, color="dark_gray")
                    new_item = create_item_from_char(char, depth=depth)
                    if new_item:
                        items.setdefault((x, y), []).append(new_item)
                elif char in monster_chars:
                    # Monster spawn on floor
                    tile = Tile(char=".", walkable=True, transparent=True, color="dark_gray")
                    m = create_monster_from_char(char, x=x, y=y, depth=depth)
                    if m:
                        monsters.append(m)
                else:
                    # Fallback floor
                    tile = Tile(char=".", walkable=True, transparent=True, color="dark_gray")

                tile_row.append(tile)
            grid.append(tile_row)

        if player_start is None:
            # Fallback player start to stairs up or first walkable floor
            if stairs_up:
                player_start = stairs_up
            else:
                found = False
                for y in range(height):
                    for x in range(width):
                        if grid[y][x].walkable:
                            player_start = (x, y)
                            found = True
                            break
                    if found:
                        break
                if not found:
                    player_start = (1, 1)

        # Build exits from grid and metadata
        raw_exits = metadata.get("exits", [])
        configured_exits_by_pos = {}
        if isinstance(raw_exits, list):
            for e_data in raw_exits:
                if isinstance(e_data, dict) and "pos" in e_data:
                    epos = tuple(e_data["pos"])
                    configured_exits_by_pos[epos] = e_data

        exits: List[Exit] = []
        exits_by_pos: Dict[Tuple[int, int], Exit] = {}

        for y in range(height):
            for x in range(width):
                tile_char = grid[y][x].char
                if tile_char in (">", "}", "<", "{"):
                    pos = (x, y)
                    is_down = tile_char in (">", "}")
                    direction = "down" if is_down else "up"
                    cfg = configured_exits_by_pos.get(pos, {})

                    default_target = next_level if is_down else prev_level
                    target_lvl = cfg.get("target_level", cfg.get("dest", default_target))
                    target_pos_raw = cfg.get("target_pos")
                    target_pos = tuple(target_pos_raw) if target_pos_raw else None

                    default_label = (
                        "Stairs down" if tile_char == ">"
                        else "Ladder down" if tile_char == "}"
                        else "Stairs up" if tile_char == "<"
                        else "Ladder up"
                    )
                    label = cfg.get("label", default_label)

                    exit_obj = Exit(
                        x=x,
                        y=y,
                        char=tile_char,
                        direction=direction,
                        target_level=target_lvl,
                        target_pos=target_pos,
                        label=label,
                    )
                    exits.append(exit_obj)
                    exits_by_pos[pos] = exit_obj

        git_info = cls.get_git_info(file_path) if file_path else {}

        return MapData(
            id=level_id,
            name=name,
            depth=depth,
            author=author,
            description=description,
            next_level=next_level,
            prev_level=prev_level,
            width=width,
            height=height,
            grid=grid,
            player_start=player_start,
            stairs_down=stairs_down,
            stairs_up=stairs_up,
            items=items,
            monsters=monsters,
            exits=exits,
            exits_by_pos=exits_by_pos,
            git_sha=git_info.get("git_sha", "local"),
            git_last_author=git_info.get("git_last_author", author),
            git_commit_msg=git_info.get("git_commit_msg", "none"),
            file_path=file_path,
        )
