# AGENTS.md

Instructions for AI coding agents working on AI disclosure, whatever the tool.

## Rules for AI agents

These rules come from the "Spirit of the project" and "Use of AI and LLM tools"
sections of [CONTRIBUTING.md](CONTRIBUTING.md), and from the
[AI transparency charter](AI_CHARTER.md) that this project adopts. They are
mandatory. Read CONTRIBUTING.md too: it is the reference, and it wins if the two
files ever disagree.

- **Keep the spirit of the project.** Describe, do not judge: write "no AI declared",
  never "does not use AI", write "lines changed in commits naming a model", never
  "lines written by AI", and do not rank people. Never write an e-mail address to
  the published data. Python uses the standard library only; the site is plain HTML,
  CSS and browser-native JavaScript, with no framework and no build step. Insert text
  that comes from a repository with `textContent`, never as HTML. Add no dependency
  without a justification.
- **Stay in scope.** Keep changes minimal and focused on the task. Do not reformat,
  rename, or rewrite unrelated code or comments.
- **Check what you produce.** Run `pytest` before handing your work over, look at the
  page when you change the site, and say plainly what you could not verify. The human
  you work with must read, understand and test every change before submitting it.
- **Make it explainable.** Explain every change to the human you work with. Reviewers
  may ask them to explain any part of it. Do not write their answers to review
  comments for them to paste.
- **A human reviews and submits.** Never open a pull request or an issue on your own;
  the decision is the human's, after they have reviewed your work.
- **Report only what was reproduced.** When you help write an issue, the human must
  have observed the problem. Never present an unverified finding as a confirmed one.
- **Say so.** End every commit you author with a `Co-Authored-By` trailer naming the
  model and its version, for example:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

  When you draft a pull request description, follow
  [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) and keep all
  its sections, and mention that a significant part of the change was generated with
  an AI tool. Never tick the box "I have read, understood and tested every change":
  it is the human's own statement, leave it for them.
- **The charter has a version.** When you change a commitment of
  [AI_CHARTER.md](AI_CHARTER.md), raise its version (second number for an addition,
  first for a change or a removal) and add a line to its table of versions.

## Project overview

A charter for projects that want to be open about the use of AI tools, and a tool
that reads the commits and pull requests of the projects listed in `projects/` and
builds a static site of charts from what their contributors declare.

## Key commands

```bash
pip install -e . pytest        # in a virtual environment
pytest                         # the tests
ai-disclosure build            # reads projects/, writes _site/
ai-disclosure build --no-github  # from git alone: no profiles, no lines, no pull requests
python3 -m http.server -d _site
```

The GitHub API needs `GITHUB_TOKEN` or `GH_TOKEN`, or a logged-in `gh`. Clones and
the GitHub account of each commit author are cached in `.cache/`.

## Important paths

- `ai_disclosure/models.py`: recognises a model in a `Co-Authored-By` trailer
  (vendor, family, version). A person must never be taken for a model: add a test in
  `tests/test_models.py` with every new rule.
- `ai_disclosure/config.py`: the project files of `projects/*.toml`, and `site.toml`,
  the list of the projects a site publishes (`--site` selects another list).
- `ai_disclosure/gitlog.py`, `ai_disclosure/github.py`: reading the commits, the
  GitHub accounts and the pull requests.
- `ai_disclosure/report.py`: builds the published JSON of a project.
- `ai_disclosure/gource.py`: the optional Gource video of a project (`ai-disclosure
  video`, needs `gource` and `ffmpeg`). Models appear as users; a file is never
  coloured after who changed it, because a trailer does not say how much of a file a
  model wrote.
- `ai_disclosure/cli.py`: the `ai-disclosure` command.
- `ai_disclosure/site/`: the static site (`index.html`, `app.js`, `style.css`,
  `good-practice.html`), copied as is to the output.
- `AI_CHARTER.md`: the charter.
- `.github/workflows/pages.yml`: tests, build and deployment to GitHub Pages, on
  every push to `main` and once a day.
