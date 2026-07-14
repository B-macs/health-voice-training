# praat_scripts/

Empty by design. The official AVQI/ABI Praat scripts are a paid, licensed
Phonanium product (~€67) and cannot legally be vendored into this repo --
see `PLAN.md` ("Architecture decision: AVQI / ABI sourcing") and
`analysis/indices.py`'s module docstring for the full rationale.

`analysis/indices.py` currently reimplements AVQI v03.01 and ABI directly
from the published, peer-reviewed coefficients using `parselmouth`.

If you obtain a licensed copy of the official script, drop the `.praat`
file(s) here and wire them up via `parselmouth.praat.run_file(...)` as a
substitute backend in `analysis/indices.py` -- that would let you validate
(or replace) the current formula-reimplementation against the real script's
output on the same input file.
