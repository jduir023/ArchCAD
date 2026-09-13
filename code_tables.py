"""
code_tables.py — Kentucky / IRC 2021 structural lookup tables and helpers.

Kentucky Building Code (KBC) adopts IRC 2021.
Regional defaults for most of central Kentucky (Louisville / Lexington area):
  Ground snow load : 20 psf
  Frost depth      : 24 in
  Wind speed       : 90 mph, Exposure B
  Seismic category : A / B
"""
from __future__ import annotations

# ── Regional defaults ─────────────────────────────────────────────────────────

KY_DEFAULTS: dict = {
    "ground_snow_psf":  20,
    "frost_depth_in":   24,
    "floor_live_psf":   40,   # living areas, IRC R502.3.2
    "deck_live_psf":    40,   # IRC R507
    "dead_load_psf":    10,
    "soil_bearing_psf": 1500, # conservative default (lb/ft²)
}

# ── Deck joist spans — IRC Table R507.6  ─────────────────────────────────────
# Southern Pine #2, 40 psf LL, no cantilever
# {joist_size: {spacing_in: max_span_ft_decimal}}
# Spans rounded down to nearest 0.1 ft for safety

DECK_JOIST_SPANS: dict[str, dict[int, float]] = {
    "2x6":  {12: 9.9,  16: 9.0,  24: 7.6},
    "2x8":  {12: 13.1, 16: 11.8, 24: 9.7},
    "2x10": {12: 16.2, 16: 14.0, 24: 11.4},
    "2x12": {12: 18.0, 16: 16.5, 24: 13.5},
}

# Maximum deck joist cantilever (IRC R507.6 Table footnote d) — Southern Pine #2
# keyed by joist_size, values in inches, 40 psf LL, backspan >= 3× cantilever
DECK_JOIST_CANTILEVER: dict[str, float] = {
    "2x6":  12.0,
    "2x8":  24.0,
    "2x10": 40.0,
    "2x12": 48.0,
}

# ── Floor joist spans — IRC Table R502.3.1(2) ────────────────────────────────
# Living areas, 40 psf LL, 10 psf DL
# Southern Pine #2 and Spruce-Pine-Fir #2 columns combined (conservative/SYP #2)

FLOOR_JOIST_SPANS: dict[str, dict[int, float]] = {
    "2x6":  {12: 11.4, 16: 10.4, 19: 9.9,  24: 9.0},
    "2x8":  {12: 15.0, 16: 13.7, 19: 12.9, 24: 11.8},
    "2x10": {12: 19.2, 16: 17.5, 19: 16.5, 24: 15.1},
    "2x12": {12: 23.3, 16: 21.2, 19: 20.0, 24: 18.4},
}

# ── Deck beam spans — IRC Table R507.5(1)  ───────────────────────────────────
# Southern Pine #2, 40 psf LL, Dead = 10 psf
# {beam_spec: {joist_span_ft(nominal): max_beam_span_ft}}
# beam_spec examples: "1-2x8", "2-2x10", "3-2x12"
# joist_span keys are the effective deck joist span (use nearest ≥ key)

DECK_BEAM_SPANS: dict[str, dict[int, float]] = {
    "1-2x6":  {6: 5.6,  8: 4.9,  10: 4.4, 12: 4.0, 14: 3.7, 16: 3.4},
    "1-2x8":  {6: 7.2,  8: 6.2,  10: 5.6, 12: 5.1, 14: 4.7, 16: 4.4},
    "1-2x10": {6: 8.8,  8: 7.6,  10: 6.9, 12: 6.3, 14: 5.8, 16: 5.4},
    "1-2x12": {6: 10.2, 8: 8.9,  10: 7.9, 12: 7.3, 14: 6.8, 16: 6.3},
    "2-2x8":  {6: 11.4, 8: 10.0, 10: 9.1, 12: 8.4, 14: 7.7, 16: 7.2},
    "2-2x10": {6: 14.3, 8: 12.4, 10: 11.1,12: 10.2,14: 9.5, 16: 8.9},
    "2-2x12": {6: 16.8, 8: 14.6, 10: 13.1,12: 12.0,14: 11.2,16: 10.4},
    "3-2x8":  {6: 14.2, 8: 12.5, 10: 11.4,12: 10.5,14: 9.7, 16: 9.1},
    "3-2x10": {6: 18.1, 8: 15.7, 10: 14.2,12: 13.0,14: 12.1,16: 11.3},
    "3-2x12": {6: 21.2, 8: 18.4, 10: 16.6,12: 15.2,14: 14.1,16: 13.2},
}

