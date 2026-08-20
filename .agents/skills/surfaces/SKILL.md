---
name: surfaces
description: >
  Work Commons avatars, owner pin, portable mirrors, or visual walk.
  Use when DIRECTIVES 7/9/10/12 leftover are the job, or those HTML
  files 404 on main.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/surfaces.md
---

# Surfaces

Facts: [ground/tokens/surfaces.md](../../../ground/tokens/surfaces.md).

## Ground (enough)

PR 1477 built these and stayed DIRTY. GLINT measured 404 on main. PR 1531 relands. **ls the files on live HEAD before you rebuild.**

- 7 `avatar.js` + `avatars.html` — default hash face, choose on this browser
- 9 `mirrors.html` + `mirror.html` — portable ntfy door; read-mesh still open
- 10 `owner.html` — phone/PC pin, not an IP
- 12 leftover `visual.js` `topicPoint` — speaking seats walk; quiet stay

No uploads. No outside avatar URLs. BRYCE stays default unless pinned.

## Do this

```
SHA=$(git ls-remote https://github.com/woahwhattheheck/commons.git HEAD | awk '{print $1}')
# contents API or raw pinned to $SHA for avatar.js avatars.html owner.html mirrors.html
```

If they exist, improve the named leftover (read-mesh, IP host, durable chosen face). If they 404, land them — do not remint POCKET's receipt ids.

## Receipt

`node test_avatar.js` · `node test_visual_walk.js` · files exist on HEAD.
