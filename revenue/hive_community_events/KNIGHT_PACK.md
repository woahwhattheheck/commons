# Knight challenges for Lantern community events

Two ready-to-import, twelve-question packs add empty-board knight challenges to
LANTERN's existing scheduled trivia workflow. They are original generated
questions, not a chess engine or a second event service. ROOKBRIDGE authored the
generator and its original regression suite; ASTER-PUBLISH composed the packs
with LANTERN's actual import contract and added the consumer tests.

## Use the supplied packs

`knight-week-1.json` and `knight-week-2.json` are question arrays with `prompt`,
`choices`, and **zero-based `correct`** fields. Supply either array as the
`questions` value when creating a Lantern event, or paste its JSON into the
existing question-set editor. Each question uses the app's default 100 non-cash
points. A perfect twelve-question round scores 1200 points.

Start the existing application from this directory:

```sh
python3 app.py --db /existing/private/path/events.sqlite3 --port 8765
```

Use its existing schedule, room, join, answer, finish, and reconnect workflow.
No application, browser UI, host controls, or data schema are replaced by this
addition. Native browser interaction and a community-platform installation are
not claimed by the tests below.

## Generate another pack

From `revenue/hive_community_events`, write a new file:

```sh
python3 knight_pack.py --seed community-knight-week-3 --count 12 \
  --answer-key correct --omit-explanation --output knight-week-3.json
```

The output filename must not already exist; generation preserves an existing
file rather than overwriting it. The generator accepts 1–64 questions, but the
current Lantern importer accepts 1–50 questions per event. Use `--count 50` or
less for a single event. Both supplied packs contain 12.

The generator's original generic default remains `answer` with `explanation`.
That default is useful for another consumer or a host answer sheet but is **not**
the ready-to-import Lantern schema. The explicit `--answer-key correct` mapping
above is required. `--omit-explanation` prevents putting host explanations in
public questions while the round is still open. To retain a separate host answer
sheet, run the generic default to a different filename. Do not distribute that
answer sheet to participants during a round.

Python integration uses the same adapter:

```python
import knight_pack

questions = knight_pack.adapt(
    knight_pack.generate("community-knight-week-3", count=12),
    answer_key="correct",
    explanation_key=None,
)
# Pass questions to Store.create or as the HTTP creation payload's questions.
```

## Question rules and determinism

The packs alternate single-move questions and minimum-move-distance questions.
Every question concerns a lone knight on an otherwise empty 8-by-8 board.
Single-move questions have exactly one reachable destination among four choices;
distance questions use breadth-first shortest paths on the finite knight graph.
No blockers, captures, checks, castling, legal full-game positions, or tournament
identity rules are modeled. LANTERN's separate chess-position UI remains its
own feature; these packs use the ordinary multiple-choice interface.

Stable SHA-256 ordering derives the question selection and choice placement from
the supplied seed. The same seed and count reproduce the same serialized output;
there is no network call, randomness source, external service, or paid dependency.
Correct-answer positions are balanced to within one across a pack, not fixed to
one slot. The two supplied seeds are `community-knight-week-1` and
`community-knight-week-2`.

## Executed validation

```sh
python3 -B -m unittest -v test_knight_pack test_knight_lantern_integration
```

The publication run passed **38 test methods** in 2.446 seconds. The original 30
methods cover every square's legal neighbors, all 4096 source/target pairs,
question correctness, deterministic generation, answer-position balance, adapter
validation, CLI behavior, and preservation of existing files. The additional
eight methods exercise the actual Lantern implementation with real SQLite and
loopback HTTP: both supplied imports, hidden answers while open, schedule
boundaries, twelve correct answers, identical and conflicting retries, final
scores, database reopening, reconnect, and the importer size boundary.

Consumer source was read at main
`3a271f9b819f41f5385adf3ad26baf455723c60e`; `app.py` Git blob
`186084da7922c0d18fc4106597693cd3054c40f2`. Fresh main
`53a9e0525585af91df1115a587cdf12fc818d66e` retains that exact consumer blob.
The consumer's bytes are not included in this contribution's change set.

The tests ran only in the provided cloud container. They do not establish
native-browser transport, hosted deployment, platform integration, user adoption,
a sale, or completion of every item in demand `bm-hive-20260908-038`.
