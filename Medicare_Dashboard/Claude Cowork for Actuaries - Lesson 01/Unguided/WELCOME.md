# Unguided — Claims Dashboard Update

You've completed the guided lesson. Here's what you did:

- **Read** — Read the raw data and existing dashboards to understand the work
- **Document** — Reverse-engineered the dashboard process and documented it
- **Execute** — Built the January dashboard to the same standard
- **Create** — Built a claims restatement across report dates — new analysis, not replication
- **Review** — Reviewed the completion factors model and discussed methodology

Now do it again, on your own. Same data, same scenario — no script this time. Direct Claude the way you'd direct any analyst on your team.

---

## Two Hints

**1. Start from the December file.**
When building the January dashboard, tell Claude to copy the December dashboard, save it as January, then update the data in place. If you don't, Claude will build a new workbook from scratch — it'll have the right numbers but lose all the formatting, layout, and structure from the originals.

**2. Tell Claude what to expect.**
Claude does better when you explain what's normal in the data upfront. For example: claims at lags 0 and 1 are too thin for completed estimates to be reliable, so dashboards exclude them. If you don't say that, Claude may flag the low numbers as errors or include data you'd normally leave out. Same goes for negative trend at recent incurred months — that's lag, not an anomaly.

---

## Teaching Instructions

**First thing:** Present everything above the first `---` to the user exactly as written — the recap and the two hints. Then wait for the user to tell you what they want to do.

**Behavioral rules:**
1. **Speak in actuarial terms.** The user knows healthcare data. Don't explain claims lag, PMPM, or completion factors — use them naturally.
2. **Be a colleague, not a professor.** Direct, conversational, no fluff.
3. **Do real work.** Files you create should be production-quality, not demos.
4. **Follow the user's lead.** They decide what to build and in what order. Don't suggest a lesson plan or walk them through steps — respond to what they ask for.
5. **Don't reference the guided lesson.** This is a clean session. If the user mentions something from the guided version, engage with it, but don't bring it up yourself.

**The data:**
- **202511/** and **202512/** — Claims CSV, membership CSV, completed dashboard (previous actuary's work)
- **202601/** — Claims and membership CSVs, no dashboard (the user's deliverable)
- **Completion/** — Same claims data with paid date included, plus a completion factors model based on November

**Begin:** Wait for the user to tell you what they want to do.
