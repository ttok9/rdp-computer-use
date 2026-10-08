# Third-party notices

The project-level MIT license covers this project's original code. It does not
replace the licenses, copyright, or authorship of dependencies or embedded assets.

## Runtime dependencies (installed separately)

| Component | Use | License |
| --- | --- | --- |
| [aardwolf](https://github.com/skelsec/aardwolf), 0.2.13 | RDP transport through the optional `rdp` extra | MIT |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | Client for the configured vision endpoint | Apache-2.0 |

No aardwolf source tree or OpenAI SDK source is vendored here. Package installers
obtain them and their transitive dependencies separately, with their own license
files. Distributors bundling those packages must retain their applicable notices.
This list is not a full dependency license audit or SBOM.

The RDP adapter targets upstream aardwolf. A private, modified fork is **not** part
of this distribution. Integrating a fork later requires a source diff, a clear
record of changes, and preservation of the upstream notices; modifications do
not transfer ownership of the upstream work.

## Archify viewer and derived diagram assets

The standalone HTML files in `docs/visualizations/` include code generated from
[Archify](https://github.com/tt-a1i/archify), version 2.17, itself based on Cocoon AI.
The PNG/SVG previews in `docs/assets/` are derived from these diagrams. The
following notice accompanies that embedded viewer code and derived assets:

```text
MIT License

Copyright (c) 2026 tt-a1i (Archify)
Copyright (c) 2025 Cocoon AI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Names of third-party products identify compatibility or dependencies, not an
endorsement. No ownership of third-party names or marks is claimed.
