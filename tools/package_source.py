"""Build an allowlisted, inspectable source ZIP without private workspace history."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from check_release import ROOT, check


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    checksum = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or checksum.exists():
        raise SystemExit("Refusing to overwrite an existing archive or checksum")
    files = check()
    if output in files or checksum in files:
        raise SystemExit("Output must not be an allowlisted source file")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = (Path("rdp-computer-use") / path.relative_to(ROOT)).as_posix()
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with checksum.open("x", encoding="utf-8") as handle:
        handle.write(f"{digest}  {output.name}\n")
    print(json.dumps({"archive": output.name, "files": len(files), "sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
