import json
import os
import sys
from pathlib import Path

import jsonschema
import pytest

# Ensure we can import from the layer1-watch directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SCHEMA_PATH
from scoring.fuser import build_sub_scores, fuse

def test_schema_loads():
    """Verify the shared schema file exists and is valid JSON."""
    assert SCHEMA_PATH.exists(), f"Schema file not found at {SCHEMA_PATH}"
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    assert "properties" in schema
    assert "required" in schema


def test_valid_output_schema():
    """Verify a synthetically generated output passes schema validation."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    # Build a valid synthetic output
    sub_scores = build_sub_scores(
        news_sentiment=85.5,
        sanctions_delta=100.0,
        prediction_market=None,
    )
    overall_score, alert_level = fuse(sub_scores)

    output = {
        "corridor": "hormuz",
        "timestamp": "2026-07-18T12:00:00Z",
        "score": overall_score,
        "alert_level": alert_level,
        "sub_scores": sub_scores,
        "evidence": [
            {
                "source": "GDELT",
                "summary": "Sample news event",
                "url": "https://example.com",
                "timestamp": "2026-07-18T11:55:00Z",
            }
        ],
    }

    # Should not raise an exception
    jsonschema.validate(instance=output, schema=schema)


def test_missing_required_field():
    """Verify validation fails if a required field is missing."""
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    output = {
        "corridor": "hormuz",
        "timestamp": "2026-07-18T12:00:00Z",
        # "score": 50.0,  # missing required field
        "alert_level": "medium",
        "sub_scores": build_sub_scores(50, 50, 50),
        "evidence": [],
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=output, schema=schema)
