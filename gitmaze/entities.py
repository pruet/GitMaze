"""Entities for GitMaze: Player and Monsters."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import random
from .items import Item, Weapon, Armor


@dataclass
class Entity:
    x: int
    y: int
    char: str
    color: str
    name: str
    blocks_movement: bool = True
    alive: bool = True

    def distance_to(self, target_x: int, target_y: int) -> float:
        return ((self.x - target_x) ** 2 + (self.y - target_y) ** 2) ** 0.5


@dataclass
class Fighter(Entity):
    max_hp: int = 15
    hp: int = 15
    base_ac: int = 10  # D&D / NetHack AC: lower or higher depending on formula, we treat AC as Defense Rating
    base_damage_dice: int = 1
    base_damage_sides: int = 4
    str_score: int = 12
    dex_score: int = 12
    inventory: List[Item] = field(default_factory=list)
    speed: int = 10  # 10 is normal
    speed_boost: int = 0

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> int:
        actual = max(1, amount)
        self.hp -= actual
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return actual

    def heal(self, amount: int) -> int:
        healed = min(self.max_hp - self.hp, amount)
        self.hp += healed
        return healed


@dataclass
class Player(Fighter):
    char: str = "@"
    color: str = "bright_white"
    name: str = "Player"
    max_hp: int = 20
    hp: int = 20
    level: int = 1
    exp: int = 0
    gold: int = 0
    max_hunger: int = 1000
    hunger: int = 800  # >700 Satiated, 300-700 Normal, 100-300 Hungry, <100 Weak, 0 Starving
    equipped_weapon: Optional[Weapon] = None
    equipped_armor: Optional[Armor] = None
    score: int = 0

    @property
    def ac(self) -> int:
        bonus = self.equipped_armor.ac_bonus if self.equipped_armor else 0
        dex_mod = (self.dex_score - 10) // 2
        return self.base_ac + bonus + dex_mod

    @property
    def hunger_status(self) -> str:
        if self.hunger > 800:
            return "Satiated"
        elif self.hunger > 350:
            return "Normal"
        elif self.hunger > 150:
            return "Hungry"
        elif self.hunger > 0:
            return "Weak"
        return "Fainting"

    def add_exp(self, amount: int) -> List[str]:
        messages = []
        self.exp += amount
        self.score += amount
        needed = self.level * 20
        while self.exp >= needed:
            self.level += 1
            hp_gain = random.randint(4, 8) + (self.str_score - 10) // 2
            hp_gain = max(2, hp_gain)
            self.max_hp += hp_gain
            self.hp += hp_gain
            messages.append(f"Welcome to experience level {self.level}! (Max HP +{hp_gain})")
            needed += self.level * 25
        return messages

    def tick_turn(self) -> List[str]:
        messages = []
        if self.speed_boost > 0:
            self.speed_boost -= 1
            if self.speed_boost == 0:
                messages.append("You slow down to normal speed.")

        # Hunger
        self.hunger = max(0, self.hunger - 1)
        if self.hunger == 150:
            messages.append("You are beginning to feel hungry.")
        elif self.hunger == 50:
            messages.append("You are feeling weak from hunger!")
        elif self.hunger == 0:
            self.take_damage(1)
            messages.append("You are fainting from starvation! (-1 HP)")

        # Natural regen every 15 turns if not hungry
        return messages


@dataclass
class Monster(Fighter):
    ai_type: str = "hostile"
    exp_reward: int = 10
    description: str = ""

    def get_action(self, engine) -> Optional[Tuple[int, int]]:
        """Return target dx, dy step towards player if visible or adjacent."""
        player = engine.player
        dist = self.distance_to(player.x, player.y)

        # If adjacent, attack player
        if dist <= 1.5:
            return (player.x - self.x, player.y - self.y)

        # If player is in sight and within 8 tiles, move towards player
        if dist <= 8 and (self.x, self.y) in engine.visible_tiles:
            # Simple step towards player
            dx = 0
            dy = 0
            if player.x > self.x:
                dx = 1
            elif player.x < self.x:
                dx = -1

            if player.y > self.y:
                dy = 1
            elif player.y < self.y:
                dy = -1

            # Check if direct diagonal or cardinal is walkable
            if engine.is_walkable(self.x + dx, self.y + dy):
                return (dx, dy)
            elif dx != 0 and engine.is_walkable(self.x + dx, self.y):
                return (dx, 0)
            elif dy != 0 and engine.is_walkable(self.x, self.y + dy):
                return (0, dy)

        # Idle wander
        if random.random() < 0.25:
            choices = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            dx, dy = random.choice(choices)
            if engine.is_walkable(self.x + dx, self.y + dy):
                return (dx, dy)
        return None


def create_monster_from_char(char: str, x: int, y: int, depth: int = 1) -> Optional[Monster]:
    """Monster factory based on glyph."""
    if char == "d":
        return Monster(
            x=x, y=y, char="d", color="brown", name="jackal",
            max_hp=6 + depth, hp=6 + depth, base_ac=8,
            base_damage_dice=1, base_damage_sides=4,
            exp_reward=8 * depth, description="A swift, yapping jackal."
        )
    elif char == "k":
        return Monster(
            x=x, y=y, char="k", color="green", name="kobold",
            max_hp=8 + depth * 2, hp=8 + depth * 2, base_ac=9,
            base_damage_dice=1, base_damage_sides=4,
            exp_reward=10 * depth, description="A small reptilian humanoid with a sharp spear."
        )
    elif char == "g":
        return Monster(
            x=x, y=y, char="g", color="bright_green", name="goblin",
            max_hp=12 + depth * 2, hp=12 + depth * 2, base_ac=10,
            base_damage_dice=1, base_damage_sides=6,
            exp_reward=15 * depth, description="A sneaky goblin clutching a rusty blade."
        )
    elif char == "o":
        return Monster(
            x=x, y=y, char="o", color="yellow", name="orc",
            max_hp=18 + depth * 3, hp=18 + depth * 3, base_ac=11,
            base_damage_dice=1, base_damage_sides=8,
            exp_reward=25 * depth, description="A ferocious orc with bloodthirsty red eyes."
        )
    elif char == "z":
        return Monster(
            x=x, y=y, char="z", color="cyan", name="zombie",
            max_hp=22 + depth * 4, hp=22 + depth * 4, base_ac=9,
            base_damage_dice=1, base_damage_sides=6,
            exp_reward=20 * depth, description="A shambling corpse reeking of rot."
        )
    elif char == "D":
        return Monster(
            x=x, y=y, char="D", color="bright_red", name="red dragon",
            max_hp=50 + depth * 10, hp=50 + depth * 10, base_ac=16,
            base_damage_dice=2, base_damage_sides=8,
            exp_reward=100 * depth, description="A terrifying dragon with smoke billowing from its nostrils."
        )
    return None
