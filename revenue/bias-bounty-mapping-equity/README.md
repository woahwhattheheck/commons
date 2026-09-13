# Mapping Equity Tract Aggregation

Deterministic DuckDB runner for four Source Cooperative regions.

## Regions
- eastern-ok (1,192 tracts)
- maricopa-az (1,593 tracts)
- northern-ca (591 tracts)
- south-central-tx (6,003 tracts)

## Methodology
- Roads: Overture (motorway/trunk/primary/secondary) vs TIGER (S1100/S1200)
- Length: EPSG:5070 metric, CRS84 source with always_xy=true
- Buildings: Overture vs Microsoft footprints
- POI: fire/EMS/schools categories per specification
- Business: Overture places vs cbp_estab (HUD USPS)

## Run