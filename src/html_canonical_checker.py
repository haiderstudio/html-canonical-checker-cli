#!/usr/bin/env python3
"""Check every HTML file carries exactly one canonical link.

Run: python3 src/html_canonical_checker.py page.html
     python3 src/html_canonical_checker.py site/
     python3 src/html_canonical_checker.py --stdin < page.html

A page with no canonical link leaves the search
engine to pick one itself, and two canonical links
on one page contradict each other — both are silent
SEO damage, found only when rankings slip. This
tool reads each HTML file, counts its <link
rel="canonical"> tags, and reports each page with
none, or with more than one, with the file and the
line number. It exits 1 when any page fails, so it
can fail a CI run. A file with exactly one
canonical link exits 0.

A page with no canonical link is reported once, on
line 1, because there is no tag line to point at.
A page with more than one is reported once per
extra link, on the line that link sits on. The
rel value is matched without regard to case, and a
rel list such as rel="canonical alternate" counts
— the word "canonical" anywhere in the rel value
is enough, as HTML requires.

What the canonical points at is NOT checked here.
A link to the wrong address, a relative address,
or an address that returns a 404 all pass this
tool — that is a different job, and the README
names the tool that does it. This tool checks
presence only: exactly one canonical link per page.

A file given directly on the command line is always
checked, whatever its name. A folder is walked for
files ending in .html or .htm only, recursively by
default (--no-recursive stops at the top level).
.git folders are never walked, and directory links
are never followed.

Links inside HTML comments are not links — the
parser skips them. Markup inside <script> and
<style> blocks is not parsed as HTML either, so a
"<link rel=\"canonical\">" written in a JavaScript
string is left alone. Tag and attribute names are
matched without regard to case, as HTML requires.

It never rewrites a file, never touches the network,
and reads only the files and folders you point it at.
"""

import argparse
import fnmatch
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path

__version__ = "1.0.0"

HTML_SUFFIXES = (".html", ".htm")


class CanonicalParser(HTMLParser):
    """Collect the lines of every canonical link.

    HTMLParser already treats <script> and <style>
    content as character data, so markup written
    inside those blocks never reaches handle_starttag.
    Comments never reach it either.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        values = dict(attrs)
        rel = values.get("rel") or ""
        if "canonical" in rel.lower().split():
            line, _offset = self.getpos()
            self.lines.append(line)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def check_text(text):
    """Check one document's text.

    Returns a list of findings, each {"line": int,
    "reason": str}, in document order.
    """
    parser = CanonicalParser()
    parser.feed(text)
    parser.close()
    if not parser.lines:
        return [{"line": 1,
                 "reason": "has no <link rel=\"canonical\">"}]
    if len(parser.lines) == 1:
        return []
    return [{"line": line,
             "reason": "extra <link rel=\"canonical\"> — "
                       "the page already has one"}
            for line in parser.lines[1:]]


def check_file(path):
    """Check one file. Returns (findings, error)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], "not valid UTF-8"
    except OSError as exc:
        return [], str(exc)
    try:
        return check_text(text), None
    except Exception as exc:  # malformed markup the parser rejects
        return [], "could not be parsed: %s" % exc


def _is_html_file(path):
    return Path(path).name.lower().endswith(HTML_SUFFIXES)


def collect_files(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of HTML files.

    A file given directly is always checked, whatever its
    name. A folder is walked for files ending in .html
    or .htm only. .git folders are never walked, and
    directory links are never followed.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(str(path))
        elif path.is_dir():
            for dirpath, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if d != ".git"
                    and not any(fnmatch.fnmatch(d, pat) for pat in exclude)
                ]
                for name in files:
                    candidate = Path(dirpath) / name
                    if not _is_html_file(candidate):
                        continue
                    if any(
                        fnmatch.fnmatch(str(candidate), pat)
                        or fnmatch.fnmatch(name, pat)
                        for pat in exclude
                    ):
                        continue
                    found.append(str(candidate))
                if not recursive:
                    break
        else:
            raise FileNotFoundError("no such file or folder: %s" % raw)
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one failing page."""
    return ("FAIL %s: page line %d %s"
            % (path, finding["line"], finding["reason"]))


def run(paths, recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        files = collect_files(paths, recursive=recursive, exclude=exclude)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not files:
        print("error: no HTML files found", file=sys.stderr)
        return 2
    results = []
    findings = 0
    files_with_findings = 0
    for path in files:
        bad, error = check_file(path)
        count = len(bad) + (1 if error else 0)
        if count:
            findings += count
            files_with_findings += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"files": results, "checked": len(files),
             "findings": findings},
            indent=2, ensure_ascii=False))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if findings:
            print("Checked %d file(s), %d canonical problem(s) "
                  "in %d file(s)." % (len(files), findings,
                                      files_with_findings))
        else:
            print("OK — %d file(s) checked, every page carries "
                  "exactly one canonical link." % len(files))
    return 1 if findings else 0


def run_stdin(as_json=False):
    """Check one HTML document read from standard input."""
    text = sys.stdin.read()
    bad = check_text(text)
    findings = len(bad)
    if as_json:
        print(json.dumps(
            {"files": [{"path": "<stdin>", "findings": bad,
                        "error": None}],
             "checked": 1, "findings": findings},
            indent=2, ensure_ascii=False))
    else:
        for finding in bad:
            print(format_finding("<stdin>", finding))
        if findings:
            print("Checked 1 file(s), %d canonical problem(s) "
                  "in 1 file(s)." % findings)
        else:
            print("OK — 1 file(s) checked, every page carries "
                  "exactly one canonical link.")
    return 1 if findings else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="html_canonical_checker",
        description="Check every HTML file carries exactly "
                    "one <link rel=\"canonical\">, fail CI "
                    "when a page has none or more than one.")
    parser.add_argument("paths", nargs="*",
                        help="HTML files or folders to walk")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files or folders matching this pattern "
                             "(repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--stdin", action="store_true",
                        help="check one HTML document from standard input")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    args = parser.parse_args(argv)
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no file or folder arguments")
        return run_stdin(as_json=args.json)
    if not args.paths:
        parser.error("give at least one HTML file or folder")
    return run(args.paths, recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
