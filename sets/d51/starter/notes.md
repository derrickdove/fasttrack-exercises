# d51 bench notebook

Use one or two sentences per blank. This notebook supports E1-E4;
E5 timing and E6 captured-evidence diagnosis are also graded in
`starter/timing.py`. E6 requires evidence IDs, a fault decision, a distinguishing
next measurement, and a safe disposition. A hypothesis is a possible cause
that you can check. Evidence is an observation that supports or rejects it.

| Bug | Observed symptom / reproduction input | Hypothesis and evidence | Repair and confirming test |
| --- | --- | --- | --- |
| E1 | 1000x reading error: | | |
| E2 | Station waits forever: | | |
| E3 | Gap count at wrap: | | |
| E4 | Output remains on: | | |

For E1, record what a multimeter could confirm about the steady voltage.
For E3, record what an oscilloscope could reveal about a short voltage dip
that a slow software reading could miss. Then use the actual supplied
serial, DMM, and scope captures in `data/` for the graded E6 decisions.
No physical instruments are needed; the E6 README defines each capture
condition and the exact answer fields.
