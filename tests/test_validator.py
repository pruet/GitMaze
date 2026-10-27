"""Unit tests for GitMaze map validator."""
import unittest
from gitmaze.validator import MapValidator


class TestMapValidator(unittest.TestCase):

    def test_valid_map(self):
        valid_map = """---
id: test_01
name: Test Level
depth: 1
author: tester
description: A test level
next_level: null
prev_level: null
---
##########
#........#
#.@....>.#
#........#
##########
"""
        issues = MapValidator.validate_string(valid_map, "test.map")
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertEqual(len(errors), 0)

    def test_missing_frontmatter(self):
        invalid_map = """
##########
#.@....>.#
##########
"""
        issues = MapValidator.validate_string(invalid_map, "test.map")
        self.assertTrue(any("Missing YAML frontmatter" in i.message for i in issues))

    def test_unreachable_stairs(self):
        unreachable_map = """---
id: test_unreachable
name: Blocked Level
depth: 1
author: tester
description: Stairs are blocked by walls
next_level: null
prev_level: null
---
################
#.@....#....>..#
################
"""
        issues = MapValidator.validate_string(unreachable_map, "test.map")
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertTrue(any("unreachable" in err.message.lower() for err in errors))

    def test_small_dimensions(self):
        tiny_map = """---
id: tiny
name: Tiny
depth: 1
author: tester
next_level: null
prev_level: null
---
###
#@#
"""
        issues = MapValidator.validate_string(tiny_map, "tiny.map")
        self.assertTrue(any("too small" in i.message for i in issues))


if __name__ == "__main__":
    unittest.main()
