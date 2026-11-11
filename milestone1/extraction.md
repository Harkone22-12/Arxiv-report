# 2.3 Extraction and figure removal

*Author: Võ Nguyễn Vân Anh · code: `src/02_download.ipynb`*

The statement asks to keep **only the `.tex` and `.bib` files** of every version, obtained by extraction,
and to leave the LaTeX text untouched. `extract_source` in `src/02_download.ipynb` does this for every
downloaded archive, in a worker thread, while the main thread is already waiting for the next request slot.

## 2.3.1 What a source can be

arXiv does not always return a tarball. `extract_source` recognises the **content**, not the file name or
the HTTP headers:

| arXiv returns | Result |
|---|---|
| TAR (any compression) or ZIP with `.tex` files | the `.tex` and `.bib` files, with their folder structure |
| one gzip / bzip2 / xz-compressed or plain TeX file | saved as `main.tex` |
| PDF or Word file (the paper has no LaTeX source) | empty `vN/` folder, status `empty_source` |
| HTML or JSON (an error page served with HTTP 200) | rejected, asked again in the next run |

A version without LaTeX source is **not dropped**: it keeps an empty `vN/` folder and an `empty_source`
receipt, so the paper stays in the corpus, as the statement asks, and later runs do not request it again.

## 2.3.2 Figure removal by file selection

Figures are removed by **not extracting them**. Only archive members whose name ends in `.tex` or `.bib`
(`KEEP = {".tex", ".bib"}`, case-insensitive) are written to Drive; everything else never leaves the
runtime's local disk and is deleted with the archive:

| Kept | Discarded |
|---|---|
| `.tex`, `.bib`, in their original folders | figures (PNG, JPEG, PDF, EPS, …), `.bbl`, `.sty`, `.cls`, data files, the archive itself |

Two consequences follow from this rule:

- **The TeX is not edited.** The kept files are copied byte for byte, so `figure` environments and
  `\includegraphics` commands stay exactly as the authors wrote them, which the parsing milestone relies on.
  The corpus is a text corpus: it is not expected to compile without the files that were removed.
- **An archive without any `.tex` file keeps nothing.** A lone `.bib` is not a usable source, so such a
  version is recorded as `empty_source`.

The receipt of a version stores the size of all files of the unpacked archive (`before_bytes`) and the size
of the kept files (`after_bytes`); the comparison is the subject of [3.2](statistics.ipynb).

## 2.3.3 Safety and edge cases

Archives come from the public and are unpacked automatically, so every member is checked before anything is
written.

- **Unsafe paths.** Absolute paths, `..` components, links and special files are rejected, as is a file
  whose path is also used as a folder. A single text file is limited to 128 MB (`MAX_TEXT_BYTES`). Such an
  archive fails with `REJECTED_ARCHIVE`.
- **Names that differ only in case.** A real archive (`2609.32867v1`) contains both
  `sections/limitations.tex` and `sections/Limitations.tex`, with different text. Both are kept: on a
  case-insensitive file system the second one is stored as `Limitations~2.tex` and the receipt records the
  original name.
- **Duplicate names.** A name listed twice in a TAR keeps its last copy, as `tar` does.
- **Broken archives.** Data that cannot be unpacked fails with `CORRUPT_ARCHIVE`; the version is asked again
  in the next run, in case the download was at fault.
- **Atomic result.** A version is unpacked into a staging folder and renamed into place only when complete,
  and its receipt lists the size and SHA-256 of every kept file, so the stored corpus can be verified later
  without downloading anything again.
