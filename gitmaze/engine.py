"""Main Game Engine for GitMaze."""
import os
import random
from typing import Dict, List, Optional, Set, Tuple
from .entities import Player, Monster, Fighter
from .items import Item, Weapon, Armor, Potion, Scroll, Food, Gold
from .map_loader import MapLoader, MapData
from .fov import FOV
from .combat import resolve_attack


class GameEngine:
    def __init__(self, levels_dir: str = "levels", start_level_id: str = "level_01"):
        self.levels_dir = levels_dir
        self.levels: Dict[str, MapData] = {}
        self.current_level_id = start_level_id
        self.current_level: Optional[MapData] = None
        self.explored_tiles: Dict[str, Set[Tuple[int, int]]] = {}
        self.visible_tiles: Set[Tuple[int, int]] = set()
        self.turn = 1
        self.messages: List[str] = []
        self.game_over = False
        self.won = False
        self.fov_radius = 8

        # Create Player
        self.player = Player(
            x=1, y=1, char="@", color="bright_white", name="Adventurer",
            max_hp=25, hp=25, base_ac=10, str_score=14, dex_score=12
        )
        # Give starting gear
        starter_dagger = Weapon(name="dagger", char=")", color="white", damage_dice=1, damage_sides=4, bonus=1)
        starter_ration = Food(name="food ration", char="%", color="green", nutrition=600)
        starter_pot = Potion(name="potion of healing", char="!", color="magenta", effect="heal", power=20)
        self.player.inventory.extend([starter_dagger, starter_ration, starter_pot])
        self.player.equipped_weapon = starter_dagger

        self.load_all_levels()
        self.switch_to_level(start_level_id, from_stairs="start")
        self.log_message("Welcome to GitMaze! Press '?' for help, 'M' for Git map details.")

    def log_message(self, msg: str):
        self.messages.append(msg)
        if len(self.messages) > 100:
            self.messages.pop(0)

    def load_all_levels(self):
        if not os.path.exists(self.levels_dir):
            return

        for fname in os.listdir(self.levels_dir):
            if fname.endswith(".map") or fname.endswith(".txt"):
                fpath = os.path.join(self.levels_dir, fname)
                try:
                    m = MapLoader.load_from_file(fpath)
                    self.levels[m.id] = m
                    self.explored_tiles[m.id] = set()
                except Exception as e:
                    self.log_message(f"Warning: Failed to load map {fname}: {e}")

    def switch_to_level(self, level_id: str, from_stairs: str = "down"):
        if level_id not in self.levels:
            # Try to load directly from file
            potential_file = os.path.join(self.levels_dir, f"{level_id}.map")
            if os.path.exists(potential_file):
                self.levels[level_id] = MapLoader.load_from_file(potential_file)
                self.explored_tiles[level_id] = set()
            else:
                self.log_message(f"There is no way to {level_id}!")
                return

        self.current_level_id = level_id
        self.current_level = self.levels[level_id]

        # Position player
        if from_stairs == "start":
            self.player.x, self.player.y = self.current_level.player_start
        elif from_stairs == "down":
            if self.current_level.stairs_up:
                self.player.x, self.player.y = self.current_level.stairs_up
            else:
                self.player.x, self.player.y = self.current_level.player_start
        elif from_stairs == "up":
            if self.current_level.stairs_down:
                self.player.x, self.player.y = self.current_level.stairs_down
            else:
                self.player.x, self.player.y = self.current_level.player_start

        self.update_fov()
        self.log_message(f"You enter {self.current_level.name} (Depth {self.current_level.depth}).")
        if self.current_level.author:
            self.log_message(f"[Map Contributor: {self.current_level.author} | Git SHA: {self.current_level.git_sha}]")

    def update_fov(self):
        if not self.current_level:
            return

        def is_transparent(x: int, y: int) -> bool:
            if 0 <= x < self.current_level.width and 0 <= y < self.current_level.height:
                return self.current_level.grid[y][x].transparent
            return False

        self.visible_tiles = FOV.compute(
            self.player.x, self.player.y, self.fov_radius, is_transparent
        )
        self.explored_tiles.setdefault(self.current_level_id, set()).update(self.visible_tiles)

    def is_walkable(self, x: int, y: int) -> bool:
        if not (0 <= x < self.current_level.width and 0 <= y < self.current_level.height):
            return False
        tile = self.current_level.grid[y][x]
        if not tile.walkable:
            return False
        # Check if monster occupies tile
        for m in self.current_level.monsters:
            if m.alive and m.x == x and m.y == y:
                return False
        # Check if player occupies tile
        if self.player.x == x and self.player.y == y:
            return False
        return True

    def get_monster_at(self, x: int, y: int) -> Optional[Monster]:
        for m in self.current_level.monsters:
            if m.alive and m.x == x and m.y == y:
                return m
        return None

    def handle_move_or_attack(self, dx: int, dy: int):
        target_x = self.player.x + dx
        target_y = self.player.y + dy

        if not (0 <= target_x < self.current_level.width and 0 <= target_y < self.current_level.height):
            self.log_message("You cannot move past the edge of the world.")
            return

        # Check for monster in target cell
        monster = self.get_monster_at(target_x, target_y)
        if monster:
            attack_msgs = resolve_attack(self.player, monster)
            for m in attack_msgs:
                self.log_message(m)
            self.end_player_turn()
            return

        tile = self.current_level.grid[target_y][target_x]

        # Check for closed door
        if tile.is_door and not tile.door_open:
            tile.door_open = True
            tile.char = "/"
            tile.transparent = True
            self.log_message("You open the door.")
            self.end_player_turn()
            return

        if not tile.walkable:
            self.log_message("Ouch! You bump into a wall.")
            return

        # Move player
        self.player.x = target_x
        self.player.y = target_y

        # Check if stepped on items
        pos = (target_x, target_y)
        if pos in self.current_level.items and self.current_level.items[pos]:
            items_here = self.current_level.items[pos]
            if len(items_here) == 1:
                item = items_here[0]
                if isinstance(item, Gold):
                    # Auto pickup gold NetHack style
                    self.player.gold += item.amount
                    self.player.score += item.amount
                    self.current_level.items[pos].remove(item)
                    self.log_message(f"You pick up {item.amount} gold pieces.")
                else:
                    self.log_message(f"You see here a {item.name}.")
            else:
                self.log_message(f"There are several items here ({len(items_here)} items).")

        self.end_player_turn()

    def pickup_item(self):
        pos = (self.player.x, self.player.y)
        items = self.current_level.items.get(pos, [])
        if not items:
            self.log_message("There is nothing here to pick up.")
            return

        if len(self.player.inventory) >= 26:
            self.log_message("Your pack is completely full!")
            return

        item = items.pop(0)
        if isinstance(item, Gold):
            self.player.gold += item.amount
            self.player.score += item.amount
            self.log_message(f"You pick up {item.amount} gold pieces.")
        else:
            self.player.inventory.append(item)
            self.log_message(f"You pick up the {item.name}.")
        self.end_player_turn()

    def drop_item(self, index: int):
        if not (0 <= index < len(self.player.inventory)):
            return
        item = self.player.inventory.pop(index)
        if self.player.equipped_weapon == item:
            self.player.equipped_weapon = None
            self.log_message(f"You unwield the {item.name}.")
        elif self.player.equipped_armor == item:
            self.player.equipped_armor = None
            self.log_message(f"You take off the {item.name}.")

        pos = (self.player.x, self.player.y)
        self.current_level.items.setdefault(pos, []).append(item)
        self.log_message(f"You drop the {item.name}.")
        self.end_player_turn()

    def use_item(self, index: int):
        if not (0 <= index < len(self.player.inventory)):
            return
        item = self.player.inventory[index]
        if isinstance(item, Weapon):
            if self.player.equipped_weapon == item:
                self.player.equipped_weapon = None
                self.log_message(f"You unwield the {item.name}.")
            else:
                self.player.equipped_weapon = item
                self.log_message(f"You wield the {item.name}.")
        elif isinstance(item, Armor):
            if self.player.equipped_armor == item:
                self.player.equipped_armor = None
                self.log_message(f"You take off the {item.name}.")
            else:
                self.player.equipped_armor = item
                self.log_message(f"You put on the {item.name}.")
        elif isinstance(item, (Potion, Scroll, Food)):
            res = item.use(self.player, self)
            self.log_message(res)
            self.player.inventory.pop(index)
        else:
            self.log_message(f"You don't know how to use the {item.name}.")
        self.end_player_turn()

    def descend_stairs(self):
        pos = (self.player.x, self.player.y)
        if self.current_level.stairs_down and pos == self.current_level.stairs_down:
            next_id = self.current_level.next_level
            if next_id:
                self.switch_to_level(next_id, from_stairs="down")
            else:
                # Reached the end!
                self.won = True
                self.game_over = True
                self.log_message("*** You have retrieved the Amulet and conquered GitMaze! You Win! ***")
        else:
            self.log_message("You cannot go down here.")

    def ascend_stairs(self):
        pos = (self.player.x, self.player.y)
        if self.current_level.stairs_up and pos == self.current_level.stairs_up:
            prev_id = self.current_level.prev_level
            if prev_id:
                self.switch_to_level(prev_id, from_stairs="up")
            else:
                self.log_message("The entrance is sealed behind you.")
        else:
            self.log_message("You cannot go up here.")

    def wait_turn(self):
        self.log_message("You wait a moment...")
        self.end_player_turn()

    def teleport_entity(self, entity: Fighter):
        """Teleport entity to a random walkable position."""
        walkable_coords = []
        for y in range(self.current_level.height):
            for x in range(self.current_level.width):
                if self.is_walkable(x, y):
                    walkable_coords.append((x, y))
        if walkable_coords:
            entity.x, entity.y = random.choice(walkable_coords)

    def reveal_full_map(self):
        """Magic mapping: explore all tiles in current level."""
        for y in range(self.current_level.height):
            for x in range(self.current_level.width):
                self.explored_tiles[self.current_level_id].add((x, y))

    def end_player_turn(self):
        self.turn += 1
        # Tick player effects & hunger
        msgs = self.player.tick_turn()
        for m in msgs:
            self.log_message(m)

        if not self.player.is_alive:
            self.game_over = True
            self.log_message("*** You died! Game over. ***")
            return

        # Monsters turn
        for monster in self.current_level.monsters:
            if not monster.alive:
                continue

            action = monster.get_action(self)
            if action:
                dx, dy = action
                nx = monster.x + dx
                ny = monster.y + dy

                # If attacking player
                if nx == self.player.x and ny == self.player.y:
                    combat_msgs = resolve_attack(monster, self.player)
                    for cm in combat_msgs:
                        self.log_message(cm)
                    if not self.player.is_alive:
                        self.game_over = True
                        break
                elif self.is_walkable(nx, ny):
                    monster.x = nx
                    monster.y = ny

        self.update_fov()
