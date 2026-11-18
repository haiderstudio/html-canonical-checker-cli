# html-canonical-checker-cli

Check every HTML file carries exactly one `<link rel="canonical">` — fail CI when a page has none or more than one.

[![CI](https://github.com/haiderstudio/html-canonical-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/html-canonical-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`html_canonical_checker` reads each HTML file,
counts its `<link rel="canonical">` tags, and
reports each page with none, or with more than
one, with the file and the line number. It exits 1
when any page fails, so it can fail a CI run. A
file with exactly one canonical link exits 0.

- A page with no canonical link leaves the search
  engine to pick one itself, and two canonical
  links on one page contradict each other — both
  are silent SEO damage, found only when rankings
  slip. This names the exact line, and the fix is
  one tag per page.
- A page with no canonical link is reported once,
  on line 1, because there is no tag line to point
  at. A page with more than one is reported once
  per extra link, on the line that link sits on.
- The `rel` value is matched without regard to
  case, and a `rel` list such as
  `rel="canonical alternate"` counts — the word
  "canonical" anywhere in the `rel` value is
  enough, as HTML requires. A stylesheet or icon
  link does not count.
- A file given directly on the command line is always
  checked, whatever its name. A folder is walked for
  files ending in `.html` or `.htm` only, recursively
  by default (`--no-recursive` stops at the top
  level). `.git` folders are never walked, and
  directory links are never followed.
- `--json` prints the result as JSON, and `--stdin`
  checks one HTML document read from standard input.
- Links inside HTML comments are not links — the
  parser skips them. Markup inside `<script>` and
  `<style>` blocks is not parsed as HTML either, so
  a `"<link rel=\"canonical\">"` written in a
  JavaScript string or a stylesheet is left alone.
  Tag and attribute names are matched without
  regard to case, as HTML requires — `<LINK>` and
  `REL="CANONICAL"` are checked exactly like
  `<link>` and `rel="canonical"`.

## Who it is for

Every site owner with more than one page. One
missing canonical and the search engine guesses
which address to rank; one extra and the page
contradicts itself. Both are found by a visitor
only after rankings slip, and the fix is one tag
once the page is found. This is the gate that
stops it at the pull request.

## What it does NOT do

- It does not check what the canonical points at.
  A link to the wrong address, a relative address,
  or an address that returns a 404 all pass this
  tool. That is a different job: checking the
  canonical's target is the job of
  [kais-canonical-origin-contract](https://github.com/600me/kais-canonical-origin-contract),
  which asserts one saved page's canonical resolves
  to an explicit production origin. Origin-checking
  is its job, not this repo's.
- It does not compare canonical declarations across
  pages, a route list, or a sitemap. That
  cross-source consistency job belongs to
  [canonical-url-consistency-checker](https://github.com/edilec/canonical-url-consistency-checker).
- It does not check the `<title>` tag. That is repo
  #50, html-title-checker-cli — the title is a
  different tag on the same pages.
- It never rewrites a file, and it never touches the
  network.

## How this differs

- A fresh search of GitHub on Nov 16, 2026 found 0
  results for `"html-canonical-checker-cli"` and 7
  results for `html canonical checker`. The two
  closest — kais-canonical-origin-contract and
  canonical-url-consistency-checker, both 0 stars —
  check the canonical's target and cross-source
  consistency, not presence on every local file.
  The rest are bookmark tools, broad SEO suites,
  or web score tools.
- No rival checks canonical presence on every local
  file with a CI exit code.

## Install

```sh
git clone https://github.com/haiderstudio/html-canonical-checker-cli.git
cd html-canonical-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one HTML file:

```sh
python3 src/html_canonical_checker.py page.html
```

A file whose page carries exactly one canonical link passes:

```sh
$ python3 src/html_canonical_checker.py examples/clean.html
OK — 1 file(s) checked, every page carries exactly one canonical link.
```

A file with a page missing its canonical link fails, with the
file and line:

```sh
$ printf '<html><body>No link</body></html>\n' | python3 src/html_canonical_checker.py --stdin
FAIL <stdin>: page line 1 has no <link rel="canonical">
Checked 1 file(s), 1 canonical problem(s) in 1 file(s).
```

A file with two canonical links fails on the extra one:

```sh
$ python3 src/html_canonical_checker.py examples/flagged.html
FAIL examples/flagged.html: page line 6 extra <link rel="canonical"> — the page already has one
Checked 1 file(s), 1 canonical problem(s) in 1 file(s).
```

Check a whole folder (`.html` / `.htm` files only):

```sh
$ python3 src/html_canonical_checker.py examples/
FAIL examples/flagged.html: page line 6 extra <link rel="canonical"> — the page already has one
Checked 3 file(s), 1 canonical problem(s) in 1 file(s).
```

Machine-readable output:

```sh
$ python3 src/html_canonical_checker.py --json examples/flagged.html
{
  "files": [
    {
      "path": "examples/flagged.html",
      "findings": [
        {
          "line": 6,
          "reason": "extra <link rel=\"canonical\"> — the page already has one"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 1
}
```

Exit codes: 0 when every page carries exactly one
canonical link, 1 when any page has none or more
than one or a file cannot be read, 2 for a usage
error (a missing path, a bad flag, or no HTML files
found).

## Examples

A canonical link in a comment and one written inside
a script string are not links, and `examples/edge.html`
holds both — it passes:

```sh
$ python3 src/html_canonical_checker.py examples/edge.html
OK — 1 file(s) checked, every page carries exactly one canonical link.
```

A `rel` list that includes "canonical" counts as the
page's one link — `rel="canonical alternate"` passes:

```sh
$ printf '<link rel="canonical alternate" href="https://example.com/page">\n' | python3 src/html_canonical_checker.py --stdin
OK — 1 file(s) checked, every page carries exactly one canonical link.
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_html_canonical_checker.py
```

The tests cover canonical detection (one link passes,
no link fails on line 1, an empty document fails on
line 1, two links report the second, three links
report two extras, a `rel` list with "canonical"
counts, a `rel` list without it fails, a stylesheet
link does not count, uppercase `<LINK>` and
`REL="CANONICAL"`, a mixed-case `rel` value, a
self-closing link counts, a link split across lines
reports its start line, a canonical in the body
counts, a link without `rel` fails, a bare `rel`
fails, and the canonical's target is not checked —
a wrong, relative, or empty target still passes),
skipping (a link in a comment, a link in a script
string, a link in a style block, a real link after a
script checked, unclosed tags elsewhere in the
file), the CLI (exit 0/1/2, folder walking for
several HTML files including `.htm`, nested folders,
`--no-recursive`, `--exclude`, `.git` skipped, a
direct file checked whatever its name, duplicate
paths checked once, `--json` output, `--stdin`,
bad flags, missing paths, empty folders,
`--version`, a non-UTF-8 file reported, input files
left unchanged, the tool run from another folder
and under a changed HOME), the bundled examples
(sample output compared byte-for-byte against a
fresh run, and the README-quoted outputs checked
against it), and hygiene checks (no placeholder
text, no absolute paths, no real secrets outside
the tests and examples, stdlib imports only, no
network use in the source, `.env` first in
`.gitignore`, CI file runs the test file, README
names the neighbouring repos).

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The
idea of checking canonical links is not new, and the
parsing follows Python's own standard-library HTML
parser — but no existing tool does this one job,
checking that every local HTML file carries exactly
one canonical link, as a tested command-line gate
with a CI exit code, as the search above shows — and
every line of code here is original, built on nothing
but Python's standard library.
