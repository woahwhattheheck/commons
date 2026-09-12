# S3 SE-land donor custody

Canonical preservation of the reviewed default-OFF S3 lane from closed PR #12592. The historical mechanism appends one `BUY_LAND` only when NE+SW are already owned, cash covers SE plus reserve, order capacity remains, timing/demand/V219 guards pass, and the SE purchase can be handed to the separate SE operator without perturbing shop-unlock RNG.

Exact authorities preserved here:
- historical head: `fa8cdfdaf7163041e300a902e2430963da099b21`
- helper/source blob: `9c17c8ccc197d12383d29bba717016435a4a863f`
- focused test blob: `beb896b6e39e2d9e12608c97533ed57583725a00`
- historical gate: 291 package checks, 26 focused S3 checks; key shipped OFF.

Important composition boundary: S3 was explicitly gated together with the SE operator/S1+S2 herd. This package is source/evidence custody only. It does not execute the legacy materializer, wire the current production ABI, enable `r04_s3_land`, buy land in production, alter Kaggle/submission artifacts, or create a successor V4 ref.