# AI disclosure

AI transparency for Open Source projects: **<https://www.saywhichai.org>**

A [charter](AI_CHARTER.md) (version 1.3) for projects that want to be open about the use of AI tools
in their development, and a tool that publishes what a project's contributors
declare: it reads the commits and pull requests of a project and builds a static
page of charts.

The site presents the practice, how to adopt it, and
[a few projects followed as examples](https://www.saywhichai.org/projects.html). The
first one was
[Vulnerability-Lookup](https://github.com/vulnerability-lookup/vulnerability-lookup).

The aim is transparency, not judgement. The project takes no side on the use of AI
tools; it asks that the use be open. The page describes what
is declared without ranking anyone.

## What the page shows

- **Commits per month**, split by the model family named in their `Co-Authored-By`
  trailer (an `Assisted-by` or `Generated-by` trailer naming a model is read too), or
  "no AI declared", with the date the project started to require the
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

A **Policies** page
([ai_disclosure/site/policies.html](ai_disclosure/site/policies.html)) compares the
rules of other projects, and drafts a short statement a project could make about
what it accepts.

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

When the commit subjects of a project follow a convention, such as `fix: [security] ...`,
a `[subjects]` table gives it as a regular expression with a `kind` group, a `scope`
group, or both. The page then shows, for each kind and each scope, the share of
commits naming a model beside the share of all the commits. These figures are not
reliable on their own: nothing checks the label an author gives a commit.

```toml
[subjects]
pattern = '^(?P<kind>[a-z]+)(?=:|\s*\[):?\s*(?:\[(?P<scope>[^\]]+)\])?'
aliases = { docs = "doc", documentation = "doc" }   # spellings counted as one
```

An `[advisories]` table asks
[Vulnerability-Lookup](https://vulnerability.circl.lu) once a day for the
vulnerability records that cite a commit of the repository among their references.
The page then lists these commits and shows how many of them name a model. A record
that cites a commit is a firmer sign of a fix than a label, but not a proof. The
answer is kept in `.cache/`. When the service cannot be reached, the last answer is
used, and `--no-advisories` leaves the search out.

```toml
[advisories]
# sources = ["cvelistv5"]   # the sources searched; the CVE records by default
```

[site.toml](site.toml) lists the projects the site publishes, in the order of its
project menu (the overview page sorts them by the share of commits declaring a model):

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

When the repository of a project has an `ai-policy.yaml` file
([the proposal](https://codeberg.org/open-source-ecosystem/ai-policy), version 1), its
page shows what the project states there, beside what its commits declare. Nothing
has to be configured. The tool reads the file with a small YAML reader of its own; a
file it does not fully understand is reported as unreadable, never half shown. This
repository has [its own](ai-policy.yaml).

The overview shows the picture of the organisation that owns the repository. A
project can name its own logo instead, an image of its repository (PNG, JPEG, WebP,
GIF or SVG, 512 kB at most) that the tool copies to the site. An SVG file is copied
only when it is a plain drawing, with no script, no style sheet and nothing loaded
from elsewhere:

```toml
[project]
logo = "docs/logo.png"
```

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
ai-disclosure video --max-age 7 --due # only list the projects whose video would be rendered
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

The code of [AI disclosure](https://github.com/cedricbonhomme/ai-disclosure) is licensed
under the [GNU Affero General Public License](https://www.gnu.org/licenses/agpl-3.0.html),
version 3 or any later version.

The texts are meant to be copied and adapted by other projects: the
[charter](AI_CHARTER.md) and the texts of the Good practice and Policies pages are
licensed under [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0).


## Contact

Made by [Cédric Bonhomme](https://www.cedricbonhomme.org).
