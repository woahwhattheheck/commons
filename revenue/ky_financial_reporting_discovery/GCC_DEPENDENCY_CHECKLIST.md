# Government cloud and deployment dependency checklist

The source package asks vendors to identify Microsoft Government Community Cloud compatibility, limitations, and dependencies. This carrier does not claim a certification or deployed GCC implementation. It provides questions and boundaries that must be answered for any selected reporting stack.

## Identity and access

- Which identity provider and tenant are authoritative?
- Which reporting components require GCC-specific service endpoints?
- Are role assignments derived from existing Commonwealth groups, application roles, data attributes, or a combination?
- How are privileged administration and break-glass access separated from ordinary report access?
- Can access decisions be exported for review and retained with a report-generation event?

## Data path

- Which components read directly from Oracle, which read a governed warehouse/replica, and which use extracts?
- Where can cached report data exist?
- Which services may store query results, semantic models, exports, schedules, or credentials?
- Are any components outside the approved cloud boundary?
- What controls prevent a self-service feature from bypassing row/object access rules?

## Service compatibility

For every proposed product or managed service, record:

- exact product/SKU and deployment model;
- GCC availability;
- feature differences from commercial cloud;
- API/connector differences;
- identity integration dependencies;
- network/private-endpoint requirements;
- logging/export limitations;
- update/support cadence;
- any feature that requires a non-GCC dependency.

Unsupported or unknown items remain explicit holds.

## Evidence

A deployment decision should retain:

- architecture generation;
- product/version/SKU evidence;
- connectivity and identity assumptions;
- service-boundary diagram;
- access-policy mapping;
- logging and export plan;
- test results for representative roles;
- unresolved limitations and their owners.

The included migration method treats platform choice and buyer acceptance as external authority. Engineering evidence can show how to test a boundary; it cannot certify the boundary by assertion.
