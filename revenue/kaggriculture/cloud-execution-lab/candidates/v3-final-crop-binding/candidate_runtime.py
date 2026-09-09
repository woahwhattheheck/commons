# SPDX-License-Identifier: Apache-2.0
"""Final-action binding candidate for the current TITAN crop-recovery queue."""
from __future__ import annotations

from copy import deepcopy

from titan_runtime import TitanAgent


_CROP_QUEUE_OWNER = "crop_input_repair_owns_current_queue"


class FinalCropBindingAgent(TitanAgent):
    """Canonical TITAN with receipt-critical crop repair bound at return time.

    A live crop input repair owns the current market queue for one decision.
    Optional late reordering is useful on ordinary rows, but it must not move an
    appended WHEAT buy or a WHEAT-sale reservation after the repair proposal has
    frozen exact order indices for the shared fill ledger.
    """

    def _market_pressure_selected(self, obs, cfg, selected):
        """Retain the canonical final-pressure boundary outside crop repair."""
        if not getattr(self, "_final_pressure_boundary", False):
            return selected
        return super()._market_pressure_selected(obs, cfg, selected)

    def _crop_repair_owns_market(self) -> bool:
        spatial = getattr(self, "spatial", None)
        return spatial is not None and getattr(spatial, "_crop_repair", None) is not None

    def _early_capital_selected(self, obs, cfg, selected):
        """Compose capital/pressure only when no crop receipt owns this queue."""
        if self._crop_repair_owns_market():
            diagnostics = getattr(self, "diagnostics", None)
            if isinstance(diagnostics, dict):
                diagnostics["early_capital"] = {
                    "changed": False,
                    "reason": _CROP_QUEUE_OWNER,
                }
                if getattr(getattr(self, "features", None), "market_pressure", False):
                    diagnostics["market_pressure"] = {
                        "enabled": True,
                        "changed": False,
                        "reason": _CROP_QUEUE_OWNER,
                    }
            return selected

        returned = super()._early_capital_selected(obs, cfg, selected)
        if getattr(self, "diagnostics", {}).get("status") != "completed":
            return returned
        self._final_pressure_boundary = True
        try:
            return super()._market_pressure_selected(obs, cfg, returned)
        finally:
            self._final_pressure_boundary = False

    def _finish_production(self, obs, returned, cfg=None):
        """Apply every market mutator before the crop proposal's binding guard."""
        if self.spatial is not None:
            self.spatial.observe_crop_receipts(
                obs,
                None if self.history is None else self.history.fill_result,
                self.controller.cur,
            )
        if self.spatial is not None:
            returned = self.spatial.guard_returned(
                obs,
                returned,
                repair_fallback=self.diagnostics.get("status") == "deadline_fallback",
            )
        post = self._selected_snapshot(obs, returned) if self.history is not None else None

        # These are the last market-edit seams. A receipt-critical crop repair
        # makes them identities for this action; ordinary actions retain the
        # canonical feed -> capital -> final-pressure composition.
        returned = self._feed_stock_selected(obs, cfg or {}, returned)
        returned = self._early_capital_selected(obs, cfg or {}, returned)

        # Bind against the exact action that can now be returned and recorded.
        # No later method in this finalizer is allowed to mutate the market.
        if self.spatial is not None:
            returned = self.spatial.guard_crop_returned(obs, returned, post)

        if self.quadrant is not None:
            self.quadrant.finish(obs, returned)
            self.diagnostics["fourth_quadrant_events"] = list(self.quadrant.events)
            if self._quadrant_admission is not None:
                self.diagnostics["fourth_quadrant_admission"] = deepcopy(
                    self._quadrant_admission.last_report
                )
        if self.spatial is not None:
            self.spatial.finish(obs, returned, post)
            self.spatial.finish_crop(
                obs,
                returned,
                post,
                self.controller.cur,
                seller_completed=self.diagnostics.get("status") == "completed",
            )
            self.diagnostics["route_events"] = list(self.spatial.events)
            self.diagnostics["idle_fertilizer_receipts"] = list(
                self.spatial.receipt_events
            )
            self.diagnostics["idle_fertilizer_obligation"] = deepcopy(
                self.spatial.sale_obligation
            )
            if self.features.crop_release:
                self.diagnostics["crop_release"] = deepcopy(self.spatial.crop_intent)
                self.diagnostics["crop_release_action"] = deepcopy(
                    self.spatial.crop_report
                )
        if self.history is not None:
            needed = (
                self.features.terminal_history
                or (
                    self.spatial is not None
                    and (
                        self.spatial.sale_obligation is not None
                        or self.spatial.crop_intent is not None
                    )
                )
            )
            self.history.remember(
                obs,
                cfg or {},
                returned,
                post if needed else None,
            )
            self.diagnostics["history"] = self.history.diagnostics
        return returned
