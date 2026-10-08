import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
from check_release import local_link_errors, markdown_anchors, selected_files

ROOT = Path(__file__).parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_nested_env_and_runtime_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs/traces').mkdir(parents=True)
            (root / 'docs/traces/session.json').write_text('{}')
            (root / 'docs/.env.private.json').write_text('{}')
            (root / 'docs/public.md').write_text('public')
            self.assertEqual([p.name for p in selected_files(root)], ['public.md'])

    def test_html_image_links_are_checked_against_release_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / 'README.md'
            readme.write_text('<img src="missing.svg">')
            self.assertTrue(local_link_errors(readme, root, {readme}))

    def test_existing_but_excluded_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme, hidden = root / 'README.md', root / 'private.md'
            readme.write_text('[link](private.md)')
            hidden.write_text('not in release')
            self.assertTrue(local_link_errors(readme, root, {readme}))

    def test_valid_and_invalid_heading_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / 'README.md'
            readme.write_text('# Hello world\n[good](#hello-world)\n[bad](#missing)\n')
            errors = local_link_errors(readme, root, {readme})
            self.assertEqual(len(errors), 1)
            self.assertIn('missing heading', errors[0])

    def test_duplicate_heading_anchors(self):
        self.assertEqual(markdown_anchors('# A\n# A\n## B'), {'a', 'a-1', 'b'})

    def test_all_scenarios_parse(self):
        from rdp_cua.scenario import load_scenario
        for path in (ROOT / 'examples/scenarios').iterdir():
            if path.suffix in {'.json', '.md'}:
                with self.subTest(scenario=path.name):
                    self.assertGreater(len(load_scenario(path).steps), 0)

    def test_demo_fixture_is_actual_cli_output(self):
        process = subprocess.run([sys.executable, '-m', 'rdp_cua', 'demo'], capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(json.loads(process.stdout), json.loads((ROOT / 'examples/demo-result.json').read_text()))

    def test_diagram_receipts_bind_exact_artifacts(self):
        for name in ('release.architecture', 'control-loop.sequence'):
            with self.subTest(diagram=name):
                directory = ROOT / 'docs/visualizations'
                receipt = json.loads((directory / (name + '.visual-check.json')).read_text())
                self.assertEqual(receipt['artifact']['sha256'], hashlib.sha256((directory / (name + '.html')).read_bytes()).hexdigest())
                self.assertEqual(receipt['artifact']['bytes'], (directory / (name + '.html')).stat().st_size)
                self.assertEqual(json.loads((directory / (name + '.json')).read_text())['meta']['quality_profile'], 'showcase')


if __name__ == '__main__':
    unittest.main()
