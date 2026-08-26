"""Linux AT-SPI adapter sketch.

This module names the next computer-use hand. It is not shipped. Calls return
ADAPTER_NOT_WRITTEN instead of pretending AT-SPI observation or actuation works.
Windows UI Automation and Android (LDA Kotlin, UIAutomator fallback) remain the
live computer-use adapters.
"""

from __future__ import annotations

from typing import Any, Mapping

from host.titan_hands_windows.protocol import PROTOCOL_VERSION, failure


ATSPI_SKETCH = {
    "platform": "linux",
    "status": "ADAPTER_NOT_WRITTEN",
    "observation": "at-spi2 accessibility tree",
    "actuation": "AT-SPI actions plus toolkit patterns",
    "pixels": "explicit compositor capture only",
    "headless": "legacy apps under a headless compositor, when that compositor exists",
    "delta": "same DeltaUI added/updated/removed contract as Windows and Android",
    "role_map": {
        "frame": "Window",
        "push button": "Button",
        "entry": "TextBox",
        "text": "Text",
        "check box": "CheckBox",
        "radio button": "RadioButton",
        "combo box": "ComboBox",
        "menu item": "MenuItem",
        "scroll pane": "ScrollView",
        "slider": "Slider",
        "tab": "Tab",
        "link": "Hyperlink",
    },
    "action_map": {
        "click": "AccessibleAction click / press",
        "invoke": "AccessibleAction activate",
        "set_value": "AccessibleText / AccessibleEditableText / AccessibleValue",
        "toggle": "AccessibleAction toggle / AccessibleState checked",
        "select": "AccessibleSelection",
        "focus": "AccessibleComponent grab-focus",
        "scroll": "AccessibleAction scroll / AccessibleComponent",
        "key": "synthetic key after focus",
        "launch": "desktop file or argv, then AT-SPI observe",
        "wait": "local sleep",
        "capture": "compositor screenshot of the named window, never the default path",
        "done": "no-op receipt",
    },
    "not_shipped": [
        "no AT-SPI bus connection",
        "no compositor capture",
        "no live node IDs",
        "no pretend success",
    ],
}


def linux_capabilities() -> dict[str, Any]:
    return failure(
        "ADAPTER_NOT_WRITTEN",
        "Linux AT-SPI is named as the next adapter and is not shipped. "
        "Windows and Android remain the live computer-use hands.",
        platform="linux",
        sketch=ATSPI_SKETCH,
    )


def handle_linux(request: Mapping[str, Any]) -> dict[str, Any]:
    del request
    result = linux_capabilities()
    result["protocol"] = PROTOCOL_VERSION
    return result
