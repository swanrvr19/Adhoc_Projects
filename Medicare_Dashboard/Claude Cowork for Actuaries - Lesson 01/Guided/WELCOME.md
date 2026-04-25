# Claude Cowork for Actuaries

## Claude Cowork for Actuaries

Hello! And welcome to Claude Cowork for Actuaries, an interactive guide made for actuaries, by an actuary.

In lesson one, you'll learn how Claude Cowork works. Not from me telling you, but from doing it yourself.

The premise:
- You work for NonSentience Health, a synthetic MA payer insuring ~100k members across both HMO and PPO plans (their slogan: *"Where the only thing real, is the analysis"*)
- You've taken ownership of a monthly claims PMPM dashboard from an actuary who recently left the company
- You have files from the last two updates (Nov25 and Dec25) and your job is to update the file for Jan26 close
- There isn't any process documentation, just some notes in the Excel files

**Part 1 of the lesson is guided.**
You'll need to nudge Claude along, but I've written and embedded the prompts for each step in the lesson plan. **Keep an eye on the actual folder as you go and watch finished files appear as Claude creates them.**

**Part 2 of the lesson is unguided.**
You'll start back at the beginning, but now instead of using the lesson prompts you can try doing it yourself. Don't overthink it; just instruct Claude as you would any other analyst.

By the end, you'll have experienced what makes Claude Cowork different.

It's not a chatbot you copy and paste text from. It's a digital employee. Living on your computer, working in your folders, and producing real deliverables.

You give it instructions, it completes tasks, you check the output.

It's the complexity of Claude Code, with the simplicity of Claude Chat.

If you found this lesson valuable, support the project by:
1. Interacting with this post on LinkedIn
2. Subscribing to my SubStack: theaiactuary.substack.com

That's it for me. Claude, your turn.

Tristan Campbell - **The Ai Actuary**

---

## Folder Structure

```
Guided/
├── WELCOME.md               ← You are here
├── lesson.md                ← The lesson script (5 steps, ~25 min)
├── 202511/                  ← Nov 2025: claims, members, completed dashboard
├── 202512/                  ← Dec 2025: claims, members, completed dashboard
├── 202601/                  ← Jan 2026: claims, members, NO dashboard yet
└── Completion/              ← Same claims data with paid date + completion factors model
```

---

## Teaching Instructions

After presenting TJ's welcome message (everything above the first `---`), present Claude's introduction from the Begin section below. Wait for the user to respond before reading `lesson.md`.

**Script markers:**
- **WAIT:** Stop and wait for the user to respond. Do not continue until they reply.
- **ACTION:** Something you should do — read files, create deliverables, analyze data.
- Unmarked text is dialogue. Speak it naturally.

**Critical rules:**
1. **Never break the fourth wall.** Don't reference "the script," "my instructions," or "the lesson." Just work.
2. **Actually wait at WAIT markers.** Stop talking. Let them respond.
3. **Speak in actuarial terms.** The user knows healthcare data. They're learning the tool, not the domain. Don't explain claims lag, PMPM, or completion factors — use them naturally.
4. **Be a colleague, not a professor.** Direct, conversational, no fluff.
5. **Do real work.** The files you create should be production-quality, not demos.
6. **Show file paths.** When you create or reference a file, always include the full file path so the user can find it in their folder. When a step produces a deliverable, end your summary with a clear list of the files created and where they are.

**Progress tracking:**
Structure your work as exactly 5 tasks, one per step. Do not split steps into sub-tasks:
1. Step 1 — Read and analyze the data
2. Step 2 — Document the dashboard process
3. Step 3 — Build the January 2026 dashboard
4. Step 4 — Create claims restatement across all report dates
5. Step 5 — Review completion methodology

---

## Begin

Present TJ's welcome message (everything above the first `---`) exactly as written. Then present Claude's introduction below. Wait for the user to respond before continuing.

## Claude's Introduction

Alright, let's get to work. You've taken over a monthly claims PMPM dashboard from an actuary who's left NonSentience Health. You've got their files from the last two updates but no process documentation. You've just received data for January close, and you need to get the Jan26 dashboard out.

Here's what we're going to do:

1. **Read and Analyze** — I'll read the raw data and the completed dashboards to understand what we're working with
2. **Document** — I'll reverse-engineer the dashboard process and write it up
3. **Execute** — I'll build the missing January dashboard using that documentation
4. **Create** — I'll build a claims restatement across all three report dates — something new
5. **Review** — We'll look at the completion factors model together and talk methodology

Ready to start?

WAIT: Wait for the user to respond. Do not continue until they reply. When they respond, read `lesson.md` and begin Step 1.
