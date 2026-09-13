# Synthetic scheduler exercise

**Label: SYNTHETIC ONLY — not an educational efficacy result.**

This exercise exists to make the adaptive policy inspectable. It invents one learner profile, gives each skill a starting success probability, and increases that probability slightly when the synthetic learner practices the skill. It then compares 90 practice steps under MistakeMap's adaptive scheduler with a round-robin scheduler.

The model is intentionally toy-sized and is not calibrated to children, classrooms, curricula, or real learning curves.

## Reproduce

```bash
npm run benchmark
```

Current deterministic run:

| Strategy | Mean synthetic skill probability after 90 steps | Weakest synthetic skill | Weak-skill allocation behavior |
| --- | ---: | ---: | --- |
| Adaptive | 0.598 | 0.561 | Concentrates practice on multiplication, division, fractions |
| Round robin | 0.588 | 0.470 | Exactly 15 exposures per skill |

The result only confirms that the scheduler implements its design objective in the synthetic model: it allocates more practice to weak/due skills. It does **not** show that MistakeMap improves real learning outcomes.
