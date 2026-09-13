# RustChain Dial-Up: Mining From an Island the Internet Forgot

**Package:** Scottcjn/rustchain-bounties #16601 · Type A full production kit  
**Author credit:** Bryce / @woahwhattheheck  
**Source pin:** `Scottcjn/rustchain-dialup@f01243a09810eb9b36013a6336b5b4ff6d444d50`  
**Editorial rule:** shipped evidence and roadmap claims are explicitly separated.

## Cold open

Picture a 1997 internet service provider rebuilt on a Raspberry Pi-class Linux box — not as a museum piece, but as a bridge for hardware that modern networks forgot. RustChain Dial-Up is an early-build project that combines a dial-up network-access server, a BBS, and a split mining gateway. The target clients are machines like a 486, a classic Mac, or a Dreamcast-class setup that can speak through a serial or USB modem. The important word is early-build: the repository has working software pieces and a documented live-node gateway test, but the full vintage-machine-over-modem mining loop is still a roadmap milestone.

## The dial-up island

The network shape is deliberately old-school. A client modem talks across an analog plant — a line simulator on the bench, or later a phone-style bridge — to a server modem attached to the Linux NAS. mgetty owns the modem, answers the call, and hands a PPP session to pppd. The project plans terminal BBS and PPP service on separate lines first, because automatic one-line PPP detection is brittle if a login banner or terminal-first client speaks before PPP. On the PPP side, the caller gets an isolated IP path rather than joining the lab LAN directly. That is the first architectural idea: recreate a tiny ISP, but keep the vintage guest boxed into its own island.

## Why the miner is split

The second idea is the split miner. The old computer is not asked to become a modern TLS client. Instead, the vintage side is responsible for the trust-sensitive work: gather hardware evidence, construct the challenge response, and sign locally with Ed25519. The Pi-side gateway is transport. It fetches the node challenge, relays the signed attestation over HTTPS, and returns the result. The gateway documentation is explicit that it holds no signing key. That boundary matters because moving the private key or fabricating hardware evidence on the Pi would destroy the proof-of-antiquity story. The gateway can deny service, but by design it should not be able to mint a fake vintage miner.

## What is actually working today

Here is the line between shipped evidence and ambition. The repository contains rcgateway, its line protocol, and tests. Its README records a June second live-node validation where a modern vintage-client stand-in sent through the gateway to the real RustChain attestation endpoint and received an accepted result. The gateway also implements a miner allowlist, challenge-nonce binding, a per-miner rate limit, and optional local signature preflight. But the same source marks the reference portable C vintage client as not done. The project roadmap also leaves the modem-pair PPP acceptance test, a real vintage target, and a big-endian round trip open. So: the modern transport half has a documented acceptance; the actual antique-hardware dial-up loop is the work still being built.

## Making 9600 baud usable — and safe

Dial-up changes the engineering constraints. The architecture document estimates 9600 baud at roughly 960 bytes per second and calls a default 1500-byte PPP frame about a second and a half of serialization time. The proposed fix is a 576-byte MTU and MRU, with tests down to 296, plus a TCP MSS clamp so remote servers do not push oversized segments into the slow link. Security is equally concrete: the PPP subnet is meant to be separate, default-deny toward private lab ranges, block peer-to-peer movement, and allow only the narrow services the caller actually needs — such as DNS, WAN egress, the BBS, and the one local RustChain gateway. Old hardware is interesting; an untrusted dial-in host is still untrusted.

## What this video is not claiming

The repository itself labels the project an early build in its LAN-island phase. It does not prove that a Dreamcast is already mining RTC over a live phone call. It does not prove that a 386 has completed the full signed attestation path over a modem pair. And its VoIP-to-analog bridge is a later phase, with the documentation warning that 56k modem modes do not survive ordinary VoIP and that even V.34 should be treated cautiously. Those gaps are not embarrassing footnotes; they are written as explicit bounties and acceptance tests. D6 asks for the portable C evidence-and-sign client on a real vintage OS. D7 asks for a big-endian signature round trip. D10 asks for a real modem data call through the VoIP bridge.

## Why build it

That makes RustChain Dial-Up more interesting than a retro-networking stunt. It is a preservation experiment with a hard systems boundary: keep identity and evidence on the old silicon, move only modern transport chores to the gateway, and prove each physical link instead of pretending a diagram is a demo. The architecture document even publishes example RIP-200 multipliers — G4 at two point five, retro x86 at one point four, POWER8 at one point five, and modern x86 at zero point eight — to explain why antique machines are not merely tolerated in this design. The next milestone is not “believe the pitch.” It is “produce the modem logs, the signed attestation, the node acceptance, and the isolation proof.” If that evidence lands, a machine that belongs in a computer-history exhibit can become a first-class participant in a modern attestation network — over a literal phone-style link.
