from .test_support import *


class TeamingConversionSecurityTests(BaseTeamingConversionTest):
    def test_strict_json_types_refs_and_time(self):
        p = packet(); p["assets"][0]["required_for_followup"] = 1
        with self.assertRaises(ControlError): self.comp(p)
        pol = policy(); pol["max_reply_age_seconds"] = True
        with self.assertRaises(ControlError): self.comp(packet(), pol)
        for value in ("person@example.com", "../../secret", "api-key-secret"):
            p = packet(); p["opportunity"]["counterparty_ref"] = value
            with self.assertRaises(ControlError): self.comp(p)
        with self.assertRaises(DuplicateKeyError):
            parse_json_bytes(b'{"x":1,"x":2}', "x")
        with self.assertRaises(ControlError): parse_json_bytes(b'{"x":NaN}', "x")
        for value in ("2026-09-13T08:00:00-04:00", "2026-09-13T12:00:00.123Z"):
            p = packet(); p["opportunity"]["source_checked_at"] = value
            with self.assertRaises(ControlError): self.comp(p)

    def test_receipt_verifiers_tamper_policy_and_exact_bytes(self):
        r = self.comp(); verify_control(packet(), policy(), r)
        tampered = copy.deepcopy(r); tampered["payload"]["disposition"] = "DECLINED"
        with self.assertRaises(ControlError): parse_receipt_bytes(canonical_bytes(tampered))
        pol = policy(); pol["max_reply_age_seconds"] -= 1
        with self.assertRaises(ControlError): verify_control(packet(), pol, r)
        pb, qb = canonical_bytes(packet()), canonical_bytes(policy())
        exact = compile_bytes(pb, qb, as_of=NOW); verify_bytes(pb, qb, canonical_bytes(exact))
        with self.assertRaises(ControlError): verify_bytes(b" " + pb, qb, canonical_bytes(exact))

    def test_determinism_and_order_invariant_projection(self):
        p1 = packet(); p1["assets"].append({
            "asset_id": "asset-public", "title": "Public reference", "version": "v1", "sha256": E,
            "prep_state": "READY", "release_class": "PROSPECT_SAFE_PUBLIC_REFERENCE",
            "required_for_followup": False, "safe_snippets": ["Public reference fact."],
        })
        pol = policy(); pol["asset_rules"].append(asset_rule(p1["assets"][-1]))
        p2 = copy.deepcopy(p1); p2["assets"].reverse()
        r1, r2 = self.comp(p1, pol)["payload"], self.comp(p2, pol)["payload"]
        for key in ("disposition", "safe_assets", "talking_points", "asset_blockers", "qualification_blockers"):
            self.assertEqual(r1[key], r2[key])
        md = render_markdown(self.comp())
        self.assertEqual(md, render_markdown(self.comp()))
        self.assertIn("Owner review only", md)

    def test_regular_io_and_cli(self):
        from revenue.teaming_conversion import cli
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); inp, pol = root/"packet.json", root/"policy.json"
            outj, outm = root/"receipt.json", root/"receipt.md"
            inp.write_bytes(canonical_bytes(packet())); pol.write_bytes(canonical_bytes(policy()))
            self.assertEqual(read_bounded_regular(inp), canonical_bytes(packet()))
            self.assertEqual(cli.main(["compile", "--input", str(inp), "--policy", str(pol),
                                       "--json-output", str(outj), "--markdown-output", str(outm)]), 0)
            self.assertEqual(cli.main(["verify", "--input", str(inp), "--policy", str(pol), "--receipt", str(outj)]), 0)
            self.assertEqual(cli.main(["compile", "--input", str(inp), "--policy", str(pol),
                                       "--json-output", str(outj), "--markdown-output", str(outm)]), 2)
            link = root/"link"; link.symlink_to(inp)
            with self.assertRaises(ControlError): read_bounded_regular(link)
            extra = root/"extra"; write_exclusive_regular(extra, b"x")
            with self.assertRaises(ControlError): write_exclusive_regular(extra, b"y")

    def test_fifo_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td)/"pipe"; os.mkfifo(fifo)
            with self.assertRaises(ControlError): read_bounded_regular(fifo)

    def test_python_optimized(self):
        if sys.flags.optimize:
            self.skipTest("already optimized")
        root = Path(__file__).resolve().parents[2]; env = dict(os.environ); env["PYTHONPATH"] = str(root)
        proc = subprocess.run([sys.executable, "-O", "-m", "unittest", "revenue.teaming_conversion.test_control"],
                              cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)
