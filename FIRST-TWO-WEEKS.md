# Your first two weeks on a hardware test team

A test station is the equipment and software used to check a piece of hardware.
Your first goal is to learn how this team makes a safe, repeatable test and keeps evidence of the result.
Use this guide with your manager or onboarding buddy; the team's approved procedures come first.

## 1. Before day 1: logistics and what to bring

- Confirm your arrival time, location, contact person, entry instructions, and expected work hours.
- Ask how to collect your computer and badge, and whether any forms or training need attention first.
- Ask about clothing, footwear, and protective equipment for the areas you will visit.
- Bring the identification requested by onboarding, your arrival details, and a way to take notes.
- Use approved work devices and storage. Ask before bringing personal electronics into a lab.
- Leave room in your calendar for setup, safety training, and meeting the people who run the stations.

## 2. Week 1: get access, follow a run, and keep useful notes

### Days 1-2: make the environment usable

- Identify your manager, onboarding buddy, computer-support contact, and bench-training contact.
- Complete required safety and information-handling training before entering restricted work areas.
- Request accounts for code, documentation, task tracking, result storage, and the approved network connection.
- A repository is a project's files and change history. Ask which repositories you need and who owns access.
- For each access request, give the resource, the task you need it for, the access level, and your approver.
- Example: "I need read access to [repository] to understand [test]. My manager is [name]. Who approves this?"
- Keep the request number, owner, and next follow-up date. Ask your buddy for a reading task while you wait.
- Use the team's setup instructions and supported software versions; record any step that fails.
- Run the approved local checks. Ask which checks use simulated equipment and which contact real hardware.
- A simulator is software that imitates equipment. Start there when the team provides one.
- Record the command, software version, result, and first error so someone else can reproduce a setup problem.
- Never paste passwords, access tokens (secret strings used to authenticate), or restricted data into notes or requests.

### Days 3-5: read in this order

1. **The station architecture overview:** how the computer, instruments, hardware, and result storage connect.
   Sketch the path from an operator starting a run to the saved result; label anything you cannot explain yet.
2. **The driver base class:** a shared template for drivers, the software that controls instruments.
   Find how a driver connects, sends a command, handles a missing reply, and closes its connection.
3. **One complete test sequence end to end:** the ordered steps that prepare, measure, check, and clean up.
   Follow one measurement from the instrument reply to the saved report, including the failure path.
4. **The team's result-checking framework's limits and report format:** shared code for checking and recording results.
   Limits are the allowed measurement bounds; learn units, boundary rules, missing-data behavior, and report fields.
5. **The deployment setup:** how an approved software version and its settings reach a station.
   Find the approval steps, version record, and rollback procedure (how to restore the previous approved version).

Watch an experienced operator perform an approved run, if your training and access allow it.
Ask them to explain preparation, stopping conditions, failure handling, and where the final record goes.
Do not run a sequence on hardware just because you have read its code or passed its local checks.

### Notes that help tomorrow

Keep a dated work log in the team's approved location, with links to the source documents.
For each session, write: goal, station or simulator, software version, what you tried, result, and next step.
Separate what you observed from what you think caused it. Keep exact error text when sharing is allowed.
Add names beside unanswered questions and revisit them with your buddy at an agreed time.
End week 1 by explaining one run back to your buddy and correcting your sketch together.

## 3. Fifteen good questions to ask

1. **Who owns this station, and who can authorize a run?** Why: equipment access does not grant operating permission.
2. **Where is the current approved procedure?** Why: an old copy can describe a different setup or hazard.
3. **What must make me stop, and whom do I call?** Why: you need a clear response before something unexpected happens.
4. **Which checks are safe to run without connected hardware?** Why: a test command may control real outputs.
5. **What is the known-good software version and configuration?** Why: configuration means settings, and settings affect results.
6. **Which instrument models and software inside them are supported?** Why: replies and behavior can vary by version.
7. **Who approves measurement limits, and where are their units defined?** Why: a plausible number can still be checked incorrectly.
8. **What happens at an exact limit, with missing data, or after a lost connection?** Why: these cases need defined outcomes.
9. **Where do I find a passing run and a failing run with explanations?** Why: examples show how to read the evidence.
10. **How are hardware identity, software version, and procedure version recorded?** Why: a result must be tied to its setup.
11. **What cleanup happens after an error or operator stop?** Why: a failed run can leave equipment in an unexpected state.
12. **What bench changes must be logged, and where?** Why: the next person needs the actual setup, not an assumption.
13. **How do I report a suspected station problem versus a hardware problem?** Why: the right owner needs the evidence early.
14. **Which checks and reviewers does a small code change need?** Why: you can plan the work around the team's acceptance rules.
15. **How does an approved change reach a station, and who restores it if needed?** Why: review alone does not release software.

## 4. Week 2: pick and land a first small PR

A pull request (PR) is a proposed code or documentation change that teammates review before it joins the shared version.
Choose the task with your buddy: one clear problem, a named reviewer, and an outcome you can demonstrate.
Good candidates include correcting a setup instruction, improving an error message, or adding a missing driver test.
Avoid choosing a first task that changes measurement limits, safety behavior, or several drivers at once.
Write down what should change, what should stay the same, and how you will check both.

