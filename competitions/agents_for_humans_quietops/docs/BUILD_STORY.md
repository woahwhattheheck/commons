# Agents for Humans: building an agent that knows when to stop

The temptation in agent demos is to maximize autonomy. For a professional background agent, that is backwards. The useful question is: **which interruptions can disappear without turning uncertainty into external action?**

QuietOps uses Strands Agents SDK for the parts language models are good at: evidence review, planning and explanation. It uses a deterministic Python authority gate for the part that should not be decided by persuasive prose. Customer/vendor contact, prices, payments, contract acceptance, legal interpretation, external mutation, low confidence and ambiguous evidence are human-only. Reversible analysis can complete quietly and emits a SHA-256-bound receipt.

I also wanted replay behavior to be boring. Evidence is bound as `(ref, sha256)` generations; order cannot remint a new operation; exact queue duplicates collapse; reusing the same event identity for different content fails closed. A local benchmark exercises every authority class plus adversarial ambiguity/low-confidence promotion attempts.

The practical outcome is an agent that can clear the repetitive middle of professional work while making the remaining human decisions smaller and better evidenced. That is the kind of autonomy I would actually leave running in the background.
