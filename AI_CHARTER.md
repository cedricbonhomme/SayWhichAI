# AI transparency charter

Version 1.0, 18 November 2026

A short charter that a software project can adopt to say how AI tools are used in
its development. It was first written for
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup).

The charter is about **transparency, not judgement**. Using an AI tool is welcome,
whatever your experience, including when you could not have written the change
without it. What the project asks is that it is said, and that a person stands
behind every contribution.

## The commitments

1. **Say so.** A commit that was not written by a human ends with a
   `Co-Authored-By` trailer naming the model and its version:

   ```
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   ```

   A pull request says in its description when a significant part of it was
   generated with an AI tool.

2. **A human answers for it.** Every change is read, understood and tested by the
   person who submits it, whoever or whatever wrote it. That person states it in
   the pull request, in their own name. An AI tool never makes this statement for
   them.

3. **Be able to explain it.** Reviewers may ask the author to explain any part of
   a change. The author answers themselves, not with pasted model output.

4. **A human submits.** Pull requests, issues and vulnerability reports are opened
   by a person, after they have reviewed the work. An agent does not open them on
   its own.

5. **Report only what was reproduced.** An issue or a vulnerability report
   describes a problem its author has observed, not an unverified finding of a
   tool.

6. **No shame, no ranking.** Declaring the use of AI never counts against a
   contribution. The figures a project publishes about it describe what is
   declared; they are not a score.

## What "no AI declared" means

A commit without a trailer is a commit where no AI is declared. It may have been
written entirely by hand, or the trailer may have been forgotten: nothing in a
repository proves which. Anything published under this charter uses that wording
and never says that someone "does not use AI".

## Adopting the charter

A project adopts the charter by putting it into practice in four places:

| File | What it carries |
|---|---|
| `CONTRIBUTING.md` | The commitments above, in the project's own words, and the date they apply from |
| `AGENTS.md` (imported by `CLAUDE.md` and other agent files) | The same rules, addressed to AI agents: add the trailer, never tick the human's box, never open a pull request alone |
| `.github/PULL_REQUEST_TEMPLATE.md` | Two boxes, below |
| A project file in this repository | So that the declared figures are published |

The two boxes of the pull request template:

```markdown
- [ ] Was a significant part of it generated with an AI tool? (If so, the commits carry a `Co-Authored-By` trailer naming the model.)
- [ ] I have read, understood and tested every change in this pull request, and I can explain it.
```

The first is a fact about the change. The second is the author's own statement,
and only they tick it.

A project that adopts the charter says which version, for example in its
`CONTRIBUTING.md`: "This project adopts the AI transparency charter 1.0."

## What is published

For a project that adopts the charter, this repository builds a public page from
the project's history: the models and versions named in commits, the people who
contribute and the models each of them names, and, for each pull request, whether
its boxes and the trailers of its commits tell the same story.

Only public data is read, and e-mail addresses are not published. Commits made
before the project adopted the charter are shown for the history, and are not
held to a rule that did not exist.

## Versions

The charter is versioned so that a project knows what it adopted. A change of
wording that keeps the commitments raises the second number; a change to the
commitments raises the first, and projects choose when to move to it.

| Version | Date | Changes |
|---|---|---|
| 1.0 | 18 November 2026 | First version, from the rules of Vulnerability-Lookup |