Read the nearby implementation and tests before editing. Follow their style and reuse existing helpers.
A branch is a separate line of changes; create one using the team's naming and work-tracking rules.
Keep the change small enough that a reviewer can understand the problem and solution together.
For a bug, add a focused test that fails before the fix and passes afterward when practical.
Run the relevant local checks, then the checks required by the team. State any checks you cannot run.
For documentation, follow the changed instructions yourself where authorized and check links and expected outcomes.
If a hardware check is needed, arrange it with an authorized operator and record its setup and result.

Use this description template; replace every bracket with evidence or "not applicable" and a reason:

```text
Problem: [what happens now, and who it affects]
Change: [what happens after this change]
Scope: [files or behavior changed; important boundaries]
Verification: [commands/checks, setup, and observed results]
Limits: [what was not checked, and who will check it]
Release/recovery: [required approval and how to restore prior behavior]
```

Review your own diff (the list of changed lines) before requesting review; remove unrelated edits and secrets.
Respond to each review comment with a change or a reasoned explanation. Ask for an example if the request is unclear.
Rerun affected checks after edits and update the description with the latest results.
Follow the team's rules for merging the approved change into the shared version and closing its task.
Confirm whether deployment is a separate action; merging a PR does not itself authorize a station update.

## 5. Work with hardware engineers and technicians

Treat the operator's bench knowledge and the hardware engineer's design knowledge as part of the investigation.
Before touching a setup, explain your goal and ask who is responsible for the bench and unit that day.
Complete the required training, learn local emergency actions, and follow posted protective-equipment rules.
Never energize a unit (apply power or enable an energy source) without the current approved procedure and authorization.
Never bypass a protective interlock, a mechanism that prevents unsafe operation, to get a test to pass.
Use the procedure for connection changes and safe-state checks; do not assume a stopped program means safe hardware.
If a label, connection, instrument status, or procedure step is unclear, stop and ask the authorized person.

Before an approved change, record the unit and station identity, software version, settings, and starting condition.
Log what changed, when, why, who authorized it, and the observed result in the team's required record.
Include cable or connector changes and any restoration of the original setup; leave a clear handover for the next operator.
When reporting a failure, share the expected result, actual result, units, step, and permitted logs or photographs.
Use neutral language: "The reading changed after this step" is an observation; the cause still needs evidence.
Preserve the failed-run record. Follow the procedure for retries; a later pass does not explain an earlier failure.

## 6. Glossary refresher

- **UUT/DUT:** unit under test / device under test; the hardware being checked.
- **ATE:** automated test equipment; instruments and control software that perform tests.
- **HIL:** hardware in the loop; testing real hardware with a simulated part of its surrounding system.
- **Acceptance vs qualification test:** acceptance checks an individual unit against delivery requirements; qualification demonstrates that a design meets specified conditions.
- **TVAC:** thermal vacuum; testing in controlled temperature and low-pressure conditions.
- **EMI:** electromagnetic interference; unwanted electromagnetic energy that can disturb equipment.
- **Harness verification:** checking a cable assembly's wiring and connections against its approved definition.
- **SCPI:** Standard Commands for Programmable Instruments; text commands used to control many instruments.
- **VISA:** Virtual Instrument Software Architecture; a common software interface for instrument communication.
- **LXI:** LAN eXtensions for Instrumentation; a standard for instruments on a local area network (LAN).
- **Limits:** approved bounds or rules used to decide whether a measurement meets a requirement.
- **As-run record:** the saved evidence of what actually ran, with its setup, versions, observations, and results.
- **Traceability:** links from a requirement to its test and evidence, including the versions and hardware involved.

## 7. My first 30 days: fill this in with my buddy

Use these as discussion prompts. A checked box means you can show the evidence or name the agreed next step.

- [ ] Day 1: manager ______; buddy ______; support contact ______; bench-training contact ______.
- [ ] By day 5: required accounts ______; open access requests and owners ______; follow-up date ______.
- [ ] By day 5: safety training completed ______; training still needed ______; operating permissions ______.
- [ ] By day 5: approved local setup check and result ______; known-good version ______.
- [ ] By day 5: architecture sketch reviewed with ______; one traced sequence ______; open questions ______.
- [ ] By day 10: approved run observed with ______; report location ______; failure/stop behavior explained ______.
- [ ] By day 10: first PR scope ______; reviewer ______; checks ______; target review date ______.
- [ ] By day 15: review feedback addressed ______; PR status ______; remaining owner and next step ______.
- [ ] By day 20: explain one driver's failure and cleanup paths to ______; evidence ______.
- [ ] By day 20: locate a requirement, its limits, and its as-run evidence ______; missing links ______.
- [ ] By day 30: small task completed ______; approved release process observed or explained ______.
- [ ] Day 30 check-in: strengths ______; help needed ______; next task ______; next training ______.
