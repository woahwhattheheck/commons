from __future__ import annotations

import unittest

from host.titan_hands.android import AndroidHandsServer, parse_uiautomator_xml


XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="android" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[0,0][1080,1920]">
    <node index="0" text="Hello" resource-id="com.example:id/input" class="android.widget.EditText" package="com.example" content-desc="Greeting" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="true" scrollable="false" long-clickable="true" password="false" selected="false" bounds="[20,100][500,180]" />
  </node>
</hierarchy>"""


class FakeAdb:
    serial = "emulator-5554"

    def __init__(self):
        self.calls = []
        self.xml = XML

    def devices(self):
        return [{"serial": self.serial, "state": "device", "model": "headless"}]

    def resolve_serial(self):
        return self.serial

    def shell(self, *args, timeout=30):
        self.calls.append(("shell", args))
        return "UI hierchary dumped"

    def exec_out(self, *args, timeout=30):
        self.calls.append(("exec_out", args))
        if args[0] == "cat":
            return self.xml.encode()
        return b"PNG"


class FlakyAdb(FakeAdb):
    def __init__(self):
        super().__init__()
        self.reads = 0

    def exec_out(self, *args, timeout=30):
        if args[0] == "cat":
            self.reads += 1
            if self.reads == 1:
                return b"UI hierarchy unavailable"
        return super().exec_out(*args, timeout=timeout)


class PhysicalOnlyAdb(FakeAdb):
    serial = None

    def devices(self):
        return [{"serial": "PHONE123", "state": "device", "model": "personal"}]

    def resolve_serial(self):
        from host.titan_hands.android import AndroidBackendError

        raise AndroidBackendError("DEVICE_MISS", "no online Android emulator")


class AndroidHandsTests(unittest.TestCase):
    def test_parser_produces_semantic_edit_node(self):
        nodes = parse_uiautomator_xml(XML, "emulator-5554")
        edit = next(node for node in nodes if node["role"] == "TextBox")
        self.assertEqual(edit["name"], "Hello")
        self.assertIn("set_value", edit["actions"])
        self.assertEqual(edit["bounds"]["width"], 480)

    def test_observe_then_click_returns_delta(self):
        adb = FakeAdb()
        server = AndroidHandsServer(adb)
        first = server.handle({"op": "observe"})
        target = next(node for node in first["added"] if node["role"] == "TextBox")
        result = server.handle({"op": "act", "action": {"type": "click", "id": target["id"]}})
        self.assertTrue(result["ok"])
        self.assertIn(("shell", ("input", "tap", "260", "140")), adb.calls)
        self.assertFalse(result["observation"]["full"])

    def test_capabilities_do_not_require_live_observation(self):
        result = AndroidHandsServer(FakeAdb()).handle({"op": "capabilities"})
        self.assertTrue(result["online"])
        self.assertEqual(result["observation"], "uiautomator-semantic-delta")

    def test_observation_retries_transient_uiautomator_failure(self):
        adb = FlakyAdb()
        result = AndroidHandsServer(adb).handle({"op": "observe"})
        self.assertTrue(result["ok"])
        self.assertEqual(adb.reads, 2)

    def test_physical_only_backend_is_not_reported_as_default_online_target(self):
        result = AndroidHandsServer(PhysicalOnlyAdb()).handle({"op": "capabilities"})
        self.assertFalse(result["online"])
        self.assertEqual(result["devices"][0]["serial"], "PHONE123")


if __name__ == "__main__":
    unittest.main()
