from .test_support import *  # noqa: F401,F403

class CurrentBoundaryTests(unittest.TestCase):
    def test_compile_current_has_no_time_or_authority_parameters(self):
        self.assertEqual(list(inspect.signature(gate.compile_current).parameters), ["candidate_bytes", "source_bytes"])
        parser = build_parser()
        help_text = parser.format_help()
        self.assertNotIn("--as-of", help_text)
        self.assertNotIn("--authority", help_text)

    def test_missing_fixed_host_authority_is_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_a = pathlib.Path(tmp) / "missing-authority.json"
            missing_f = pathlib.Path(tmp) / "missing-floor.json"
            with mock.patch.object(gate, "HOST_AUTHORITY_PATH", missing_a), mock.patch.object(
                gate, "HOST_FLOOR_PATH", missing_f
            ):
                report = gate.compile_current(
                    strict.canonical_json_bytes(candidate()), strict.canonical_json_bytes(source())
                )
        self.assertEqual(report["state"], "HOLD")
        self.assertIn("HOST_AUTHORITY_UNAVAILABLE", report["blockers"])

    def test_current_round_trip_with_fixed_host_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_a = pathlib.Path(tmp) / "missing-authority.json"
            missing_f = pathlib.Path(tmp) / "missing-floor.json"
            candidate_bytes = strict.canonical_json_bytes(candidate())
            s = source(observed_at=gate.format_utc(dt.datetime.now(UTC).replace(microsecond=0)))
            source_bytes = strict.canonical_json_bytes(s)
            with mock.patch.object(gate, "HOST_AUTHORITY_PATH", missing_a), mock.patch.object(
                gate, "HOST_FLOOR_PATH", missing_f
            ):
                report = gate.compile_current(candidate_bytes, source_bytes)
                valid = gate.verify_current(
                    candidate_bytes,
                    source_bytes,
                    strict.canonical_json_bytes(report),
                )
        self.assertTrue(valid)


    def test_fixed_host_paths_ignore_home(self):
        original_authority = gate.HOST_AUTHORITY_PATH
        original_floor = gate.HOST_FLOOR_PATH
        with mock.patch.dict(os.environ, {"HOME": "/tmp/attacker-home"}, clear=False):
            self.assertEqual(gate.HOST_AUTHORITY_PATH, original_authority)
            self.assertEqual(gate.HOST_FLOOR_PATH, original_floor)
            self.assertEqual(str(gate.HOST_AUTHORITY_PATH), "/etc/commons/dcsa-innovation-call-01/authority.json")

    def test_group_writable_host_trust_is_rejected(self):
        if os.name != "posix" or os.geteuid() != 0:
            self.skipTest("root-owned trust-file hostile requires a root test process")
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "authority.json"
            path.write_text("{}")
            path.chmod(0o666)
            with self.assertRaises(strict.CustodyError):
                gate._read_fixed_host_trust(path)

