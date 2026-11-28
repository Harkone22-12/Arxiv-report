# 2.3 References: BibTeX extraction and deduplication

*Author: Lưu Minh Quân · code: `src/12_bibtex.ipynb` (`extract_bib`, `bib_source`, `dedup_bib`, `rename_cites`;
41 offline tests)*

`parse_paper` calls this step on the **gathered** text of each version (comments removed, `\input` and
`\include` expanded, chapter [2.1](hierarchy.md)), before the text is normalized and the tree is built:
the renamed `\cite` keys must be in the text before identical elements are matched (chapter
[2.4](deduplication.ipynb)).

## 2.3.1 Where the references of a version come from

Each version gets exactly one source label:

| Source label | Rule |
|---|---|
| `bib` | `.bib` files named by `\bibliography{a,b}` or `\addbibresource{x.bib}` (path or base name, case-insensitive) |
| `bibitem` | a `thebibliography` block with `\bibitem` entries written in the `.tex` |
| `bbl` | no usable `.bib`, entries recovered from a `.bbl` file (classic or biblatex) |
| `missing_bbl` | a bibliography is declared, but neither its `.bib` nor a `.bbl` is in the source folder |
| `none` | no bibliography at all |

The `.bib` parser is our own (standard library only). It handles nested braces, `"..."` values, `@string`
macros, `#` concatenation, `@comment` and `@preamble`, and skips a broken entry instead of stopping the file.

**Only cited entries are kept.** A `.bib` file is often a shared library: one paper of a test sample declares
a `.bib` of 864 entries and cites 19 of them, and some papers ship a whole bibliography database of tens of
thousands of entries. BibTeX prints only the cited entries, so the parser keeps the entries whose key appears
in a `\cite`-family command of that version; `\nocite{*}`, and versions without any `\cite`, keep every
entry.

