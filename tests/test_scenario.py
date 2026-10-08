import unittest
from pathlib import Path

from rdp_cua.scenario import load_scenario, parse_markdown_scenario


class ScenarioTests(unittest.TestCase):
    def test_load_json_example(self) -> None:
        path = Path(__file__).parents[1] / "examples" / "scenarios" / "notepad.json"
        scenario = load_scenario(path)
        self.assertEqual(scenario.title, "Create a note")
        self.assertEqual(len(scenario.steps), 2)

    def test_parse_markdown(self) -> None:
        scenario = parse_markdown_scenario(
            """# Demo

## Goal
Open a public demo application.

## Steps
### 1. Open the application
- **Verification**: The window is visible
"""
        )
        self.assertEqual(scenario.goal, "Open a public demo application.")
        self.assertEqual(scenario.steps[0].verification, "The window is visible")


if __name__ == "__main__":
    unittest.main()