# ── Rafter spans — IRC Table R802.4.1  ───────────────────────────────────────
# Southern Pine #2, 20 psf ground snow, 10 psf DL, ceiling NOT attached (L/Δ=180)
# {rafter_size: {spacing_in: max_rafter_span_ft_horizontal}}

RAFTER_SPANS: dict[str, dict[int, float]] = {
    "2x4":  {12: 10.3, 16: 9.0,  19: 8.3,  24: 7.6},
    "2x6":  {12: 15.6, 16: 13.6, 19: 12.6, 24: 11.2},
    "2x8":  {12: 19.8, 16: 17.1, 19: 15.7, 24: 14.2},
    "2x10": {12: 23.5, 16: 20.3, 19: 18.5, 24: 16.9},
    "2x12": {12: 26.0, 16: 24.0, 19: 22.0, 24: 20.0},  # Note b capped at 26
}

# ── Footing sizes — IRC Table R507.3.1  ──────────────────────────────────────
# 1500 psf soil bearing, 40 psf live + snow load
# Minimum ROUND footing diameter in inches by tributary area (ft²)
# (tributary area = supported deck area per post)

FOOTING_DIA_BY_TRIB: list[tuple[float, int]] = [
    (20,  8),
    (40,  12),
    (60,  14),
    (80,  16),
    (100, 18),
    (120, 20),
    (140, 22),
    (160, 24),
    (180, 26),
    (200, 28),
]

# ── Post max heights — IRC Table R507.4  ─────────────────────────────────────
# Measured from underside of beam to top of footing

POST_MAX_HEIGHTS: dict[str, float] = {
    "4x4": 8.0,
    "4x6": 8.0,
    "6x6": 14.0,
    "8x8": 14.0,
}

# ── Header sizes — IRC R602.7 (load-bearing, 1-story)  ───────────────────────
# {max_opening_width_in: header_size}
HEADER_SIZES: list[tuple[int, str]] = [
    (48,  "2x6"),
    (72,  "2x8"),
    (96,  "2x10"),
    (144, "2x12"),
]

# ── Lumber actual dimensions (nominal → actual in inches)  ───────────────────
NOMINAL_TO_ACTUAL: dict[str, tuple[float, float]] = {
    "2x4":  (1.5, 3.5),
    "2x6":  (1.5, 5.5),
    "2x8":  (1.5, 7.25),
    "2x10": (1.5, 9.25),
    "2x12": (1.5, 11.25),
    "4x4":  (3.5, 3.5),
    "4x6":  (3.5, 5.5),
    "6x6":  (5.5, 5.5),
    "8x8":  (7.5, 7.5),
}


# ── Lookup helpers ─────────────────────────────────────────────────────────────

def _nearest_spacing(table: dict[int, float], spacing_in: float) -> int:
    """Return the largest key in *table* that is ≤ *spacing_in*, else smallest."""
    candidates = [k for k in table if k <= spacing_in]
    return max(candidates) if candidates else min(table)


def min_deck_joist(span_ft: float, spacing_in: float) -> str:
    """Return the smallest IRC-compliant deck joist size for span/spacing.
    Returns '2x12+' if span exceeds all table values."""
    for size in ("2x6", "2x8", "2x10", "2x12"):
        key = _nearest_spacing(DECK_JOIST_SPANS[size], spacing_in)
        if DECK_JOIST_SPANS[size][key] >= span_ft:
            return size
    return "2x12+"  # exceeds tables — engineer required


