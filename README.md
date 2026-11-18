# AI disclosure

AI transparency for Open Source projects.

A [charter](AI_CHARTER.md) (version 1.1) for projects that want to be open about the use of AI tools
in their development, and a tool that publishes what a project's contributors
declare: it reads the commits and pull requests of a project and builds a static
page of charts.

The first project followed is
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup).

The aim is transparency, not judgement: using an AI tool is welcome, and the page
describes what is declared without ranking anyone.

## What the page shows

- **Commits per month**, split by the model family named in their `Co-Authored-By`
  trailer, or "no AI declared", with the date the project started to require the
  trailer.
- **Models and versions**: commits naming each model, the months it was in use, the
  number of people who named it. Spellings of one model ("Claude Opus 4.8",
  "Claude Opus 4.8 (1M context)") are counted together.
- **Lines changed per month**, with the same split: the lines added and deleted by the
  commits that name a model, and by the others, with the few commits that weigh the
  most. These are the lines of commits naming a model, not lines written by a model.
- **Contributors**, with their GitHub profile: commits, commits declaring a model,
  the models each person names, and the same since the rule applies. Contributors
  with no AI declared are listed like the others.
- **Pull requests** opened since the template asks about AI: the state of each box
  (AI-generated part; "read, understood and tested"), the commits naming a model,
  and whether the box and the commits agree.

- **The history, in motion**: an optional [Gource](https://gource.io/) video of the
  project, where each model family named in a trailer works beside the person who
  made the commit. Files keep the colour of their type: the video does not say who
  wrote a file.

The site also has a **Good practice** page
([ai_disclosure/site/good-practice.html](ai_disclosure/site/good-practice.html)): why
declaring matters, the `Co-Authored-By` trailer, and the four files (`CONTRIBUTING.md`,
`AGENTS.md`, `CLAUDE.md`, the pull request template) that make it a habit.

"No AI declared" means exactly that: a repository cannot prove that a commit was
written without an AI tool.

## How it reads a project

| Source | What is read |
|---|---|
| A clone of the repository (history only, no file content) | Non-merge commits of the default branch: author, date, message, trailers |
| GitHub GraphQL API | The GitHub account of each commit author, the lines each commit adds and deletes, and the pull requests: description, author, commits |

A commit authored by an AI agent (for example `copilot-swe-agent[bot]`) is credited
to the person named as its co-author, with the agent as the declared model.
Automation such as Dependabot is counted apart. E-mail addresses are used to
recognise people and are never written to the published data.

## Follow a project

Add a file to `projects/`, named after the project. See
[projects/vulnerability-lookup.toml](projects/vulnerability-lookup.toml):

```toml
[project]
name = "Vulnerability-Lookup"
repository = "vulnerability-lookup/vulnerability-lookup"

[policy]
url = "https://github.com/vulnerability-lookup/vulnerability-lookup/blob/main/CONTRIBUTING.md#use-of-ai-and-llm-tools"
trailer_since = "2026-11-04"

[[policy.checkbox]]
id = "ai"                               # compared with the trailers of the commits
label = "AI-generated"
match = ["generated with an AI tool"]   # a piece of the box's text
since = "2026-11-04"

[[policy.checkbox]]
id = "human"
label = "Read and tested"
match = ["read, understood and tested"]
since = "2026-11-04"
```

[site.toml](site.toml) lists the projects the site publishes, in the order of its
overview page:

```toml
[site]
projects = ["vulnerability-lookup", "misp", "newspipe"]
```

A project file that is not listed is neither read nor published. Another site, with
another selection, has its own file: `ai-disclosure build --site other-site.toml`
(and the same option for `ai-disclosure video`). Without any site file, every
project of `projects/` is published.

With several projects, the site opens on an overview of the projects, and each
project has its own page (`?project=<file name>`), reachable from a selector too.

A co-author the built-in rules do not recognise as a model can be declared:

```toml
[[identities.model]]
match = "my-internal-agent"   # case-insensitive piece of the trailer
vendor = "Example"
family = "Example Agent"
version = "2"
```

## Build the site

Python 3.11 or later and git; no other dependency.

```bash
pip install .
ai-disclosure build            # reads projects/, writes _site/
python3 -m http.server -d _site  # then open http://localhost:8000
```

The GitHub API needs a token: `GITHUB_TOKEN` or `GH_TOKEN`, or a logged-in `gh`
command. Without one (or with `--no-github`) the page is built from git alone:
no profile pictures, no lines changed and no pull requests.

`--local SLUG=PATH` reads a project from a clone you already have.

The clones, and what GitHub says of each commit (account of the author, lines changed),
are kept in `.cache/`, so
that a later build only asks for the new commits.

## Render the videos

Optional, and needs `gource` and `ffmpeg`:

```bash
ai-disclosure video                 # every project, into .cache/video/
ai-disclosure video misp --max-age 7  # one project, unless its video is under a week old
ai-disclosure build                 # publishes the videos it finds in .cache/video/
```

Gource draws with OpenGL and needs a display. On a server, run it under
`xvfb-run -a`. `GOURCE=/path/to/gource` selects another binary. The video lasts one
to three minutes depending on the number of commits, in 1280x720 (`--size`).

## Publish with GitHub Pages

[.github/workflows/pages.yml](.github/workflows/pages.yml) builds the site on every
push to `main` and once a day, and deploys it to GitHub Pages. The videos are rendered
again once a week and kept in the workflow's cache in between. In the repository
settings, set **Pages → Source** to **GitHub Actions**.

## Tests

```bash
pip install pytest
pytest
```

## License

[AI disclosure](https://github.com/cedricbonhomme/ai-disclosure) is licensed under
[GNU General Public License version 3](https://www.gnu.org/licenses/gpl-3.0.html)


## Contact

Made by [Cédric Bonhomme](https://www.cedricbonhomme.org).