**About `.bbl` files and hand-written reference lists.** Some authors upload only the compiled `.bbl` and not
the `.bib`. Asked how to handle these versions (Q&A M1 #18, M2 #2), the instructor advised attempting to
convert `.bbl` back into BibTeX entries directly for the `bibtex` table (without needing to emit intermediate
`.bib` files if the downstream pipeline does not require them) and documenting the approaches tried and any
remaining losses. Our parser therefore implements converters for both `.bbl` formats: classic `.bbl` files
(a `\bibitem` list parsed by the same extractor as in-`.tex` `\bibitem` entries) and biblatex `.bbl` files
(`\entry … \endentry` records). On our 32-paper validation sample downloaded with `.bbl` files, all 4 `.bbl`
versions were converted cleanly (section 2.3.6). On the full Milestone 1 corpus, however, only `.tex` and
`.bib` files were kept per the Milestone 1 requirement, so no `.bbl` file is present on Drive: **2,231 of the
25,767 TeX versions (8.66%)** declare a `.bib` that was not uploaded and are recorded as `missing_bbl`, while
**496 versions (1.92%)** have no bibliography declaration or `thebibliography` block (`none`, which includes
papers whose authors typed references by hand under a `\section{References}` heading; those prose lists are
excluded from the hierarchy and not scraped). Recovering the `missing_bbl` references would require
re-downloading those 2,231 versions with their `.bbl` files (~2 hours at 3 s/request); the parser is ready
for them, and we record this as the main known bibliography loss of Milestone 2 (chapter [3.5](statistics.ipynb)).

## 2.3.2 Converting `\bibitem` to BibTeX

A `\bibitem` is free text, so fields are recovered with regular expressions—with one structured exception
added in parser **13.9** (27 Nov 2026):

- **REVTeX (`apsrev4-1` / `apsrev4-2`) items.** Many physics papers paste compiled REVTeX `\bibitem` blocks
  between `\BibitemOpen` and `\BibitemShut{NoStop}`, where every field is wrapped in `\bibinfo{author}{…}`,
  `\bibinfo{title}{…}`, `\bibinfo{journal}{…}`, etc. Through parser 13.8, these were parsed as free text,
  leaving raw macro names in titles and authors (e.g. `BibitemOpen K. Ahnert…`) and splitting journals at
  `Phys.` (`Lett`). Since parser 13.9 (`revtex_to_fields`, verified by `test_revtex_bibitems`), `\bibinfo`
  fields are read directly, and REVTeX items without `\bibinfo` have their wrapper macros stripped before
  free-text parsing. Across the 190 papers containing `\BibitemOpen` in any `.tex` or `.bbl` file, entries
  containing macro names in their title or authors dropped from 10,727 to 0, entries with extracted authors
  rose from 6,282 to 11,325, all 11,597 items carrying `\bibinfo{title}` recovered their title, and the 3,755
  Physical Review items without a title (journal/volume/page only) now leave `title` empty rather than
  storing corrupted text.

For every other `\bibitem`, the most reliable rules run first:

1. **Identifiers.** DOI (from `\doi{}`, `doi.org/` links or `doi:` text), URL, arXiv ID and year (the year in
   parentheses, a year written right after the title, otherwise the last year in the text).
2. **Layout of the text.** Six layouts cover the styles found in the corpus:
   - `\newblock` blocks (natbib/BibTeX styles, and every classic `.bbl`): authors, then title, then venue;
   - IEEE: ``` A. Author, ``Title,'' \emph{Venue} ```;
   - Springer LNCS: `Author, A.: Title. Venue (year)`;
   - small-caps authors (JFM): `\textsc{Author, A. \& Author, B.} 2003 Title. \textit{Journal} …`;
   - emphasized title after the authors (amsplain, JHEP): `Authors, \emph{Title}, Venue`, where `\bysame`
     repeats the previous authors and `DES collaboration` counts as an author;
   - elsarticle and many math styles: `A. B, C. D, Title, Venue vol (year) pages`.

   A text that fits none of them is split as `Authors. Title. Venue.`
3. **Venue.** The emphasized text after the title becomes `journal`, or `booktitle` when the text reads
   `In …`, `Proceedings`, `Conference`, and so on.

A person name is detected per comma segment: one to five capitalized words or initials, with particles such
as *van der* allowed. The raw text of every item is kept in a private field, so nothing is lost when a rule
fails.

## 2.3.3 Deduplication inside and across versions

Every entry of every version is a node. A union–find merges two nodes when **one** rule holds:

1. the same key appears twice in one version;
2. both entries have the same **DOI**;
3. both entries have the same **arXiv ID**, taken from `eprint`, the URL, `arXiv preprint …`, or an arXiv DOI;
4. both entries have the same **normalized title** (LaTeX and accents removed, lower case, only letters and
   digits, so `Rayleigh-Bénard` and `Rayleigh--B\'enard` are equal) and compatible years (equal, or one is
   missing). Titles shorter than four words also need the same first-author surname;
5. the **same key appears in two versions**, **both** entries have a title, and the titles share at least
   60% of their words. Purely numeric keys (`15`) never use this rule, because numbered reference lists are
   renumbered between versions.

Rules 2–4 are what the statement asks for: entries that point to the same underlying work. **Rule 5 is a
choice of our group**: it only catches a title that was edited between versions while the key stayed the
same, and it never merges on the key alone. A merge is **refused** when the two groups carry different DOIs
or different arXiv IDs, which keeps apart two different works that share a generic title.

For each group, the **chosen key** is the key used in the newest version; when that version has two
duplicate keys, the one cited most often wins. The **fields are unioned** over all members, newer values
winning on conflicts. If the same key names two different works, the older one gets a suffix (`smith_2`).

The statement's example is one of the tests. Version 1 cites `vaswani2017`, versions 2 and 3 cite
`vit_transformer`, with a DOI added in version 2 and the year dropped in version 3. The result is one row
keyed `vit_transformer` with title, authors, year and DOI, and the key map
`{1: {vaswani2017 → vit_transformer}}`.

## 2.3.4 Renaming the citation keys

`rename_cites(text, key_map[v])` rewrites `\cite`, `\citep`, `\citet`, `\citeauthor`, `\nocite`, their
starred forms, biblatex `\parencite`, `\textcite` and multi-cite `\cites`. It keeps the optional arguments
(`\citep[see][p.~5]{a,b}`), leaves unknown keys untouched, and writes a key only once when two old keys map
to the same new one.

```{important}
The key map is **per version** and `rename_cites` is applied **exactly once** to each version's text. A map
can chain: an author who renumbered two references gives `Shevkar2025 → Shevkar2025a` together with
`Shevkar2025a → Shevkar2025b` in the map of version 1. One pass gives every `\cite` its new key; a second
pass would rename `Shevkar2025` twice.
```

## 2.3.5 Output

The rows of the `bibtex` table have the nine columns of the statement (chapter [1.5](overview.md#m2-tables)):
`journal` falls back to `booktitle`, and `url` to the arXiv abstract page when only an arXiv ID is known;
`authors` is a list, `year` an integer or null.

## 2.3.6 Check on a sample

Before the full run, the step was checked by hand on 32 papers of our ranges (46 versions, 12 papers with
two or three versions), downloaded **with** their `.bbl` files by `tools/fetch_bib_sample.py`:

- **`\bibitem` conversion.** 45 random items from `\bibitem` and `.bbl` sources: title, authors and year are
  right in all of them, and a screen of all 353 such items found no wrong row.
- **`.bbl` against the true `.bib`.** One paper has only a `.bbl` in version 1 and the `.bib` in version 2.
  Of the 62 entries converted from the `.bbl`, 61 merge with their `.bib` entry (the last one is no longer
  cited in version 2).
- **Merges.** On the sample, 2,020 entries became 1,393 (−31%): 388 merges by title and year, 195 by arXiv
  ID, 31 by DOI, 13 duplicate keys in one version. Every merge between different keys was checked and is
  correct.
- **Renaming.** Of 2,006 cited keys, 7 are renamed, and after `rename_cites` every `\cite` carries the chosen
  key.

The small-caps and collaboration layouts were added after this check: before, one paper with 114 JFM-style
items had every title wrong. The numbers of the full corpus are in chapter [3.5](statistics.ipynb).
