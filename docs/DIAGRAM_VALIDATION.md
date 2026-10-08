# Diagram delivery evidence

Generated on 2026-10-02 with the installed Archify 2.17 skill. Diagram wording
and component relationships were derived from the public core's source files.
Both diagrams use English, the showcase profile, and static motion by default.

## Architecture

```text
diagram_type: architecture
output: docs/visualizations/release.architecture.html
specification_sha256: 1ea7efbfc0f7733f3ab0118be4f8b5d35ee740f5200789ca3b4a1e31ee491149
artifact_sha256: cf369ef673efc23a7108e8249bff556d0dc820254e28394c06ebf0f535d1a10e
validation: 9/9 showcase, 0 errors, 0 warnings
browser_evidence: failed
visual_review: failed (full interactive review could not be completed)
correction_rounds: 0
```

Specification: 2,442 bytes. HTML: 708,769 bytes.

## Sequence

```text
diagram_type: sequence
output: docs/visualizations/control-loop.sequence.html
specification_sha256: ea536d0e97faad448d5690678e26432984d65a87b6c49cecac5e4afefeb97ca9
artifact_sha256: f48bd23f3a241e0dd2140d24c170047fdf32a6e879041496cf23076582f814ca
validation: 9/9 showcase, 0 errors, 0 warnings
browser_evidence: failed
visual_review: failed (full interactive review could not be completed)
correction_rounds: 0
```

Specification: 2,584 bytes. HTML: 709,000 bytes.

## What passed, and what did not

Archify `deliver` completed successfully for each frozen specification. This
proves deterministic artifact checks and byte identity, not browser behavior.
`visual-check` then failed because the Chrome DevTools process exited with
SIGABRT in the execution environment. No completed viewport measurements or
browser captures were produced. The failed `.visual-check.json` receipts remain
next to the HTML; local user paths were mechanically replaced with relative
paths for publication, without changing hashes or outcomes.

Both commands were retried during the 0.2.0a2 validation pass on 2026-10-02 and
failed with the same environment error. Both unchanged specifications again
passed 9/9 showcase checks. Automated tests also verify that receipt hashes and
byte counts match the actual HTML. No browser pass is inferred from static tests.

The full interactive visual-review gate remains incomplete; this is not an
observed diagram geometry defect. No claims are made about full-viewer desktop
containment, both-theme rendering, focus/search closure, or runtime exports.

The README's passive PNG/SVG images were separately derived from the frozen
inline SVG geometry with dark-theme styling and rendered using Sharp, without
executing HTML or JavaScript. An image-capable reviewer inspected both PNGs and
the hero illustration: text is readable, relationships are visible, and no
overlaps/clipping were observed. This **static-preview review passed**, but it
does not replace or upgrade the failed browser/full-viewer status above.

Before claiming full viewer acceptance, run in a browser-capable environment:

```bash
node /path/to/archify/bin/archify.mjs visual-check docs/visualizations/release.architecture.html --json
node /path/to/archify/bin/archify.mjs visual-check docs/visualizations/control-loop.sequence.html --json
```

Inspect both themes and the 1440×900 through 2048×1320 captures. Preserve the
distinction between artifact validation, automated browser evidence, and actual
perceptual inspection. Do not replace these receipts with a fabricated pass.
