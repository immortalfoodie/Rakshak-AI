"""Shared paths and constants for the integration layer."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SAMPLE = SHARED / "sample_data"
SCHEMAS = SHARED / "schemas"
HISTORICAL = SAMPLE / "historical_events"

# Geo coordinates for corridor regions
CORRIDORS = {
    "hormuz": {"lat": 26.56, "lon": 56.25, "zoom": 7, "label": "Strait of Hormuz"},
    "red_sea": {"lat": 14.0, "lon": 42.5, "zoom": 6, "label": "Red Sea / Bab el-Mandeb"},
    "iran_exports": {"lat": 27.1, "lon": 56.0, "zoom": 7, "label": "Iran Export Terminals"},
}

# Mock AIS vessel positions near Hormuz/Red Sea
MOCK_VESSELS = [
    {"name": "MT Desh Shanti", "lat": 26.2, "lon": 56.4, "type": "VLCC", "status": "Transiting"},
    {"name": "MT Jag Lakshya", "lat": 26.0, "lon": 56.6, "type": "Suezmax", "status": "Anchored"},
    {"name": "MT New Diamond", "lat": 25.8, "lon": 56.3, "type": "VLCC", "status": "Transiting"},
    {"name": "MT Desh Garima", "lat": 14.5, "lon": 42.8, "type": "Aframax", "status": "Transiting"},
    {"name": "MT Kerala", "lat": 13.8, "lon": 43.2, "type": "VLCC", "status": "Waiting"},
    {"name": "MT Maharshi Valmiki", "lat": 25.5, "lon": 57.0, "type": "Suezmax", "status": "Dark(AIS off)"},
]

# Route waypoints for Layer 3 recommendations
ROUTE_COORDS = {
    "Basra -> Vadinar via Arabian Sea (non-Hormuz)": [
        [30.5, 47.8], [28.0, 50.5], [25.0, 57.0], [22.0, 60.0], [20.5, 69.5]
    ],
    "Basra -> Vadinar via Arabian Sea": [
        [30.5, 47.8], [28.0, 50.5], [25.0, 57.0], [22.0, 60.0], [20.5, 69.5]
    ],
    "Bonny -> Jamnagar via Cape of Good Hope": [
        [4.4, 7.0], [0.0, 5.0], [-6.0, 8.0], [-34.0, 18.5], [-35.0, 25.0],
        [-30.0, 35.0], [-15.0, 45.0], [5.0, 55.0], [15.0, 65.0], [22.3, 70.0]
    ],
    "Houston -> Paradip via Cape of Good Hope": [
        [29.7, -95.0], [25.0, -85.0], [15.0, -60.0], [5.0, -30.0],
        [-10.0, -5.0], [-34.0, 18.5], [-25.0, 40.0], [-10.0, 55.0],
        [5.0, 65.0], [15.0, 75.0], [20.3, 86.7]
    ],
    "Fujairah -> Mumbai High via Arabian Sea": [
        [25.1, 56.3], [24.0, 58.0], [22.0, 63.0], [19.0, 72.8]
    ],
    "Fujairah -> Mangalore via Arabian Sea": [
        [25.1, 56.3], [22.0, 60.0], [18.0, 65.0], [12.9, 74.8]
    ],
    "Ras Tanura -> Mumbai High via Arabian Sea": [
        [26.6, 50.1], [25.0, 54.0], [23.0, 58.0], [20.0, 65.0], [19.0, 72.8]
    ],
    "Novorossiysk -> Paradip via Suez Canal": [
        [44.7, 37.8], [41.0, 29.0], [37.0, 26.0], [31.0, 32.3],
        [27.0, 34.0], [15.0, 42.0], [12.0, 50.0], [10.0, 60.0],
        [12.0, 70.0], [15.0, 78.0], [20.3, 86.7]
    ],
    "Georgetown -> Paradip via Cape of Good Hope": [
        [6.8, -58.1], [0.0, -30.0], [-15.0, -5.0], [-34.0, 18.5],
        [-25.0, 40.0], [-10.0, 55.0], [5.0, 65.0], [15.0, 78.0], [20.3, 86.7]
    ],
}

ROUTE_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]
