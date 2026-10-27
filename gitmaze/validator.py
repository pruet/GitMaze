"""Validator for GitMaze maps to verify PR contributions and community maps."""
import os
import re
from collections import deque
from typing import List, Tuple, Dict, Any, Set
from .map_loader import MapLoader, MapData


class ValidationError:
    def __init__(self, level_id: str, message: str, severity: str = "ERROR", pos: Tuple[int, int] = None):
        self.level_id = level_id
        self.message = message
        self.severity = severity  # "ERROR" or "WARNING"
        self.pos = pos

    def __str__(self):
        pos_str = f" at ({self.pos[0]}, {self.pos[1]})" if self.pos else ""
        return f"[{self.severity}] [{self.level_id}]{pos_str}: {self.message}"


class MapValidator:
    """Validates that a map adheres to GitMaze standards for gameplay and integrity."""

    @classmethod
    def validate_file(cls, file_path: str) -> List[ValidationError]:
        issues: List[ValidationError] = []
        if not os.path.exists(file_path):
            return [ValidationError(file_path, f"File does not exist: {file_path}")]

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return [ValidationError(file_path, f"Failed to read file: {e}")]

        return cls.validate_string(content, file_path=file_path)

    @classmethod
    def validate_string(cls, content: str, file_path: str = "") -> List[ValidationError]:
        issues: List[ValidationError] = []
        level_id = os.path.basename(file_path) if file_path else "unknown"

        # 1. Frontmatter syntax check
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            issues.append(ValidationError(level_id, "Missing YAML frontmatter delimited by '---'"))
            return issues

        try:
            map_data = MapLoader.load_from_string(content, file_path=file_path)
        except Exception as e:
            issues.append(ValidationError(level_id, f"Failed to parse map: {e}"))
            return issues

        level_id = map_data.id

        # 2. Metadata field validation
        if not re.match(r"^[a-zA-Z0-9_-]+$", map_data.id):
            issues.append(ValidationError(level_id, f"Invalid ID '{map_data.id}': must be alphanumeric with '_' or '-'"))

        if map_data.depth < 1:
            issues.append(ValidationError(level_id, f"Depth must be >= 1, got {map_data.depth}"))

        if not map_data.author or map_data.author == "anonymous":
            issues.append(ValidationError(level_id, "Author field is required (e.g. your GitHub username)", severity="WARNING"))

        # 3. Grid size checks
        if map_data.width < 10 or map_data.height < 5:
            issues.append(ValidationError(level_id, f"Map dimensions too small ({map_data.width}x{map_data.height}). Minimum is 10x5"))

        if map_data.width > 120 or map_data.height > 60:
            issues.append(ValidationError(level_id, f"Map dimensions too large ({map_data.width}x{map_data.height}). Maximum is 120x60"))

        # 4. Spawns and exits
        start_x, start_y = map_data.player_start
        if not (0 <= start_x < map_data.width and 0 <= start_y < map_data.height):
            issues.append(ValidationError(level_id, f"Player start ({start_x}, {start_y}) is outside map bounds"))
        elif not map_data.grid[start_y][start_x].walkable:
            issues.append(ValidationError(level_id, f"Player start ({start_x}, {start_y}) is on unwalkable tile", pos=(start_x, start_y)))

        # 5. Reachability check using BFS
        walkable_from_start = cls._flood_fill(map_data, start_x, start_y)

        if map_data.stairs_down:
            sx, sy = map_data.stairs_down
            if (sx, sy) not in walkable_from_start:
                issues.append(ValidationError(level_id, f"Stairs down (>) at ({sx}, {sy}) are unreachable from player start ({start_x}, {start_y})", pos=(sx, sy)))
        elif map_data.next_level:
            issues.append(ValidationError(level_id, f"Level specifies next_level='{map_data.next_level}' but has no stairs down (>)"))

        if map_data.stairs_up:
            ux, uy = map_data.stairs_up
            if (ux, uy) not in walkable_from_start:
                issues.append(ValidationError(level_id, f"Stairs up (<) at ({ux}, {uy}) are unreachable from player start", pos=(ux, uy)))

        # 6. Entity placement reachability
        for (ix, iy), item_list in map_data.items.items():
            if (ix, iy) not in walkable_from_start:
                issues.append(ValidationError(level_id, f"Item at ({ix}, {iy}) is trapped/unreachable", severity="WARNING", pos=(ix, iy)))

        for m in map_data.monsters:
            if (m.x, m.y) not in walkable_from_start:
                issues.append(ValidationError(level_id, f"Monster '{m.name}' at ({m.x}, {m.y}) is trapped in an unreachable area", severity="WARNING", pos=(m.x, m.y)))

        return issues

    @classmethod
    def _flood_fill(cls, map_data: MapData, start_x: int, start_y: int) -> Set[Tuple[int, int]]:
        visited: Set[Tuple[int, int]] = set()
        queue = deque([(start_x, start_y)])
        visited.add((start_x, start_y))

        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < map_data.width and 0 <= ny < map_data.height:
                    tile = map_data.grid[ny][nx]
                    # Walkable tiles or doors can be traversed
                    if tile.walkable and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        return visited
