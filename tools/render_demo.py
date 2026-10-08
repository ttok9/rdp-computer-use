"""Render a truthful, passive terminal card from the actual offline demo output."""
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    process = subprocess.run([sys.executable, '-m', 'rdp_cua', 'demo'], text=True, capture_output=True, check=True, timeout=15)
    result = json.loads(process.stdout)
    if result['status'] != 'succeeded' or result['step_count'] != 2:
        raise SystemExit('Unexpected scripted demo result; refusing to label it success')
    (ROOT / 'examples/demo-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    lines = ['$ rdp-cua demo', '', 'OFFLINE / SCRIPTED DESKTOP / NO NETWORK', '', f"status      {result['status']}", f"step_count  {result['step_count']}"]
    lines.extend(f"step {step['number']}      {step['action']}  →  {step['verification']}" for step in result['steps'])
    lines += ['', 'Same runner. Synthetic desktop. Not a live Windows recording.']
    rows = []
    for index, line in enumerate(lines):
        color = '#65e4cb' if index in (0, 4) else '#b9cbe0'
        rows.append(f'<text x="34" y="{80+index*27}" fill="{color}">{html.escape(line)}</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="370" viewBox="0 0 1100 370" role="img" aria-label="Actual offline scripted demo output, not live RDP"><rect width="1100" height="370" rx="16" fill="#0c1728"/><circle cx="27" cy="26" r="5" fill="#65e4cb"/><circle cx="45" cy="26" r="5" fill="#506a85"/><circle cx="63" cy="26" r="5" fill="#506a85"/><g font-family="monospace" font-size="17">' + ''.join(rows) + '</g></svg>\n'
    (ROOT / 'docs/assets/demo.svg').write_text(svg, encoding='utf-8')
    print('Generated demo-result.json and demo.svg from the scripted runner')


if __name__ == '__main__':
    main()
