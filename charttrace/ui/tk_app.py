"""Native Tk interface with a display-free headless mode for unit tests."""

from typing import Dict, Optional

import tkinter as tk
from tkinter import messagebox, ttk

from charttrace.app import BUILD_LABEL, ChartTraceController
from charttrace.legal import INSTRUMENTS

from .screens import LEGAL_ACTION_ID, SCREEN_CATALOG, ScreenDefinition, ScreenId


class ChartTraceWindow:
    def __init__(
        self,
        controller: Optional[ChartTraceController] = None,
        headless: bool = False,
    ):
        self.controller = controller or ChartTraceController()
        self.headless = headless
        self.current_screen = ScreenId.UNLOCK
        self.root: Optional[tk.Tk] = None
        self._content: Optional[ttk.Frame] = None
        self._nav_buttons: Dict[ScreenId, ttk.Button] = {}
        self._ack_vars: Dict[str, tk.BooleanVar] = {}
        self._status_var: Optional[tk.StringVar] = None
        self.legal_button: Optional[ttk.Button] = None

        if not headless:
            self._build_native_window()

    def screen_snapshot(self, screen_id: ScreenId) -> dict:
        """Describe a screen without creating any display resources."""
        definition = SCREEN_CATALOG[screen_id]
        return {
            "screen_id": definition.screen_id.value,
            "title": definition.title,
            "summary": definition.summary,
            "deadline_banner": definition.deadline_banner,
            "persistent_actions": list(definition.persistent_actions),
            "has_legal_button": definition.has_legal_button,
            "locked": not self.controller.unlocked,
            "legal_state": self.controller.legal_state.value,
            "acknowledgements": (
                self.controller.consent.blank_acknowledgements()
                if screen_id is ScreenId.LEGAL_DATA_TERMS
                else {}
            ),
        }

    def navigate(self, screen_id: ScreenId) -> None:
        if (
            not self.controller.unlocked
            and screen_id not in {ScreenId.UNLOCK, ScreenId.LEGAL_DATA_TERMS}
        ):
            raise PermissionError("Unlock is required for this screen.")
        self.current_screen = screen_id
        if self.root is not None:
            self._render_current_screen()

    def run(self) -> None:
        if self.headless or self.root is None:
            return
        self.root.mainloop()

    def _build_native_window(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"ChartTrace 1.1 — {BUILD_LABEL}")
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)

        shell = ttk.Frame(self.root, padding=10)
        shell.pack(fill=tk.BOTH, expand=True)

        chrome = ttk.Frame(shell)
        chrome.pack(fill=tk.X)
        ttk.Label(
            chrome,
            text="ChartTrace 1.1",
            font=("Segoe UI", 16, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            chrome,
            text=f"  {BUILD_LABEL} · signing_state=unsigned",
            foreground="#8a4b00",
        ).pack(side=tk.LEFT)
        self.legal_button = ttk.Button(
            chrome,
            text="Legal, Data & Terms",
            command=lambda: self.navigate(ScreenId.LEGAL_DATA_TERMS),
        )
        self.legal_button.pack(side=tk.RIGHT)
        # The legal control lives in persistent chrome, never in replaceable
        # screen content, so it remains available even while locked.
        self.legal_button.charttrace_action_id = LEGAL_ACTION_ID  # type: ignore[attr-defined]

        banner = tk.Label(
            shell,
            text=SCREEN_CATALOG[ScreenId.UNLOCK].deadline_banner,
            bg="#7a1f1f",
            fg="white",
            padx=8,
            pady=7,
            anchor=tk.W,
        )
        banner.pack(fill=tk.X, pady=(10, 8))

        workspace = ttk.Frame(shell)
        workspace.pack(fill=tk.BOTH, expand=True)
        nav = ttk.Frame(workspace, width=230)
        nav.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        nav.pack_propagate(False)
        for screen_id, definition in SCREEN_CATALOG.items():
            if screen_id in {ScreenId.UNLOCK, ScreenId.LEGAL_DATA_TERMS}:
                continue
            button = ttk.Button(
                nav,
                text=definition.title,
                command=lambda selected=screen_id: self.navigate(selected),
            )
            button.pack(fill=tk.X, pady=2)
            self._nav_buttons[screen_id] = button

        self._content = ttk.Frame(workspace, padding=12)
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._render_current_screen()

    def _render_current_screen(self) -> None:
        if self._content is None:
            return
        for child in self._content.winfo_children():
            child.destroy()
        definition = SCREEN_CATALOG[self.current_screen]
        ttk.Label(
            self._content,
            text=definition.title,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(
            self._content,
            text=definition.summary,
            wraplength=720,
        ).pack(anchor=tk.W, pady=(0, 12))

        if self.current_screen is ScreenId.UNLOCK:
            self._render_unlock()
        elif self.current_screen is ScreenId.LEGAL_DATA_TERMS:
            self._render_legal()
        else:
            self._render_workspace(definition)
        self._refresh_navigation()

    def _render_unlock(self) -> None:
        if self._content is None:
            return
        form = ttk.Frame(self._content)
        form.pack(anchor=tk.W)
        ttk.Label(form, text="Operator").grid(row=0, column=0, sticky=tk.W, pady=4)
        operator = ttk.Entry(form, width=42)
        operator.grid(row=0, column=1, pady=4, padx=8)
        operator.insert(0, "Local operator")
        ttk.Label(form, text="Local unlock secret").grid(
            row=1, column=0, sticky=tk.W, pady=4
        )
        secret = ttk.Entry(form, width=42, show="•")
        secret.grid(row=1, column=1, pady=4, padx=8)

        def unlock() -> None:
            try:
                self.controller.unlock(secret.get(), operator.get())
            except Exception as error:
                messagebox.showerror("Unlock blocked", str(error), parent=self.root)
                return
            self.navigate(ScreenId.CASE_LIBRARY)

        ttk.Button(form, text="Unlock local session", command=unlock).grid(
            row=2, column=1, sticky=tk.W, padx=8, pady=10
        )
        ttk.Label(
            self._content,
            text=(
                "Legal, Data & Terms remains available before unlock. "
                "The local secret is not stored."
            ),
        ).pack(anchor=tk.W, pady=10)

    def _render_legal(self) -> None:
        if self._content is None:
            return
        self._status_var = tk.StringVar(
            value=f"Acceptance state: {self.controller.legal_state.value}"
        )
        ttk.Label(
            self._content,
            textvariable=self._status_var,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        canvas = tk.Canvas(self._content, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self._content, orient=tk.VERTICAL, command=canvas.yview
        )
        instruments = ttk.Frame(canvas)
        instruments.bind(
            "<Configure>",
            lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=instruments, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._ack_vars = {}
        for row, instrument in enumerate(INSTRUMENTS):
            panel = ttk.LabelFrame(
                instruments,
                text=f"{row + 1}. {instrument.title} · v{instrument.version}",
                padding=8,
            )
            panel.pack(fill=tk.X, pady=4)
            ttk.Label(panel, text=instrument.body, wraplength=680).pack(anchor=tk.W)
            variable = tk.BooleanVar(value=False)
            self._ack_vars[instrument.instrument_id] = variable
            ttk.Checkbutton(
                panel,
                text=instrument.acknowledgement,
                variable=variable,
                onvalue=True,
                offvalue=False,
            ).pack(anchor=tk.W, pady=(6, 0))

        accept_row = ttk.Frame(instruments)
        accept_row.pack(fill=tk.X, pady=10)
        ttk.Label(accept_row, text="Attesting operator").pack(side=tk.LEFT)
        accepted_by = ttk.Entry(accept_row, width=32)
        accepted_by.pack(side=tk.LEFT, padx=8)

        def accept() -> None:
            acknowledgements = {
                key: variable.get() for key, variable in self._ack_vars.items()
            }
            try:
                self.controller.accept_legal(acknowledgements, accepted_by.get())
            except Exception as error:
                messagebox.showerror("Acceptance incomplete", str(error), parent=self.root)
                return
            if self._status_var is not None:
                self._status_var.set(
                    f"Acceptance state: {self.controller.legal_state.value}"
                )
            self._refresh_navigation()

        ttk.Button(
            accept_row,
            text="Accept all separately acknowledged instruments",
            command=accept,
        ).pack(side=tk.LEFT)
        ttk.Label(
            instruments,
            text=(
                "Recipient transfer remains OFF. Name and separately authorize "
                "each recipient in Release Builder."
            ),
            foreground="#7a1f1f",
        ).pack(anchor=tk.W, pady=(0, 12))

    def _render_workspace(self, definition: ScreenDefinition) -> None:
        if self._content is None:
            return
        ttk.Label(
            self._content,
            text=f"Legal gate: {self.controller.legal_state.value}",
        ).pack(anchor=tk.W)
        if not self.controller.consent.current_and_authorized:
            ttk.Label(
                self._content,
                text=(
                    "HOLD_TERMS_OR_AUTHORITY — ingest, analysis, and release "
                    "actions are disabled."
                ),
                foreground="#a12828",
            ).pack(anchor=tk.W, pady=8)
        if definition.screen_id is ScreenId.CASE_LIBRARY:
            cases = self.controller.list_cases()
            if not cases:
                ttk.Label(self._content, text="No local cases.").pack(
                    anchor=tk.W, pady=8
                )
            for case in cases:
                ttk.Label(
                    self._content,
                    text=f"{case.name} · {case.lifecycle.value}",
                ).pack(anchor=tk.W, pady=2)
        elif definition.screen_id is ScreenId.COMMERCIAL_CONSOLE:
            ttk.Label(
                self._content,
                text=(
                    "This console only stores account-level licensing metadata. "
                    "It has no case, source, analysis, review, or release access."
                ),
                wraplength=700,
            ).pack(anchor=tk.W, pady=8)
        else:
            ttk.Label(
                self._content,
                text=(
                    "Select a local case in Case Library to perform this workflow "
                    "step. Controller policy gates remain authoritative."
                ),
                wraplength=700,
            ).pack(anchor=tk.W, pady=8)

    def _refresh_navigation(self) -> None:
        state = tk.NORMAL if self.controller.unlocked else tk.DISABLED
        for button in self._nav_buttons.values():
            button.configure(state=state)
