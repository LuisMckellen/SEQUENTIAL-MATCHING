# METHOD — principles for the Sequential Matching Problem

Transferable rules, adapted from the AG News project. Results live in the
research note and `results/*.jsonl`, never here.

## Measuring

1. **Compare paired.** Same seed, both policies, take the per-seed difference.
   The world is identical, so its luck cancels.
2. **Compare whole worlds, never split a pool.** One introduction changes
   everyone's options (problem statement §1). Two policies sharing one pool
   contaminate each other.
3. **Report mean delta, its 95% bootstrap interval, and wins/ties/losses.**
   10/10 wins with a small mean beats 6/10 with a large one.
4. **When the mean sits inside its interval, the sign count is noise.**
   Don't quote "4/5 seeds better" on an MSMI delta of one event.
5. **Pick the signal that has events.** MSMI is about one per 200 people.
   Develop on mutual acceptances (~15× more events); decide on MSMI.
6. **Explore cheap, confirm expensive.** 5 seeds to see if anything moves,
   20+ seeds per family before claiming it moved.
7. **A tie can mean the change never reached a decision.** Before reading a
   null result, count how many introductions actually differ between the two
   policies on the same seed. Same pairs chosen = the change had nothing to
   decide. Different pairs, same score = a real null.

## Leaking

8. **Use only what was known at decision time.** A feature for a day-*d*
   introduction uses a field only if `field_observed_day <= d`.
9. **Hidden simulator data never enters the policy.** `truth`, bias and
   response rates stay out. Analysis-only scripts say so in their file name.
10. **Silence is not a No.** A missing response is missing; a pair never
    introduced has no label (§8–§9).
11. **Training seeds and reported seeds never overlap.** Seeds used while
    developing are "seen"; reproduce on them, never tune on them.

## Predicting

12. **Write the prediction and what each outcome would mean before running.**
13. **Being wrong with a recorded prediction is a finding.** Report it.
14. **A null result, tested properly, is publishable.** "Tied on 20 paired
    seeds, and here is why" beats a quiet omission.

## Auditing your own numbers

15. **The funnel is a free identity.** Every run must satisfy
    assignments ≥ mutual acceptances ≥ dates ≥ MSMI. A violation is a bug.
16. **A number that can't be reproduced from a committed file is a liability.**
    Every figure in the note traces to a JSONL record and a script.
17. **One definition, one script.** Final numbers come from `evaluate.py`.
    In-process scripts are for exploring; their denominators may differ.
18. **Pair by key, never by position.** Join results on `(experiment, family,
    seed, policy)`, not on list order.
19. **Zero selected is not zero failed.** Check the seed count in every
    summary before reading its numbers.

## Deciding

20. **Arbitrary parameters get a sensitivity check, not a hunt.** For the
    shrinkage prior (4 observations) or the reserve τ0: rerun at a few values
    and show whether the conclusion changes.
21. **Size the effect before designing the experiment.** Count how many
    people or pairs a change can touch, compare against the paired
    resolution, then decide whether the run can show anything.
22. **Label every claim:** stated rule (problem statement §), public-simulator
    measurement (seeds named), or hypothesis (untested).

## Building

23. **A gate must be shown to fail.** Feed the validator a deliberately
    invalid pair, a duplicate, an over-budget ask, before trusting it.
24. **Store the environment with every result.** Python and package versions,
    git SHA, seeds, `PYTHONHASHSEED=0`.
25. **JSONL with an `experiment` field.** One file can hold many experiments;
    filter, never assume.
26. **Commit intermediate results.** They are the evidence for the note.
27. **When a test fails, decide whether the code or the test is wrong first.**

## Reading the simulator

28. **Read episodes, not just totals.** Print a few introductions and their
    feedback rows end to end; aggregates hide what reading reveals.
29. **A rate on a selected group doesn't lift to the pool.** Newcomers,
    declined-field members and frequent responders are selected groups.
30. **Two checks agreeing is evidence only if they are independent.** The
    graph diagnostic and the decision-diff check (rule 7) test scarcity in
    different ways; agreement between them counts.
