# SPDX-License-Identifier: Apache-2.0
"""Final-action binding candidate for the current TITAN crop-recovery queue."""
from __future__ import annotations

from copy import deepcopy

from titan_runtime import TitanAgent


_CROP_QUEUE_OWNER = "crop_input_repair_owns_current_queue"


class FinalCropBindingAgent(TitanAgent):
    """Canonical TITAN with receipt-critical crop repair bound at return time.

    A crop proposal owns one returned market queue only after the fallback/idle
    guard and selected post-unit snapshot still bind that exact proposal. A
    stale timed-stage proposal is detached before every late market transform,
    then restored only for fail-closed receipt classification.
    """

    def _market_pressure_selected(self, obs, cfg, selected):
        """Retain the canonical final-pressure boundary outside crop repair."""
        if not getattr(self, "_final_pressure_boundary", False):
            return selected
        return super()._market_pressure_selected(obs, cfg, selected)

    @staticmethod
    def _proposal_bound(proposal, obs, returned, post) -> bool:
        """Mirror the canonical crop guard's exact action/snapshot binding."""
        if proposal is None:
            return False
        from crop_release import units

        try:
            return (
                int(obs["step"]) == proposal["step"]
                and int(obs["player"]) == proposal["player"]
                and units(returned) == proposal["unit_binding"]
                and post is not None
                and int(post["step"]) == proposal["step"]
                and int(post["player"]) == proposal["player"]
                and returned.get("market", []) == proposal["expected_market"]
            )
        except (KeyError, TypeError, ValueError):
            return False

    def _crop_repair_still_bound(self, obs, returned, post) -> bool:
        """True only when the live proposal binds the post-guard action."""
        spatial = getattr(self, "spatial", None)
        proposal = None if spatial is None else getattr(spatial, "_crop_repair", None)
        return self._proposal_bound(proposal, obs, returned, post)

    def _crop_repair_owns_market(self) -> bool:
        """Use validated per-action ownership, never mere proposal existence."""
        return bool(getattr(self, "_crop_repair_live", False))

    @staticmethod
    def _repair_residue(proposal, returned) -> bool:
        """Match commit_input_repair's ambiguous-effect screen."""
        if proposal is None:
            return False
        market = returned.get("market", [])
        try:
            if proposal["kind"] == "buy":
                return any(
                    row
                    and len(row) > 2
                    and row[:2] == ["BUY_PRODUCT", "WHEAT"]
                    and row[2] > 0
                    for row in market[:10]
                )
            if proposal["kind"] == "withhold":
                inherited = proposal["inherited_market"]
                return any(
                    market[slot : slot + 1] != inherited[slot : slot + 1]
                    for slot in proposal["original_sale_slots"]
                )
        except (KeyError, TypeError, ValueError):
            return True
        return True

    def _retire_unbound_crop_repair(self, obs, returned, post):
        """Cancel recognizable effects, detach proposal, preserve its receipt check."""
        spatial = getattr(self, "spatial", None)
        proposal = None if spatial is None else getattr(spatial, "_crop_repair", None)
        if proposal is None:
            return returned, None, False

        before = returned
        returned = spatial.guard_crop_returned(obs, returned, post)
        residue = self._repair_residue(proposal, returned)
        if returned is before:
            spatial.crop_report = {
                "changed": False,
                "reason": "pre_transform_unbound_repair_retired",
                "repair_residue": residue,
            }
        spatial._crop_repair = None
        self._crop_repair_live = False
        return returned, proposal, residue

    def _early_capital_selected(self, obs, cfg, selected):
        """Compose capital/pressure only when the exact repair owns this queue."""
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

    def _feed_stock_selected(self, obs, cfg, selected):
        """Apply feed-stock unless an exact live crop repair owns this queue."""
        if self._crop_repair_owns_market():
            diagnostics = getattr(self, "diagnostics", None)
            if isinstance(diagnostics, dict):
                diagnostics["feed_stock"] = {
                    "changed": False,
                    "certified": False,
                    "reason": _CROP_QUEUE_OWNER,
                }
            return selected
        return super()._feed_stock_selected(obs, cfg, selected)

    def _finish_production(self, obs, returned, cfg=None):
        """Validate ownership, finish market edits, then bind the final action."""
        self._crop_repair_live = False
        if self.spatial is not None:
            self.spatial.observe_crop_receipts(
                obs,
                None if self.history is None else self.history.fill_result,
                self.controller.cur,
            )
            returned = self.spatial.guard_returned(
                obs,
                returned,
                repair_fallback=self.diagnostics.get("status") == "deadline_fallback",
            )

        post = self._selected_snapshot(obs, returned) if self.history is not None else None
        proposal = (
            None if self.spatial is None else getattr(self.spatial, "_crop_repair", None)
        )
        retired_proposal = None
        residue = False
        if proposal is not None:
            if self._proposal_bound(proposal, obs, returned, post):
                self._crop_repair_live = True
            else:
                returned, retired_proposal, residue = (
                    self._retire_unbound_crop_repair(obs, returned, post)
                )

        self.diagnostics["crop_repair_binding"] = {
            "proposal": proposal is not None,
            "bound_after_return_guard": self._crop_repair_live,
            "retired_before_late_market": retired_proposal is not None,
            "repair_residue_after_retirement": residue,
        }

        # Detaching an unbound proposal releases both the validated candidate
        # ownership checks and TitanAgent._feed_stock_selected's raw-proposal
        # veto. Exact owners preserve the queue byte-for-byte.
        try:
            returned = self._feed_stock_selected(obs, cfg or {}, returned)
            returned = self._early_capital_selected(obs, cfg or {}, returned)

            # No method after this point may mutate the market. Exact owners are
            # checked against the true final queue; detached proposals are an
            # identity here and return only for fail-closed receipt accounting.
            if self.spatial is not None:
                returned = self.spatial.guard_crop_returned(obs, returned, post)
        except BaseException:
            if retired_proposal is not None:
                self.spatial._crop_repair = retired_proposal
            raise
        finally:
            self._crop_repair_live = False

        receipt_started = False
        try:
            if self.quadrant is not None:
                self.quadrant.finish(obs, returned)
                self.diagnostics["fourth_quadrant_events"] = list(self.quadrant.events)
                if self._quadrant_admission is not None:
                    self.diagnostics["fourth_quadrant_admission"] = deepcopy(
                        self._quadrant_admission.last_report
                    )
            if self.spatial is not None:
                self.spatial.finish(obs, returned, post)
                if retired_proposal is not None:
                    self.spatial._crop_repair = retired_proposal
                receipt_started = True
                try:
                    self.spatial.finish_crop(
                        obs,
                        returned,
                        post,
                        self.controller.cur,
                        seller_completed=self.diagnostics.get("status") == "completed",
                    )
                finally:
                    # Real SpatialTempo clears this itself. Keep test doubles and
                    # exceptional paths from leaking a retired proposal.
                    if (
                        retired_proposal is not None
                        and getattr(self.spatial, "_crop_repair", None)
                        is retired_proposal
                    ):
                        self.spatial._crop_repair = None
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
        except BaseException:
            if (
                retired_proposal is not None
                and not receipt_started
                and self.spatial is not None
                and getattr(self.spatial, "_crop_repair", None) is None
            ):
                self.spatial._crop_repair = retired_proposal
            raise

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
