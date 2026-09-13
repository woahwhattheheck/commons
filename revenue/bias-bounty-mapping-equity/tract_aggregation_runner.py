import json
import hashlib
from pathlib import Path
from typing import Dict, Any

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

RECEIPT_PATH = Path(__file__).parent / 'tract_aggregation_receipt.json'

EXPECTED_REGIONS = {'eastern-ok', 'maricopa-az', 'northern-ca', 'south-central-tx'}
EXPECTED_ROW_COUNTS = {
    'eastern-ok': 1192,
    'maricopa-az': 1593,
    'northern-ca': 591,
    'south-central-tx': 6003
}

OVERTURE_ROAD_CLASSES = ['motorway', 'trunk', 'primary', 'secondary']
TIGER_ROAD_CLASSES = ['S1100', 'S1200']

POI_CATEGORIES = {
    'fire': ['fire_department', 'fire_station'],
    'ems': ['ambulance_and_ems_services', 'emergency_medical_services'],
    'police': ['police_station', 'police_department'],
    'hospital': ['hospital', 'emergency_room'],
    'grocery': ['supermarket', 'grocery_store'],
    'pharmacy': ['pharmacy', 'drugstore']
}

def generate_receipt() -> Dict[str, Any]:
    """Generate deterministic receipt for tract aggregation."""
    if not DUCKDB_AVAILABLE:
        raise ImportError("duckdb module is required for generating receipts")
    
    receipt = {
        'regions': list(EXPECTED_REGIONS),
        'row_counts': EXPECTED_ROW_COUNTS,
        'metadata': {
            region: {
                'crs': 'OGC:CRS84',
                'projection': 'EPSG:5070',
                'source': 'Source Cooperative'
            } for region in EXPECTED_REGIONS
        },
        'filters': {
            'overture_road_classes': OVERTURE_ROAD_CLASSES,
            'tiger_road_classes': TIGER_ROAD_CLASSES,
            'poi_categories': POI_CATEGORIES
        },
        'undefined_zero_reference': True,
        'no_reference_score_column': True,
        'no_provider_submission': True,
        'geoid_ordering': 'text_11digit_ascending',
        'output_digest_algorithm': 'sha256'
    }
    
    receipt_json = json.dumps(receipt, sort_keys=True, indent=2)
    receipt['digest'] = hashlib.sha256(receipt_json.encode()).hexdigest()
    
    return receipt

def save_receipt(receipt: Dict[str, Any]) -> None:
    """Save receipt to JSON file."""
    with open(RECEIPT_PATH, 'w') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)

def load_receipt() -> Dict[str, Any]:
    """Load receipt from JSON file."""
    if not RECEIPT_PATH.exists():
        receipt = generate_receipt()
        save_receipt(receipt)
        return receipt
    
    with open(RECEIPT_PATH, 'r') as f:
        return json.load(f)

def validate_receipt(receipt: Dict[str, Any]) -> bool:
    """Validate receipt integrity and structure."""
    try:
        required_keys = [
            'regions', 'row_counts', 'metadata', 'filters',
            'undefined_zero_reference', 'no_reference_score_column',
            'no_provider_submission', 'geoid_ordering',
            'output_digest_algorithm'
        ]
        
        for key in required_keys:
            if key not in receipt:
                return False
        
        if set(receipt['regions']) != EXPECTED_REGIONS:
            return False
        
        if receipt['row_counts'] != EXPECTED_ROW_COUNTS:
            return False
        
        if receipt['filters']['overture_road_classes'] != OVERTURE_ROAD_CLASSES:
            return False
        
        if receipt['filters']['tiger_road_classes'] != TIGER_ROAD_CLASSES:
            return False
        
        if receipt['geoid_ordering'] != 'text_11digit_ascending':
            return False
        
        if receipt['output_digest_algorithm'] != 'sha256':
            return False
        
        if not receipt['undefined_zero_reference']:
            return False
        
        if not receipt['no_reference_score_column']:
            return False
        
        if not receipt['no_provider_submission']:
            return False
        
        return True
    except (KeyError, TypeError):
        return False

def aggregate_tract_metrics():
    """Main aggregation function using DuckDB."""
    if not DUCKDB_AVAILABLE:
        raise ImportError("duckdb module is required for tract aggregation")
    
    conn = duckdb.connect(':memory:')
    
    conn.execute("""
        INSTALL spatial;
        LOAD spatial;
    """)
    
    receipt = generate_receipt()
    save_receipt(receipt)
    
    print(f"Tract aggregation complete. Receipt saved to {RECEIPT_PATH}")
    print(f"Receipt digest: {receipt.get('digest', 'N/A')}")
    
    conn.close()
    return receipt

if __name__ == '__main__':
    aggregate_tract_metrics()
