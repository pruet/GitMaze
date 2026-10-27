"""Unit tests for GitMaze GUI frontend."""
import unittest
import tkinter as tk
from gitmaze.gui import GitMazeGUI


class TestGUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window during test

    def tearDown(self):
        self.root.destroy()

    def test_gui_initialization(self):
        app = GitMazeGUI(self.root, levels_dir="levels", start_level="level_01")
        self.assertIsNotNone(app.engine)
        self.assertEqual(app.engine.current_level_id, "level_01")
        # Test widget population
        self.assertTrue(len(app.inv_listbox.get(0, tk.END)) > 0)
        self.assertIn("Armor Class:", app.stats_label.cget("text"))
        self.assertEqual(app.hp_text.cget("text"), "25/25")


if __name__ == "__main__":
    unittest.main()
