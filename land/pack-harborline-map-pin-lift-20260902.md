# Land — Harborline map pin-lift

Leftover Harborline map/pointer helpers observe TALLY and LotRibbon blobs
at land time. They do not freeze those files live. TALLY can land the
sold-once badge. After that helper is on main, Harborline can run
`--write` on its own door.

```bash
python3 -m unittest \
  test_business_pack_harborline_tally_map.py \
  test_business_pack_harborline_tally_map_pointer.py \
  test_business_pack_harborline_map_helper_pointer.py \
  test_pack_harborline_map_pin_lift.py
```

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP.
