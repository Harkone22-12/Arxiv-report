# 2.1 Hierarchical parsing

*Author: Võ Nguyễn Vân Anh · code: `src/10_parse_tree.ipynb` (`find_root`, `gather`, `build_tree`)*

A version folder holds the `.tex` files of one submission, often several: a main file, one file per section,
a preamble, figures drawn in TikZ, sometimes a cover letter or a rebuttal. Three functions turn it into one
tree: `find_root` chooses the file that LaTeX would compile, `gather` builds the text that LaTeX would read
from it, and `build_tree` reads the structure of that text. The parser is lexical: it reads LaTeX commands
with regular expressions and a brace matcher, and does not run TeX. Every rule below is checked by the
regression tests of the notebook (71 tests).

## 2.1.1 Reading the files

Files are decoded as UTF-8 and, when that fails, as Latin-1 (every byte is then a character, so nothing is
lost). Line ends are normalized: TeX ends a line at a carriage return as well as at a line feed, and a few
files of the corpus were saved with carriage returns only (the old Mac format). Read as they are, such a file
is a single line, and a `%` on its first line comments out the whole document, `\documentclass` included.
This was found in the full run (two versions without a root) and fixed in parser 13.8.

Comments are removed before anything else is searched: a `%` that is not escaped as `\%` starts a comment up
to the end of the line, and the `comment` environment is dropped. `verbatim`-like environments are kept as
they are. A commented-out `\input` is therefore not followed, as the statement asks.

## 2.1.2 Finding the root

Every `.tex` file is a candidate **entry**. From each entry, the inclusions are followed as LaTeX would (the
next section), and the entry is a possible root when a `\documentclass` is reached, either in the entry itself
or in a file it includes: a `main.tex` that starts with `\input{preamble}` is the root even when
`\documentclass` is written in `preamble.tex`. Then:

- a file that another candidate includes is not a root (a section file that happens to have its own
  `\documentclass` for separate compilation);
- a file of class `standalone` or `subfiles` is a part of the paper, not the paper;
- among the remaining candidates, a score prefers the file where the document body starts
  (`\begin{document}` in the file itself, else reachable through its inclusions, and `\end{document}`
  reachable), a name like `main` or `ms`, and more files reached; a name like `rebuttal`, `response` or
  `supplementary` lowers the score.

A version whose files never reach a `\documentclass` has no root (`no_root`, chapter [3.1](statistics.ipynb)):
in the corpus these are Plain TeX papers.

## 2.1.3 Gathering a multi-file document

`gather` starts from the root and replaces each inclusion command by the text of the file it names,
recursively and in the order of the text. Only files reached from the root are read, so a file that the root
does not include (an old draft, a cover letter) never enters the document.

| Command | Handling |
|---|---|
| `\input{f}`, `\input f`, `\include{f}` | the file `f` or `f.tex`; a name with dots (`Sections/1.Introduction`) is also tried with `.tex` added |
| `\subfile{f}` | only the document body of `f`, without its preamble and `\begin{document}` |
| `\import{dir}{f}`, `\subimport{dir}{f}`, `\inputfrom`, `\includefrom` | `f` in `dir`; the files that `f` includes are then looked up in `dir` too |
| inclusion inside braces (`\resizebox{..}{!}{\input{table}}`, `\IfFileExists{f}{\input{f}}{}`) | followed |
| inclusion inside a macro definition (`\newcommand`, `\def`, `\newenvironment`) | not followed: a macro body is not compiled until the macro is used |

Paths are resolved against the folder of the root (or of the active `\import`), then against the folder of
the including file. A file included twice is included twice, as in LaTeX; a cycle (`a` includes `b`
includes `a`) is cut and reported. A missing file (typically a `.bbl` or a style file that Milestone 1 did
not keep) leaves the command out and is reported; the version is still parsed. To stay bounded on unusual
inputs, the expansion stops at a depth of 64, 10,000 inclusions or 20 million characters.

## 2.1.4 Building the tree

`build_tree` receives the gathered text after normalization (chapter [2.2](normalization.md)) and reads the
document body, between `\begin{document}` and `\end{document}`. The title (`\title{...}`) becomes the
content of the `document` node; an abstract written in the preamble is moved into the body.

**Levels.** The sectioning commands have fixed ranks: `\part` and `\chapter` 1 (kind `chapter`), `\section`
2, `\subsection` 3, `\subsubsection` 4, `\paragraph` 5 and `\subparagraph` 6 (kind `paragraph`), starred or
not, with or without a short title. A new heading closes every open heading of the same or a lower rank and
becomes the child of the nearest open heading of a higher rank, or of the document. The depth of the tree
therefore comes from the document: in a paper without chapters the sections hang under the document, and in
a short note that only uses `\subsection`, the subsections do.

**Leaves.**

| Leaf | Source |
|---|---|
| `formula` | block math environments: `equation`, `align`, `gather`, `multline`, `eqnarray`, `flalign`, `alignat`, `displaymath`, `dmath` (starred or not), after normalization (chapter [2.2](normalization.md)) |
| `figure` | `figure`, `table`, `wrapfigure`, `sidewaysfigure`/`table`, `longtable`, `subfigure`/`subtable`, `algorithm`, `algorithmic`, a bare `tabular`, `tikzpicture`, `listing`, `deluxetable`; the content is the cleaned environment (caption, graphics file name, table cells), so a table counts as a figure, as the statement says |
| `sentence` | the remaining prose, cut into paragraphs at blank lines, then into sentences by `split_sentences` (chapter [2.2](normalization.md)); a sentence without any word (left over from removed commands) is dropped |

**Lists.** `itemize`, `enumerate`, `description` and the `paralist` variants become an `itemize` node whose
children are `item` nodes (content: the optional label of `\item[...]`), each holding the sentences, formulas
and nested lists of its item.

**Included and excluded parts.**

- The **references** are not part of the hierarchy: a section titled *References*, *Bibliography*, *Works
  cited* or *Literature cited* (or `\refname`, `\bibname`) is skipped up to the next heading of the same or a
  higher rank, together with `thebibliography`, `\bibliography{...}`, `\printbibliography` and `\bibitem`
  lines written outside a bibliography environment. The references are extracted separately (chapter
  [2.3](references.md)).
- **Acknowledgements** (a section of that name, or the `acknowledgements` environments) and every section
  after `\appendix` or inside `appendices` are kept, numbered or not.
- Other environments (`theorem`, `proof`, `center`, `quote`, ...) keep their content in place, under the
  current heading.

**Malformed input.** Real sources are not always well formed, and one problem must not lose the whole
version. An environment whose `\end` is missing is closed at the next `\end` of the same name, or its
`\begin` marker alone is dropped and parsing goes on. Each of these cases is reported as a warning and
covered by a regression test.

## 2.1.5 Output

The result is a nested tree of `{kind, content, children}` nodes, the interface agreed with notebook `13`,
which gives every node its `element_id` (chapter [2.4](deduplication.ipynb)). The tree is checked before
any ID is given (a single root of kind `document`, leaves without children, known kinds); a version whose
tree fails the check is recorded as `error`.
