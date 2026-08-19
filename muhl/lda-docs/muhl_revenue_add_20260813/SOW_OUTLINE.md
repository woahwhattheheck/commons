# White Box 30-day pilot SOW outline

**Provider:** Muhlnickel / Bryce Muhlnickel  
**Customer:** [Customer legal name]  
**Term:** 30 calendar days  
**Fee:** $30,000 fixed; $15,000 on signing and $15,000 on delivery

## 1. Objective

Apply White Box privately to one customer-owned GGUF model family and demonstrate a narrow, reversible model change using the customer's evaluation harness.

The pilot is a professional service and evaluation engagement. It is not a sale, license, or transfer of Bryce Muhlnickel's computer.

## 2. Customer-selected target

Before work begins, the parties will write one precise target statement:

- model and version;
- behavior, feature, or capability to examine;
- one ablation objective;
- one targeted-edit objective;
- evaluation cases and acceptance measurements; and
- prohibited regressions or protected capabilities.

Material changes to that target require a written change order.

## 3. Thirty-day work plan

### Days 1–5: intake and baseline

- Confirm the supplied GGUF, model ownership or authorization, and artifact hash.
- Run the customer's baseline evaluation harness.
- Agree on the target, protected behaviors, and acceptance measurements.
- Produce a model-level map focused on the selected target.

### Days 6–12: reversible ablation

- Perform one bounded ablation related to the agreed target.
- Preserve the original customer artifact.
- Evaluate the ablated model with the customer's harness.
- Record the measured effect and any protected-behavior regressions.

### Days 13–21: targeted edit

- Restore the approved working baseline.
- Perform one targeted edit related to the agreed objective.
- Evaluate the edited model with the customer's harness.
- Compare baseline, ablation, and edited results.

### Days 22–26: rollback proof

- Roll the targeted edit back.
- Verify the restored artifact against the agreed integrity check.
- Re-run the agreed rollback subset of the customer's harness.
- Package the rollback evidence.

### Days 27–30: delivery and review

- Deliver the agreed customer-retainable artifacts.
- Present results, limitations, and measured regressions.
- Hold one technical review with the customer's designated team.
- Present an optional organization-license path for follow-on White Box work.

## 4. Deliverables

1. A target-focused model map suitable for the customer's decision-making.
2. One reversible ablation artifact and its evaluation results.
3. One targeted-edit artifact and its evaluation results.
4. One restored artifact plus rollback proof.
5. A concise comparison of baseline, ablation, edit, and rollback runs.
6. A final technical review under NDA.

The customer may retain its edited, ablated, and restored model artifacts and the agreed reports.

## 5. Customer responsibilities

The customer will provide by the start date:

- a legally controlled GGUF and permission for Muhlnickel to work on it;
- a runnable evaluation harness with representative test data;
- documented success measurements and protected behaviors;
- a technical owner able to answer model and harness questions; and
- a secure method for model and result exchange.

Delays in customer inputs move the delivery dates by the same number of days.

## 6. Acceptance

The pilot is accepted when Muhlnickel has:

- supplied each listed deliverable;
- demonstrated that the ablation and edit are reversible;
- shown rollback integrity using the agreed check; and
- run the agreed baseline, ablation, edit, and rollback evaluations through the customer's harness.

Acceptance is based on completion of the agreed intervention and proof package, not a promise that every evaluation metric will improve. Any required quantitative threshold must be written into the target statement before work begins.

## 7. What the customer sees

- Its original, ablated, edited, and restored model artifacts.
- Artifact identity and integrity evidence.
- The agreed model-level map.
- Before-and-after results from its own evaluation harness.
- A record of the contracted intervention at the level needed to evaluate, use, and roll back the delivered model.
- A private technical presentation of the outcome and limitations.

## 8. What remains Muhlnickel confidential

- Bryce Muhlnickel's computer.
- White Box machinery, internal tooling, targeting methodology, and implementation details.
- Any internal artifact or process not expressly named as a customer deliverable.

No confidential Muhlnickel material is transferred, published, or made available as a downloadable product. A closed-room demonstration may be added by written agreement under NDA.

## 9. Intellectual property and publicity

- The customer retains its pre-existing model, data, harness, and customer materials.
- The customer may use the contracted model deliverables internally under the SOW.
- Bryce Muhlnickel retains White Box, his computer, his methods, machinery, tooling, and all improvements to them.
- Neither party may use the other's name, marks, results, or pilot details publicly without written approval.
- No open-source release is included or authorized.

## 10. Out of scope

- Transfer or access to Bryce Muhlnickel's computer.
- Public release of White Box.
- Production integration, hosting, ongoing support, or additional model families.
- Training-data remediation, broad retraining, or unrelated model changes.
- Safety certification, regulatory certification, or warranties beyond the written acceptance terms.

Follow-on work requires a separate SOW or a $100,000–$175,000 organization license.
