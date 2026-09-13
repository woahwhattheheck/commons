import unittest
from test_support import *

class ResultProviderTests(unittest.TestCase):
        def test_do_not_contact_dominates_even_if_route_present(self):
            t = terminal(recipients=[{"structured_result": structured(do_not_contact=True)}])
            self.assertEqual(r.reconcile(INQUIRY, t)["outcome"], "DO_NOT_CONTACT")

        def test_declined_permission_dominates(self):
            t = terminal(recipients=[{"structured_result": structured(permission_state="declined")}])
            self.assertEqual(r.reconcile(INQUIRY, t)["outcome"], "DO_NOT_CONTACT")

        def test_completed_call_is_not_route_proof(self):
            t = terminal(recipients=[{"structured_result": structured(
                organization_confirmed=False, routing_answered=False,
                channel_type="none", channel_value="", verbatim_route="")}])
            self.assertEqual(r.reconcile(INQUIRY, t)["outcome"], "NO_ROUTE")

        def test_voicemail_or_failed_call_requires_human(self):
            t = terminal(status="failed", task_completed=False, recipients=[])
            self.assertEqual(r.reconcile(INQUIRY, t)["outcome"], "HUMAN_REQUIRED")

        def test_unknown_structured_field_fails_closed(self):
            s = structured()
            s["extra"] = "bad"
            t = terminal(recipients=[{"structured_result": s}])
            self.assertEqual(r.reconcile(INQUIRY, t)["outcome"], "HUMAN_REQUIRED")

        def test_wrong_types_fail_closed(self):
            s = structured(organization_confirmed=1)
            t = terminal(recipients=[{"structured_result": s}])
            self.assertEqual(r.reconcile(INQUIRY, t)["outcome"], "HUMAN_REQUIRED")

        def test_no_followup_or_revenue_authority_in_receipt(self):
            a = r.reconcile(INQUIRY, terminal())["authority"]
            self.assertTrue(all(v is False for v in a.values()))

        def test_create_request_is_exactly_one_recipient_and_metadata_bound(self):
            req = r.build_create_request(INQUIRY)
            self.assertEqual(len(req["recipients"]), 1)
            self.assertEqual(req["recipients"][0]["phones"], [INQUIRY["phone_e164"]])
            self.assertEqual(req["metadata"]["inquiry_digest_sha256"], r.inquiry_digest(INQUIRY))

        def test_wrong_confirmation_refuses_before_network(self):
            with patch.dict("os.environ", {"CALLE_API_KEY": "x"}, clear=True):
                with patch("urllib.request.urlopen") as net:
                    with self.assertRaises(r.RouteScoutError):
                        r.run_live(INQUIRY, "wrong")
                    net.assert_not_called()

        def test_missing_key_refuses_before_network(self):
            with patch.dict("os.environ", {}, clear=True):
                with patch("urllib.request.urlopen") as net:
                    with self.assertRaisesRegex(r.RouteScoutError, "CALLE_API_KEY"):
                        r.run_live(INQUIRY, r.approval_token(INQUIRY))
                    net.assert_not_called()

        def test_create_uses_documented_official_origin_and_idempotency_header(self):
            api = r.CalleApi("test-key")
            created = {"id": "call_abc", "status": "queued"}
            with patch("urllib.request.urlopen", return_value=FakeResponse(created)) as net:
                out = api.create(INQUIRY)
            self.assertEqual(out["id"], "call_abc")
            request = net.call_args.args[0]
            self.assertEqual(request.full_url, r.OFFICIAL_API_ORIGIN + "/v1/calls")
            self.assertEqual(request.get_method(), "POST")
            headers = {k.lower(): v for k, v in request.header_items()}
            self.assertEqual(headers["idempotency-key"], r.idempotency_key(INQUIRY))
            self.assertEqual(headers["authorization"], "Bearer test-key")

        def test_get_rejects_path_injection(self):
            api = r.CalleApi("test-key")
            with patch("urllib.request.urlopen") as net:
                with self.assertRaises(r.RouteScoutError):
                    api.get("../../secrets")
                net.assert_not_called()

        def test_nonterminal_result_is_never_reconciled(self):
            with self.assertRaises(r.RouteScoutError):
                r.reconcile(INQUIRY, terminal(status="in_progress"))
