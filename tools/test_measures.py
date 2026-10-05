#!/usr/bin/env python3
"""Test measures.json generation: air quality, pollen, UV, river level, water restrictions."""
import json, sys, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

assert os.path.exists("measures.json"), "measures.json should exist"

with open("measures.json") as f:
    data = json.load(f)
    assert "measures" in data, "measures.json should have 'measures' key"
    assert "generated_at" in data, "measures.json should have 'generated_at' key"
    assert isinstance(data["measures"], list), "measures should be a list"
    assert len(data["measures"]) >= 5, f"measures.json should have >=5 measures, got {len(data['measures'])}"
    
    keys_to_check = ["k", "l", "v", "ok", "d", "src"]
    for m in data["measures"]:
        for k in keys_to_check:
            assert k in m, f"Measure {m.get('k')} missing key '{k}'"
        assert isinstance(m["k"], str), f"Measure key should be string"
        assert isinstance(m["l"], str), f"Measure label should be string"
        assert isinstance(m["v"], str), f"Measure value should be string"
        assert m["ok"] is None or isinstance(m["ok"], bool), f"Measure ok should be None or bool"
    
    measure_keys = {m["k"] for m in data["measures"]}
    required = {"air", "pollen", "uv", "river", "water"}
    assert required <= measure_keys, f"Missing required measures: {required - measure_keys}"
    
    water_measure = next((m for m in data["measures"] if m["k"] == "water"), None)
    assert water_measure is not None, "Water measure should exist"
    assert "water" in water_measure.get("d", "").lower() or "restriction" in water_measure.get("d", "").lower(), \
        f"Water measure description should mention water or restrictions, got: {water_measure.get('d')}"
    
    pollen_measure = next((m for m in data["measures"] if m["k"] == "pollen"], None)
    assert pollen_measure is not None, "Pollen measure should exist"
    assert "UKHSA" in pollen_measure.get("src", ""), f"Pollen should be from UKHSA, got: {pollen_measure.get('src')}"
    
    print(f"✓ measures.json valid: {len(data['measures'])} measures, keys: {', '.join(sorted(measure_keys))}")
    print("✓ All 15 measures tests passed (structure, sources, water restrictions, UKHSA pollen)")
