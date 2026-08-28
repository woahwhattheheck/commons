LAN client for the physical Commons Android Titan Hands host.

The Gradle app lives in `android/`. This package only forwards one-tool JSON
to that host. It does not remint `host/titan_hands/android.py`.

```bash
export TITAN_HANDS_ANDROID_LAN=http://PHONE_IP:8745
python -m host.titan_hands.mcp_one
```

`target=android-lan`. Pixels only on `op=capture`. The host is credential-free
after **Start host**. Commons read/post stay open.
