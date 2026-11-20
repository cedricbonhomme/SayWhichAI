# Contributing

Contributions are welcome: a bug report, an idea, a project file for a project you
would like to see followed, a model the tool does not recognise, a correction to the
charter or to the good-practice page.

```bash
git clone https://github.com/cedricbonhomme/ai-disclosure.git
cd ai-disclosure/
python3 -m venv .venv && . .venv/bin/activate
pip install -e . pytest
pytest
```

A pull request is much more welcome when it follows an issue that explains the
rationale: the problem or the need, why it matters, and the approach you propose.
Small fixes, such as a typo or an obvious bug, can go straight to a pull request.

Commit messages follow the form `new: [scope] ...`, `chg: [scope] ...` or
`fix: [scope] ...`, where the scope is the part touched (`site`, `charter`,
`report`, `projects`, ...).


## Spirit of the project

The project is meant to help everybody: people who use AI tools, and people who do
not. These principles apply to every contribution, whether it is written by a human
or with the help of an AI agent.

**Describe, do not judge.**
The pages show what contributors declare. They do not rank people, and they do not
present the use of an AI tool, or its absence, as a quality or a fault.

- Write "no AI declared", never "does not use AI": a repository cannot prove that a
  commit was written without an AI tool.
- Lines are "lines changed in commits naming a model", never "lines written by AI":
  a trailer does not say who wrote each line.
- The figures are a lower bound. Do not word a chart or a sentence as if they were
  a measure.

**Publish little.**
E-mail addresses are used to recognise people and are never written to the published
data. People are shown under their public GitHub profile. Do not add personal data
to what the tool publishes.

**A small tool.**

- Python: the standard library only. Adding a dependency is an exception that must
  be justified in the pull request.
- The site is plain HTML, CSS and browser-native JavaScript: no framework, no
  TypeScript, no build step, no file loaded from another server except the GitHub
  profile pictures.
- Text coming from a repository (names, titles, messages) is untrusted: insert it
  with `textContent`, never as HTML.

**The charter has a version.**
[AI_CHARTER.md](AI_CHARTER.md) is adopted by other projects. Adding a commitment
raises the second number of its version; changing or removing one raises the first.
Add a line to its table of versions with every change.


## Use of AI and LLM tools

This project adopts the [AI transparency charter](AI_CHARTER.md) 1.3.

AI tools are used in the development of this project, and AI-assisted contributions
are accepted. Contributions written without any AI tool are accepted in the same way:
nobody has to use one, and nobody has to explain why they do not. In both cases a pull
request is the responsibility of the person who submits it.

- **Say so.** Mention in the pull request description when a significant part of the
  change was generated with an AI tool, and end each commit that was not written by
  a human with a `Co-Authored-By` trailer naming the model and its version, for
  example:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```
- **A human answers for it.** Every change in a pull request must be read,
  understood and tested by its author before it is opened, whoever or whatever wrote
  it. Say it in the pull request: keep the template's sections, and tick its last
  box yourself.
- **Be able to explain it.** Reviewers may ask you to explain any part of your
  change. Answer review comments yourself, not with pasted LLM output.
- **A human submits it.** Pull requests opened by an agent on its own, without a
  human author who reviewed them, will be closed.
- **Report only what was reproduced.** The same applies to issues: report a problem
  that you have observed yourself, and describe what you observed.
- **No shame, no ranking.** Declaring the use of an AI tool is never held against a
  contribution. It is reviewed like any other.
- **No one has to use AI.** Nothing in the project's workflow requires an AI tool,
  and a contribution is not expected to be faster or larger because such tools exist.

If you are an AI agent: follow this document, keep your changes minimal and within
the scope of the task, and leave the decision to open a pull request to the human
you work with, after they have reviewed your changes.

These rules are repeated in [AGENTS.md](AGENTS.md), which every AI agent reads, and
summarised for tools in [ai-policy.yaml](ai-policy.yaml). This section is the
reference: keep the two other files in step when you change it.
