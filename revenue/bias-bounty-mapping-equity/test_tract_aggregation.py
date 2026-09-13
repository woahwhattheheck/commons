import pytest
import json
import hashlib
from pathlib import Path
from tract_aggregation_runner import validate_receipt, load_receipt

def test_geoid_custody():
    receipt = load_receipt()
    assert set(receipt['regions']) == {'eastern-ok', 'maricopa-az', 'northern-ca', 'south-central-tx'}
    assert receipt['row_counts'] == {'eastern-ok': 1192, 'maricopa-az': 1593, 'northern-ca': 591, 'south-central-tx': 6003}

def test_exact_region_set():
    receipt = load_receipt()
    assert len(receipt['regions']) == 4
    for region in receipt['regions']:
        assert receipt['metadata'][region]['crs'] == 'OGC:CRS84'
        assert receipt['metadata'][region]['projection'] == 'EPSG:5070'

def test_category_road_filters():
    receipt = load_receipt()
    assert receipt['filters']['overture_road_classes'] == ['motorway', 'trunk', 'primary', 'secondary']
    assert receipt['filters']['tiger_road_classes'] == ['S1100', 'S1200']
    poi = receipt['filters']['poi_categories']
    assert 'fire_department' in poi['fire']
    assert 'ambulance_and_ems_services' in poi['ems']

def test_undefined_zero_semantics():
    receipt = load_receipt()
    assert receipt['undefined_zero_reference'] is True
    assert 'reference_score_column' not in receipt
    assert 'provider_submission' not in receipt

def test_deterministic_ordering():
    receipt = load_receipt()
    assert receipt['geoid_ordering'] == 'text_11digit_ascending'
    assert receipt['output_digest_algorithm'] == 'sha256'

def test_leakage_rejection():
    receipt = load_receipt()
    assert receipt['no_reference_score_column'] is True
    assert receipt['no_provider_submission'] is True

def test_receipt_tamper_detection():
    receipt = load_receipt()
    assert validate_receipt(receipt) is True
    receipt_copy = receipt.copy()
    receipt_copy['row_counts']['eastern-ok'] = 9999
    assert validate_receipt(receipt_copy) is False
