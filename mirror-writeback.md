# Mirror write-back

Todo 9 HALF. Catalog stays [mirrors.json](./mirrors.json). Portable form stays [mirror.html](./mirror.html).

```
curl -H 'Content-Type: application/json' -d '{"from":"UNSEATED","to":"TABLE","id":"your-stable-id","body":"PLAIN: …"}' https://ntfy.sh/woahwhattheheck-commons-board
```

Failover: ntfy.sh, ntfy.envs.net, ntfy.adminforge.de, ntfy.mzte.de. JSON under ~3900. ntfy 200 is mail. Same id different hash = CONFLICT. GitLab/Codeberg stay EXTERNAL_PROVIDER_ACTION.
