"""Native Tk interface with a display-free headless mode for unit tests."""

from pathlib import Path
from typing import Dict, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from charttrace.app import BUILD_LABEL, CaseLifecycle, ChartTraceController
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
        self._selected_case_id: Optional[str] = None

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
        renderers = {
            ScreenId.CASE_LIBRARY: self._render_case_library,
            ScreenId.NEW_CASE_PREFLIGHT: self._render_new_case,
            ScreenId.SECURE_INGEST: self._render_ingest,
            ScreenId.PEER_RUN: self._render_peer_run,
            ScreenId.EVIDENCE_STUDIO: self._render_evidence_studio,
            ScreenId.HYPOTHESIS_LAB: self._render_hypothesis_lab,
            ScreenId.REVIEW_CONSOLE: self._render_review_console,
            ScreenId.RELEASE_BUILDER: self._render_release_builder,
            ScreenId.AUDIT_RECEIPTS: self._render_audit_receipts,
            ScreenId.COUNSEL_REVIEW_IMPORT: self._render_counsel_import,
            ScreenId.COMMERCIAL_CONSOLE: self._render_commercial_console,
        }
        renderers[definition.screen_id]()

    def _render_case_library(self) -> None:
        if self._content is None:
            return
        cases = self.controller.list_cases()
        listbox = tk.Listbox(self._content, height=12, activestyle="dotbox")
        listbox.pack(fill=tk.X, pady=8)
        case_ids = []
        for case in cases:
            listbox.insert(tk.END, f"{case.name}  ·  {case.lifecycle.value}")
            case_ids.append(case.case_id)
        if not cases:
            listbox.insert(tk.END, "No local cases.")
            listbox.configure(state=tk.DISABLED)
        else:
            selected_index = 0
            if self._selected_case_id in case_ids:
                selected_index = case_ids.index(self._selected_case_id)
            listbox.selection_set(selected_index)
            self._selected_case_id = case_ids[selected_index]

            def select_case(_: object) -> None:
                selection = listbox.curselection()
                if selection:
                    self._selected_case_id = case_ids[selection[0]]

            listbox.bind("<<ListboxSelect>>", select_case)
        ttk.Button(
            self._content,
            text="New case preflight",
            command=lambda: self.navigate(ScreenId.NEW_CASE_PREFLIGHT),
        ).pack(anchor=tk.W, pady=4)

    def _render_new_case(self) -> None:
        if self._content is None:
            return
        ttk.Label(
            self._content,
            text=(
                "A draft may be created before acceptance, but it remains "
                "HOLD_TERMS_OR_AUTHORITY until all instruments and authority "
                "are current."
            ),
            wraplength=700,
        ).pack(anchor=tk.W, pady=6)
        case_name = ttk.Entry(self._content, width=56)
        case_name.pack(anchor=tk.W, pady=6)

        def create_case() -> None:
            try:
                case = self.controller.create_case(case_name.get())
            except Exception as error:
                self._show_action_error("Case preflight blocked", error)
                return
            self._selected_case_id = case.case_id
            self.navigate(ScreenId.CASE_LIBRARY)

        ttk.Button(
            self._content,
            text="Create local draft",
            command=create_case,
        ).pack(anchor=tk.W, pady=4)

    def _render_ingest(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        ttk.Label(
            self._content,
            text="Choose local files. ChartTrace retains hashes and display names.",
        ).pack(anchor=tk.W, pady=6)

        def ingest() -> None:
            selected = filedialog.askopenfilenames(
                parent=self.root,
                title="Select local sources to hash-seal",
            )
            if not selected:
                return
            try:
                self.controller.secure_ingest(
                    case.case_id, [Path(value) for value in selected]
                )
            except Exception as error:
                self._show_action_error("Secure ingest blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            self._content,
            text="Choose and seal local files",
            command=ingest,
        ).pack(anchor=tk.W, pady=4)

    def _render_peer_run(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        ttk.Label(
            self._content,
            text=(
                "Peer output is UNSIGNED_SYNTHETIC and cannot bypass internal "
                "QA or named-human release review."
            ),
            wraplength=700,
        ).pack(anchor=tk.W, pady=6)

        def run_peer() -> None:
            try:
                self.controller.run_peer_analysis(case.case_id)
            except Exception as error:
                self._show_action_error("Peer run blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            self._content,
            text="Run local synthetic peer envelope",
            command=run_peer,
        ).pack(anchor=tk.W, pady=4)

    def _render_evidence_studio(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        if not case.sources:
            ttk.Label(self._content, text="No sealed sources.").pack(anchor=tk.W)
        for source in case.sources:
            ttk.Label(
                self._content,
                text=(
                    f"{source.display_name} · {source.size_bytes} bytes · "
                    f"SHA-256 {source.sha256}"
                ),
                wraplength=700,
            ).pack(anchor=tk.W, pady=2)

    def _render_hypothesis_lab(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        ttk.Label(
            self._content,
            text=(
                "Hypotheses are internal prompts for review, never factual "
                "findings. Source verification remains mandatory."
            ),
            wraplength=700,
        ).pack(anchor=tk.W, pady=6)
        for index, output in enumerate(case.peer_outputs, start=1):
            ttk.Label(
                self._content,
                text=(
                    f"Envelope {index}: {output.get('kind', 'unknown')} · "
                    f"{len(output.get('hypotheses', []))} hypothesis item(s)"
                ),
            ).pack(anchor=tk.W, pady=2)

    def _render_review_console(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        if case.lifecycle is CaseLifecycle.PEER_ANALYSIS:
            def complete_qa() -> None:
                try:
                    self.controller.complete_internal_qa(case.case_id)
                except Exception as error:
                    self._show_action_error("Internal QA blocked", error)
                    return
                self._render_current_screen()

            ttk.Button(
                self._content,
                text="Complete internal QA and send to human review",
                command=complete_qa,
            ).pack(anchor=tk.W, pady=6)
        reviewer = ttk.Entry(self._content, width=48)
        reviewer.pack(anchor=tk.W, pady=6)
        reviewer.insert(0, "Named human reviewer")

        def approve() -> None:
            try:
                self.controller.complete_human_review(
                    case.case_id, reviewer.get(), approved=True
                )
            except Exception as error:
                self._show_action_error("Human release review blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            self._content,
            text="Approve after human source and citation review",
            command=approve,
        ).pack(anchor=tk.W, pady=4)

    def _render_release_builder(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        form = ttk.Frame(self._content)
        form.pack(fill=tk.X, pady=6)
        ttk.Label(form, text="Named recipient").grid(row=0, column=0, sticky=tk.W)
        recipient = ttk.Entry(form, width=40)
        recipient.grid(row=0, column=1, padx=6, pady=3)
        if case.recipient.recipient:
            recipient.insert(0, case.recipient.recipient)
        ttk.Label(form, text="Role").grid(row=1, column=0, sticky=tk.W)
        role = ttk.Entry(form, width=40)
        role.grid(row=1, column=1, padx=6, pady=3)
        role.insert(0, case.recipient.recipient_role or "attorney")

        def set_recipient() -> None:
            try:
                self.controller.set_recipient(
                    case.case_id, recipient.get(), role.get()
                )
            except Exception as error:
                self._show_action_error("Recipient update blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            form,
            text="Set recipient (revokes prior authorization if changed)",
            command=set_recipient,
        ).grid(row=2, column=1, sticky=tk.W, padx=6, pady=4)

        transfer_ack = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self._content,
            text="I separately authorize transfer to the named recipient above.",
            variable=transfer_ack,
            onvalue=True,
            offvalue=False,
        ).pack(anchor=tk.W, pady=6)
        authorizer = ttk.Entry(self._content, width=40)
        authorizer.pack(anchor=tk.W)
        authorizer.insert(0, self.controller.operator)

        def authorize() -> None:
            try:
                self.controller.authorize_recipient_transfer(
                    case.case_id, transfer_ack.get(), authorizer.get()
                )
            except Exception as error:
                self._show_action_error("Transfer authorization blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            self._content,
            text="Record separate transfer authorization",
            command=authorize,
        ).pack(anchor=tk.W, pady=4)

        def build() -> None:
            destination = filedialog.asksaveasfilename(
                parent=self.root,
                title="Build local release bundle",
                defaultextension=".json",
                filetypes=[("ChartTrace JSON bundle", "*.json")],
            )
            if not destination:
                return
            try:
                self.controller.build_release(case.case_id, destination)
            except Exception as error:
                self._show_action_error("Release build blocked", error)
                return
            messagebox.showinfo(
                "Release built",
                "UNSIGNED_SYNTHETIC local bundle created.",
                parent=self.root,
            )

        ttk.Button(
            self._content,
            text="Build unsigned local release bundle",
            command=build,
        ).pack(anchor=tk.W, pady=4)

        def release() -> None:
            try:
                self.controller.release_to_named_recipient(case.case_id)
            except Exception as error:
                self._show_action_error("Release blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            self._content,
            text="Confirm release to named recipient",
            command=release,
        ).pack(anchor=tk.W, pady=4)

    def _render_audit_receipts(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        for receipt in case.receipts:
            ttk.Label(
                self._content,
                text=(
                    f"{receipt.sequence}. {receipt.event} · "
                    f"{receipt.receipt_hash[:16]}…"
                ),
            ).pack(anchor=tk.W, pady=2)

    def _render_counsel_import(self) -> None:
        case = self._render_active_case()
        if self._content is None or case is None:
            return
        ttk.Label(
            self._content,
            text=(
                "Only local JSON bundles with mode=offline_counsel_review are "
                "accepted. This mode performs no network request."
            ),
            wraplength=700,
        ).pack(anchor=tk.W, pady=6)

        def import_review() -> None:
            selected = filedialog.askopenfilename(
                parent=self.root,
                title="Import offline counsel review",
                filetypes=[("JSON review bundle", "*.json")],
            )
            if not selected:
                return
            try:
                self.controller.import_offline_counsel_review(
                    case.case_id, Path(selected)
                )
            except Exception as error:
                self._show_action_error("Counsel import blocked", error)
                return
            self._render_current_screen()

        ttk.Button(
            self._content,
            text="Import local counsel review",
            command=import_review,
        ).pack(anchor=tk.W, pady=4)

    def _render_commercial_console(self) -> None:
        if self._content is None:
            return
        ttk.Label(
            self._content,
            text=(
                "This console only stores account-level licensing metadata. "
                "Its isolated service has no case, source, analysis, review, "
                "or release imports."
            ),
            wraplength=700,
        ).pack(anchor=tk.W, pady=8)

    def _render_active_case(self):
        if self._content is None:
            return None
        case = self._active_case()
        if case is None:
            ttk.Label(
                self._content,
                text="Select or create a case in Case Library first.",
                foreground="#a12828",
            ).pack(anchor=tk.W, pady=8)
            return None
        ttk.Label(
            self._content,
            text=f"Active case: {case.name} · {case.lifecycle.value}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, pady=4)
        return case

    def _active_case(self):
        if self._selected_case_id:
            try:
                return self.controller.get_case(self._selected_case_id)
            except KeyError:
                self._selected_case_id = None
        cases = self.controller.list_cases()
        if not cases:
            return None
        self._selected_case_id = cases[0].case_id
        return cases[0]

    def _show_action_error(self, title: str, error: Exception) -> None:
        messagebox.showerror(title, str(error), parent=self.root)

    def _refresh_navigation(self) -> None:
        state = tk.NORMAL if self.controller.unlocked else tk.DISABLED
        for button in self._nav_buttons.values():
            button.configure(state=state)
