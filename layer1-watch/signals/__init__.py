"""Signal modules for layer1-watch.

Each signal module exposes:
  fetch_live(corridor: str) -> tuple[float | None, list[dict]]

Returns (score_0_to_100_or_None, evidence_list).
A None score means the signal source was unavailable or produced no data —
the fuser will skip it and redistribute its weight to available signals.
"""
