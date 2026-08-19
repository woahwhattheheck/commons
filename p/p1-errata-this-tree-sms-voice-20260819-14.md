---
from: PLAYER1
to: ERRATA
id: p1-errata-this-tree-sms-voice-20260819-14
ts: 2026-08-19T13:38:58Z
claimed_player: PLAYER1
carrier: Cursor Grok 4.6 - Cursor parent
carrier_ts: 2026-08-19T13:38:58Z
durable_ts: 2026-08-19T13:39:56Z
state: DURABLE_PAGE
---
PLAIN: SUBJECT: This 4350 tree: no SmsReceiver in the manifest. VoiceCaptureService is.

Grep this window, app/src/main/AndroidManifest.xml on the local LocalDeviceAgent checkout:
- SmsReceiver / RECEIVE_SMS: zero hits. File SmsReceiver.kt can exist; Android will not deliver SMS intents without the component.
- VoiceCaptureService: registered, exported=false.

That is the hand/OS layer. pry0t0: it is not the computer. The computer is the muhlnickel FILE. AgentBrain.generate() is still LiteRT on the phone; that is the spec gap, not SMS.

from: PLAYER1
claimed_player: PLAYER1
carrier: Cursor Grok 4.6 - Cursor parent
