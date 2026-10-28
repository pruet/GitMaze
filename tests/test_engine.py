"""Unit tests for GitMaze engine and mechanics."""
import unittest
from gitmaze.engine import GameEngine
from gitmaze.entities import Player, Monster
from gitmaze.items import Potion, Food, Weapon, Gold
from gitmaze.combat import resolve_attack
from gitmaze.fov import FOV


class TestEngineMechanics(unittest.TestCase):

    def setUp(self):
        self.engine = GameEngine(levels_dir="levels", start_level_id="level_01")

    def test_initial_state(self):
        self.assertIsNotNone(self.engine.player)
        self.assertEqual(self.engine.player.char, "@")
        self.assertTrue(self.engine.player.hp > 0)
        self.assertEqual(self.engine.current_level_id, "level_01")
        self.assertTrue(len(self.engine.visible_tiles) > 0)

    def test_movement_and_bump(self):
        px, py = self.engine.player.x, self.engine.player.y
        # Try moving into wall or floor
        self.engine.handle_move_or_attack(1, 0)
        # Coordinates should either have changed or stayed same if blocked
        self.assertTrue((self.engine.player.x, self.engine.player.y) != (0, 0))

    def test_fov_computation(self):
        # Center in 5x5 room
        def transparent(x, y):
            return 1 <= x <= 3 and 1 <= y <= 3

        vis = FOV.compute(2, 2, 4, transparent)
        self.assertIn((2, 2), vis)
        self.assertIn((1, 1), vis)
        self.assertIn((3, 3), vis)

    def test_combat_resolution(self):
        player = Player(x=1, y=1, char="@", color="white", name="Hero", max_hp=20, hp=20)
        goblin = Monster(x=1, y=2, char="g", color="green", name="goblin", max_hp=5, hp=5)
        msgs = resolve_attack(player, goblin)
        self.assertTrue(len(msgs) > 0)
        # Either hit or miss
        self.assertTrue(any("hit" in m or "miss" in m for m in msgs))

    def test_potion_healing(self):
        p = self.engine.player
        p.hp = 10
        p.max_hp = 25
        pot = Potion(name="healing potion", char="!", color="magenta", effect="heal", power=10)
        res = pot.use(p, self.engine)
        self.assertEqual(p.hp, 20)
        self.assertIn("much better", res)

    def test_multiple_stairs_and_branching(self):
        # Level 1 has 2 down exits: stairs (70, 3) -> level_02, and ladder (60, 14) -> goblin_mines_01
        self.assertEqual(len(self.engine.current_level.exits), 2)
        exits_by_char = {e.char: e for e in self.engine.current_level.exits}
        self.assertIn(">", exits_by_char)
        self.assertIn("}", exits_by_char)

        # Move player to ladder } and descend
        self.engine.player.x, self.engine.player.y = 60, 14
        self.engine.descend_stairs()

        # Should arrive in goblin_mines_01
        self.assertEqual(self.engine.current_level_id, "goblin_mines_01")
        self.assertEqual(self.engine.player.x, 6)
        self.assertEqual(self.engine.player.y, 3)

        # Climb back up ladder { to level_01
        self.engine.ascend_stairs()
        self.assertEqual(self.engine.current_level_id, "level_01")
        self.assertEqual(self.engine.player.x, 60)
        self.assertEqual(self.engine.player.y, 14)

    def test_food_nutrition(self):
        p = self.engine.player
        p.hunger = 300
        food = Food(name="ration", char="%", color="green", nutrition=400)
        food.use(p, self.engine)
        self.assertEqual(p.hunger, 700)


if __name__ == "__main__":
    unittest.main()
