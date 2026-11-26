# AGENTS.md

Instructions for AI coding agents working on Say which AI, whatever the tool.

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
  first for a change or a removal) and add a line to its table of versions. Change
  `saywhichai/site/charter.html`, its page on the site, in the same way.

## Project overview

A charter for projects that want to be open about the use of AI tools, and a tool
that reads the commits and pull requests of the projects listed in `projects/` and
builds a static site of charts from what their contributors declare.

## Key commands

```bash
pip install -e . pytest        # in a virtual environment
pytest                         # the tests
pytest tests/test_models.py -k claude    # one file, or the tests matching a word
saywhichai build               # reads projects/, writes _site/
saywhichai build --no-github     # from git alone: no profiles, no lines, no pull requests
saywhichai build --local saywhichai=.    # read a project from a clone you already have
python3 -m http.server -d _site
```

The site reads its data with `fetch`: look at it through the local server, not by
opening the files. The workflow runs `pytest` only; no linter or type checker is run.

The GitHub API needs `GITHUB_TOKEN` or `GH_TOKEN`, or a logged-in `gh`. Clones and
the GitHub account of each commit author are cached in `.cache/`.

## How a build works

`saywhichai build` (`cli.py`) does the same for each project listed in the site file:

1. `gitlog.py` clones the repository into `.cache/<slug>.git` (bare, without file
   content) or refreshes it, and reads the commits of the default branch.
2. With a token, `github.py` asks the GraphQL API for the account of each commit
   author, the lines of each commit and the pull requests. The answers are kept in
   `.cache/<slug>-accounts.json` and `.cache/<slug>-lines.json`, so that a later build
   asks for the new commits only.
3. `report.py` puts the two together into one dictionary, written to
   `_site/data/<slug>.json`. `models.py` decides which co-author is a model. This is
   where e-mail addresses stop: people leave `report.py` under their GitHub account
   or their name.
4. `cli.py` writes the badges, `data/index.json` (the overview) and, from all the
   reports, `data/stats.json` (`stats.py`).

The pages of `saywhichai/site/` are copied as they are, the HTML ones with their meta
tags filled in (`meta.py`). Nothing is rendered in Python: `app.js` fetches
`data/index.json`, `data/<slug>.json` (the page of a project is `?project=<slug>`) or
`data/stats.json` and draws every chart and table in the browser. A new figure is
therefore a change in three places: `report.py` or `stats.py` for the JSON, `app.js`
for the drawing, and a test in `tests/`.

The tests build `Project` and `Commit` objects by hand and never reach the network:
only `gitlog.mirror`, `github.py` and `advisories.py` do.

## Important paths

- `saywhichai/models.py`: recognises a model in a `Co-Authored-By`, `Assisted-by` or `Generated-by` trailer
  (vendor, family, version). A person must never be taken for a model: add a test in
  `tests/test_models.py` with every new rule.
- `saywhichai/config.py`: the project files of `projects/*.toml`, and `site.toml`,
  the list of the projects a site publishes (`--site` selects another list).
- `saywhichai/gitlog.py`, `saywhichai/github.py`: reading the commits, the
  GitHub accounts and the pull requests.
- `saywhichai/report.py`: builds the published JSON of a project.
- `saywhichai/policy.py`: reads the `ai-policy.yaml` file of a project, what the
  project states about AI in its own repository. `saywhichai/yamlsubset.py` is the
  small YAML reader it uses: it refuses what it does not understand and never guesses.
- `ai-policy.yaml`: this project's own statement. It is a summary of the "Use of AI
  and LLM tools" section of CONTRIBUTING.md: keep the two in step.
- `saywhichai/advisories.py`: asks Vulnerability-Lookup for the vulnerability records
  that cite a commit of a project, for the projects with an `[advisories]` table.
- `saywhichai/logo.py`: decides whether the logo a project file names may be
  published. An SVG file is refused unless it is a plain drawing; it is never repaired.
- `saywhichai/badge.py`: the badges of a project, SVG images for its README: what its
  commits declare, and what its ai-policy.yaml file states.
- `saywhichai/meta.py`: the meta tags of each page, `robots.txt`, `sitemap.xml` and
  `.well-known/security.txt`. The address of the site (`url`) and the fields of
  security.txt (`[site.security]`) come from the site file; without `url`, no absolute
  link is written.
- `saywhichai/stats.py`: adds the reports up into the statistics page. It names no
  project and no person: the page is not a ranking.
- `saywhichai/gource.py`: the optional Gource video of a project (`saywhichai
  video`, needs `gource` and `ffmpeg`). Models appear as users; a file is never
  coloured after who changed it, because a trailer does not say how much of a file a
  model wrote.
- `saywhichai/cli.py`: the `saywhichai` command.
- `saywhichai/site/`: the static site (`index.html`, `projects.html`, `stats.html`, `app.js`,
  `theme.js`, `style.css`, `good-practice.html`, `policies.html`, `charter.html`), copied as is to the output.
- `AI_CHARTER.md`: the charter.
- `.github/workflows/pages.yml`: tests, build and deployment to GitHub Pages, on
  every push to `main` and once a day.
