"""Unit tests for GitMaze Map Editor."""
import unittest
import tkinter as tk
from gitmaze.editor import MapEditor


class TestMapEditor(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_editor_initialization(self):
        editor = MapEditor(self.root)
        self.assertEqual(editor.width, 79)
        self.assertEqual(editor.height, 20)
        self.assertTrue(len(editor.grid) == 20)
        self.assertTrue(len(editor.grid[0]) == 79)

    def test_editor_serialization(self):
        editor = MapEditor(self.root)
        editor.meta_id.set("test_serialize")
        editor.meta_name.set("Test Chamber")
        serialized = editor.serialize_map()
        self.assertIn("id: test_serialize", serialized)
        self.assertIn("name: Test Chamber", serialized)
        self.assertIn("---", serialized)

    def test_editor_validation_check(self):
        editor = MapEditor(self.root)
        editor.meta_id.set("valid_chamber")
        # Default room has @ and >
        is_valid = editor.action_validate()
        self.assertTrue(is_valid)

    def test_editor_flood_fill(self):
        editor = MapEditor(self.root)
        # Clear small region
        editor.grid[1][1] = "."
        editor.grid[1][2] = "."
        editor.grid[2][1] = "."
        editor.grid[2][2] = "."
        editor.flood_fill(1, 1, "#")
        self.assertEqual(editor.grid[1][1], "#")
        self.assertEqual(editor.grid[1][2], "#")
        self.assertEqual(editor.grid[2][1], "#")
        self.assertEqual(editor.grid[2][2], "#")


if __name__ == "__main__":
    unittest.main()
