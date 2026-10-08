"""Repeatable local verification. No RDP connection or model request is made."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from check_release import ROOT, check


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-adapters', action='store_true')
    args = parser.parse_args()
    environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    checks = []

    def run(label, arguments):
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, env=environment,
                                capture_output=True, text=True, timeout=120)
        checks.append({'check': label, 'passed': result.returncode == 0})
        if result.returncode:
            # Print diagnostics locally; never store them as a public receipt.
            print(result.stderr, file=sys.stderr)
            raise RuntimeError(label)
        return result

    try:
        files = check()
        checks.append({'check': 'release_content_and_links', 'passed': True, 'files': len(files)})
        suite = run('unit_and_contract_tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-q'])
        match = re.search(r'Ran (\d+) tests?', suite.stderr)
        skipped = re.search(r'skipped=(\d+)', suite.stderr)
        checks[-1].update(discovered=int(match.group(1)) if match else None,
                          skipped=int(skipped.group(1)) if skipped else 0)
        run('bytecode_compile', ['-m', 'compileall', '-q', 'src', 'tests', 'tools'])
        doctor = ['-m', 'rdp_cua', 'doctor'] + (['--require-adapters'] if args.require_adapters else [])
        run('doctor', doctor)
        demo = json.loads(run('offline_demo', ['-m', 'rdp_cua', 'demo']).stdout)
        if demo != json.loads((ROOT / 'examples/demo-result.json').read_text()):
            raise ValueError('committed demo result differs from actual demo')
        checks.append({'check': 'demo_fixture_matches', 'passed': True})
        for scenario in sorted((ROOT / 'examples/scenarios').iterdir()):
            if scenario.suffix in {'.json', '.md'}:
                run('scenario_' + scenario.name, ['-m', 'rdp_cua', 'scenario-check', str(scenario)])
        run('dependency_consistency', ['-m', 'pip', 'check'])
        with tempfile.TemporaryDirectory(prefix='rdp-cua-verify-') as directory:
            first, second = Path(directory) / 'first.zip', Path(directory) / 'second.zip'
            run('source_zip_build', ['tools/package_source.py', '--output', str(first)])
            run('source_zip_repeat', ['tools/package_source.py', '--output', str(second)])
            if hashlib.sha256(first.read_bytes()).digest() != hashlib.sha256(second.read_bytes()).digest():
                raise ValueError('source archives are not reproducible')
            with zipfile.ZipFile(first) as archive:
                expected = {'rdp-computer-use/' + p.relative_to(ROOT).as_posix() for p in files}
                if set(archive.namelist()) != expected or archive.testzip() is not None:
                    raise ValueError('source archive differs from allowlist')
                for path in files:
                    if archive.read('rdp-computer-use/' + path.relative_to(ROOT).as_posix()) != path.read_bytes():
                        raise ValueError('source archive content mismatch')
            checks.append({'check': 'zip_reproducibility_integrity_and_exact_membership', 'passed': True})
        status = 'passed'
    except Exception as exc:
        checks.append({'check': 'verification_aborted', 'passed': False, 'error_type': type(exc).__name__})
        status = 'failed'
    print(json.dumps({'status': status, 'python': platform.python_version(), 'platform': platform.system(),
                      'checks': checks, 'not_covered': ['live RDP', 'live model', 'public CI', 'browser rendering', 'dependency vulnerability audit']}, indent=2))
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
