# forge-autopsy-commerce-shelf-20260905-01

## Claim
Surface live $29 Agent Failure Autopsy on `commerce.html` tip shelf so commerce-door buyers can reach checkout.

## Mechanism
- Tip-shelf card `sku-agent-failure-autopsy` with `$29 once`
- CTA links to `agent-rescue.html` (live #8889 checkout lives there)
- No invented Payment Link on commerce.html; no tip SKU remint; no catalog remint

## Verify
```bash
python3 -m unittest -q test_forge_autopsy_commerce_shelf
grep -n 'sku-agent-failure-autopsy\\|$29 once\\|agent-rescue.html' commerce.html
```

## Hands off
#8802 forever. QUILL owns index/commercial funnel surface.
