# 2.2 Standardization: macros, cleanup, math and sentences

*Author: Phạm Tấn Nhật Thịnh · code: `src/11_normalize.ipynb` (`expand_macros`, `clean_latex`,
`normalize_math`, `split_sentences`; 70 self-tests)*

Two versions of a paper often say the same thing in different LaTeX: a macro in one and its expansion in the
other, `\[ ... \]` in one and `$$ ... $$` in the other, a `\centering` added to a figure. The deduplication of
chapter [2.4](deduplication.ipynb) compares the **cleaned** text, so these differences must be removed first.
The gathered text of each version goes through three functions, in this order, before the tree is built; the
fourth one cuts the prose into sentences while the tree is built.

```text
gathered text → expand_macros → clean_latex → normalize_math → (rename_cites) → build_tree ── split_sentences
```

## 2.2.1 Macro expansion — `expand_macros`

Authors define their own shortcuts (`\newcommand{\R}{\mathbb{R}}`), and a later version may write the
expansion instead of the macro. `expand_macros` reads the definitions of the document and replaces every use
by the definition:

- `\newcommand`, `\renewcommand` and `\providecommand` (starred or not, name in braces or not) with up to two
  parameters; the arguments of a use are its next brace groups (or single tokens) and replace `#1` and `#2`;
- `\def\name{...}` without parameters;
- a definition is removed from the text after it was read, and the replacement runs up to five passes, so a
  macro that uses another macro is expanded too.

Commands that carry structure (`\section`, `\begin`, `\cite`, `\label`, `\title`, `\item`, ...) are never
treated as macros, even if a class or the author redefines them: expanding `\renewcommand{\section}{...}`
would erase every section of the paper. Macros with more than two parameters, with an optional argument, or
defined by `\def` with parameters are left as they are. A recursive macro (`\newcommand{\x}{\x\x}`, invalid
in TeX) would multiply the text at every pass, so the expansion stops when the text grows past four times its
size.

**Nested definitions.** A definition may contain another one, as in the common
`\newcommand{\blfootnote}[1]{\begingroup\renewcommand\thefootnote{}\footnote{#1}\endgroup}`. Removing the
inner definition first and then the outer one by its original position cut as many characters after the
outer definition, often `\begin{document}` and the start of `\title{`; the preamble then leaked into the tree
as sentences. Only the outermost definition is removed since parser 13.8. On a local copy of the corpus,
231 versions of 25,760 had lost their `\begin{document}` this way.

## 2.2.2 LaTeX cleanup — `clean_latex`

`clean_latex` removes the commands that only control the layout, and the front matter that is not content:

| Group | Removed |
|---|---|
| alignment | `\centering`, `\raggedright`, `\raggedleft`, `\noindent`, `\par` at the start of a line |
| table rules | `\midrule`, `\toprule`, `\bottomrule`, `\hline` |
| spacing and page breaks | `\vspace{...}`, `\hspace{...}`, `\smallskip`, `\medskip`, `\bigskip`, `\newpage`, `\clearpage`, `\pagebreak`, `\linebreak` |
| float placement | the option of `figure`, `table`, `algorithm`: `[h]`, `[t]`, `[htbp]`, `[htpb]`, `[H]`, `[!t]`, ... |
| front matter | `\author{...}`, `\thanks{...}`, `\date{...}`, `\pagenumbering{...}`, `\and`, `\maketitle`, `\tableofcontents` |
| font wrappers | `\emph`, `\textit`, `\textbf`, `\textrm`, `\textnormal`, `\underline`, `\textsc`, `\texttt`, `\textsf`: the wrapper is removed, its content kept |

Dashes are written one way: `--` and `---` become ` - `, but **only outside math**, where `$a--b$` is two
minus signs. The math spans are found as TeX reads them (`\$` is not math, `\\[3pt]` is not `\[`, an
unclosed `$` stays text). Comments are removed first; at the end, runs of spaces are collapsed and blank lines
reduced to one, which keeps the paragraph breaks that `build_tree` relies on. `\cite`, `\ref`, `\label`, the sectioning
commands, the environments and all math are kept for the next steps.

## 2.2.3 Math normalization — `normalize_math`

The statement asks for inline math as `$...$` and block math as `\begin{equation}...\end{equation}`:

| Input | Output |
|---|---|
| `\( ... \)`, `\begin{math} ... \end{math}` | `$...$` |
| `$$ ... $$`, `\[ ... \]` | `\begin{equation}...\end{equation}` |
| `\begin{equation*} ... \end{equation*}` | `\begin{equation}...\end{equation}` |
| `\begin{align*}`, `\begin{gather*}` | `\begin{align}`, `\begin{gather}` (multi-line math keeps its environment) |

Each substitution stops at the last closing delimiter of the text: an opening `\[` or `$$` that is never
closed stays as it is instead of swallowing the rest of the paper.

## 2.2.4 Sentence splitting — `split_sentences`

A sentence ends at a `.` (also `!` or `?`) followed by a space and a word that starts with a capital letter,
a digit, a bracket, `$` or a command. Before splitting, the spans where a period does not end a sentence are
masked and restored afterwards:

| Never split inside | Example |
|---|---|
| inline and block math | `$x = 1.5$`, `\begin{equation} ... \end{equation}`, `$$ ... $$` |
| a command with its argument | `\cite{smith.2020}`, `\ref{sec.intro}`, `\url{...}` |
| a URL | `https://arxiv.org/abs/2310.12345` |
| a decimal number | `3.14`, `1.5e-6` |
| an abbreviation | `i.e.`, `e.g.`, `et al.`, `Fig.`, `Eq.`, `Sec.`, `Tab.`, `Ref.`, `cf.`, `vs.`, `approx.`, `etc.`, `resp.`, `w.r.t.`, `Prof.`, `Dr.`, `No.`, `vol.`, `pp.`, month names |

A fragment shorter than three characters is joined to the previous sentence. Of the 70 self-tests of the
notebook, 35 are sentence-splitting cases (the statement asks for at least 30); the others cover macro
expansion (7), cleanup (20) and math (6).