def min_floor_joist(span_ft: float, spacing_in: float) -> str:
    """Return the smallest IRC-compliant floor joist size for span/spacing."""
    for size in ("2x6", "2x8", "2x10", "2x12"):
        key = _nearest_spacing(FLOOR_JOIST_SPANS[size], spacing_in)
        if FLOOR_JOIST_SPANS[size][key] >= span_ft:
            return size
    return "2x12+"


def min_deck_beam(joist_span_ft: float, beam_span_ft: float) -> str:
    """Return smallest IRC-compliant deck beam spec for given joist/beam spans."""
    # Round joist span up to nearest table key
    joist_keys = (6, 8, 10, 12, 14, 16)
    eff_joist = next((k for k in joist_keys if k >= joist_span_ft), 16)

    for spec in (
        "1-2x6", "1-2x8", "1-2x10", "1-2x12",
        "2-2x8", "2-2x10", "2-2x12",
        "3-2x8", "3-2x10", "3-2x12",
    ):
        row = DECK_BEAM_SPANS[spec]
        if eff_joist in row and row[eff_joist] >= beam_span_ft:
            return spec
    return "3-2x12+"


def min_rafter(span_ft: float, spacing_in: float) -> str:
    """Return smallest IRC-compliant rafter size for given horizontal span/spacing."""
    for size in ("2x4", "2x6", "2x8", "2x10", "2x12"):
        key = _nearest_spacing(RAFTER_SPANS[size], spacing_in)
        if RAFTER_SPANS[size][key] >= span_ft:
            return size
    return "2x12+"


def min_footing_dia(trib_area_ft2: float) -> int:
    """Return minimum round footing diameter (inches) for given tributary area."""
    for area, dia in FOOTING_DIA_BY_TRIB:
        if trib_area_ft2 <= area:
            return dia
    return FOOTING_DIA_BY_TRIB[-1][1]  # max table value


def max_cantilever(joist_size: str) -> float:
    """Return IRC max cantilever length (inches) for a deck/floor joist.
    IRC R502.3.3: cantilever shall not exceed nominal depth of the joist."""
    _, depth = NOMINAL_TO_ACTUAL.get(joist_size, (1.5, 9.25))
    # round to nearest nominal inch for IRC interpretation
    return depth


def blocking_rows_required(span_in: float) -> int:
    """Return number of mid-span blocking rows required.
    IRC R502.7: lateral restraint always at ends (0 extra rows for short spans).
    IRC R502.7.1: bridging required for 2×12+ at 8-ft intervals.
    Deck/floor practice: 1 mid-span row if span > 8 ft; 2 rows if span > 16 ft."""
    span_ft = span_in / 12.0
    if span_ft <= 8.0:
        return 0
    if span_ft <= 16.0:
        return 1
    return 2


def header_size(opening_width_in: float) -> str:
    """Return IRC R602.7 header size for a load-bearing opening."""
    for max_w, size in HEADER_SIZES:
        if opening_width_in <= max_w:
            return size
    return "engineered"  # > 12 ft — requires engineering


def max_rafter_overhang(rafter_size: str, pitch: int) -> float:
    """IRC R802.7.1.1: cantilevered rafter notch limit 24 in max overhang.
    Returns max allowed overhang in inches."""
    return 24.0   # IRC absolute max for code-compliant notched overhang
    # Note: unnotched overhang can exceed 24" with engineer approval.
    # App allows 12–96" range; values > 24" flagged as "verify with engineer".


def rafter_length(half_span_ft: float, pitch: int, overhang_in: float) -> float:
    """Calculate sloped rafter length in feet.
    half_span_ft : horizontal run from plate to ridge
    pitch        : rise-per-12 (e.g. 4 for 4:12)
    overhang_in  : horizontal overhang beyond outer wall (inches)
    Returns actual sloped rafter length in feet."""
    import math
    slope_factor = math.sqrt(1 + (pitch / 12.0) ** 2)
    run_ft = half_span_ft + overhang_in / 12.0
    return run_ft * slope_factor


def footing_depth_required(frost_depth_in: int = 24) -> int:
    """IRC R507.3.2: footings shall extend below frost line.
    Returns required footing depth in inches."""
    return max(frost_depth_in, 12)   # min 12" even in warm climates
