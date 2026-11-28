# 2.3 Candidate pairs and features

*Author: Lưu Minh Quân · code: `src/22_features.ipynb` (21 offline tests)*

For every labelled publication with $m$ BibTeX entries and $n$ arXiv-keyed Semantic Scholar references,
`build_pairs()` builds the within-paper Cartesian product ($m \times n$ candidate pairs). Across all **3,773**
labelled publications, this yields **4,821,691 candidate pairs** (159,429 entries, **81,329 positive pairs**,
a 1.69% positive rate; train 158,640 / valid 439 / test 350 entries). The feature step ran in **1,421.6 s**
(23.7 min) on CPU Colab.

All features use classical methods only—unsupervised TF-IDF fitted strictly on our own corpus (without labels)
and `rapidfuzz` string similarities—with no external API calls or pretrained models.

## 2.3.1 Shared text cleaning

Both sides (`entries` and `refs`) pass through identical normalizers reusing helpers from `12_bibtex` and
`03_references`, so feature differences reflect true content rather than formatting noise:

- **Titles (`norm_title`):** LaTeX commands converted to plain text, accents folded, lowercased, tokenized to
  `[a-z0-9]` (`gpt 4` and `3d` preserved). English stop words (scikit-learn list) are removed for token
  overlap features; character n-gram TF-IDF uses the full cleaned title.
- **Authors (`author_surname`):** each author is reduced to the last word of their family name folded to
  `[a-z]`, dropping particles (`van der Waals` → `waals`), suffixes (`Jr.`, `II`) and `et al.` / `others`,
  so `A. B. Smith`, `Smith, A. B.` and `Smith Jr., A.` all map to `smith`.
- **Identifiers (`arxiv_hint`, `doi_norm`):** arXiv IDs are extracted from `doi`, `url` and `journal` and
  normalized via `normalize_ref_arxiv_id` (preserving old-style IDs like `hep-th/9901001`); DOIs are stripped
  of URL prefixes and lowercased.
- **Year:** entry `year`; for references, S2 `ref_year` falling back to the 4-digit year of
  `ref_submission_date`.
- **Fallback text (`raw_text`):** concatenation of title, author keys and venue, catching `\bibitem` entries
  whose title field was incomplete or unseparated.

After cleaning (`logs/m3_cleaning_report.csv`), 99.20% of all 766,398 entries have a title (99.74% in `.bib`
vs 96.13% in `\bibitem`), 99.36% have authors, 98.90% have a year, 24.79% carry an `arxiv_hint`, 33.12% carry
a DOI, and 98.41% have Milestone 2 citing-sentence context (chapter [3.4](statistics.ipynb)).

## 2.3.2 Feature design (25 features)

Every feature is computed on the **full** $m \times n$ matrix of a publication before slicing to labelled
rows, so row- and column-ranking features reflect every competing entry and reference in that paper. Missing
values stay `NaN` (handled natively by LightGBM; median-imputed with `*_missing` indicators for logistic
regression).

| Group | Feature | Formula / definition | Rationale |
|---|---|---|---|
| **Identifier** | `f_arxiv_eq` | `arxiv_hint == ref_arxiv_id` | Explicit arXiv ID in the citation nearly guarantees a match |
| | `f_has_arxiv_hint` *(row-const)* | Entry carries an `arxiv_hint` | Signals when `f_arxiv_eq = 0` is strong negative evidence |
| | `f_doi_eq` | `doi_norm` matches reference DOI or `10.48550/arxiv.<id>` | Exact secondary identifier |
| **Title** | `f_title_tfidf_char` | Cosine of `char_wb` 3–5-gram TF-IDF on cleaned titles | Robust to typos, hyphenation and residual LaTeX |
| | `f_title_jaccard` | Jaccard similarity of non-stopword title tokens | Shared content vocabulary |
| | `f_title_ratio` | `rapidfuzz.fuzz.ratio / 100` | Global string edit similarity |
| | `f_title_partial` | `rapidfuzz.fuzz.partial_ratio / 100` | Matches titles with added or dropped subtitles |
| | `f_title_len_diff` | $\|len(t) - len(t_{\text{ref}})\| / \max(len)$ | Penalizes large length mismatches |
| **Author** | `f_first_surname_eq` | Entry and reference share the first-author surname key | Captures canonical "FirstAuthor et al." citation style |
| | `f_surname_jaccard` | Jaccard similarity of author surname sets | Tolerates missing middle authors or reordering |
| | `f_author_cover` | Share of entry author keys present in reference | Handles BibTeX lists truncated with `et al.` |
| | `f_n_authors_diff` | $\|n_{\text{authors}} - n_{\text{ref\_authors}}\|$ | Flags large author-count discrepancies |
| **Year / venue** | `f_year_diff` | $\|year - ref\_year\|$ (`NaN` if missing) | Preprint vs proceedings versions typically differ by 0–1 year |
| | `f_year_missing` *(row-const)* | Either year is missing | Lets linear models discount `f_year_diff` when imputed |
| | `f_venue_arxiv` *(row-const)* | Entry cites arXiv explicitly in journal, URL or DOI | Prior that the cited work is in the arXiv reference pool |
| | `f_venue_sim` | `fuzz.token_set_ratio(venue, ref_venue) / 100` | Captures matching journal or conference names |
| **Fallback** | `f_raw_tfidf` | Word TF-IDF cosine of `raw_text` vs reference title + authors | Recovers `\bibitem` entries lacking a clean title field |
| **Matrix context** | `f_title_rank_in_row` | Rank of `f_title_tfidf_char` within the entry's row (1 = best) | Compares a candidate against all alternatives for the entry |
| | `f_gap_to_best` | Row max `f_title_tfidf_char` minus this candidate's value | Measures separation from the row's top candidate |
| | `f_margin` *(row-const)* | Best minus second-best `f_title_tfidf_char` in the row | Measures confidence that the row has a clear winner (key for NIL) |
| | `f_col_rank` | Rank of this cell within the reference's column | Captures mutual best-match (one-to-one bibliography structure) |
| | `f_n_candidates` *(row-const)* | Number of arXiv references $n$ in the paper | Adjusts scoring for candidate pool size |
| **M2 hierarchy** | `f_ctx_tfidf` | Word TF-IDF cosine of M2 citing sentences (`context`) vs reference title | Topical signal from how the citing sentence discusses the work |
| | `f_n_cites` *(row-const)* | Distinct M2 elements citing this key | Heavily cited entries are core related works |
| **Experimental** | `f_pos_diff` | $\|position/m - ref\_position/n\|$ | Tests whether bibliography order correlates with S2 list order |

**Row-constant features.** Five features (`f_has_arxiv_hint`, `f_year_missing`, `f_venue_arxiv`, `f_margin`,
`f_n_candidates`, plus `f_n_cites`—six in `m3_feature_report.csv`) are constant across all candidates of one
entry. They cannot rank candidates alone (their standalone MRR@5 reflects only the deterministic tie-break
order), but provide context for learned models and for NIL detection.

**Data-backed feature justification.** As plotted in chapter [3.4](statistics.ipynb), `f_raw_tfidf` alone
reaches **AUC = 0.9983** and single-feature **MRR@5 = 0.9962** (`skip`), followed closely by `f_col_rank`
(oriented AUC 0.9974, MRR@5 0.9924) and the title features (`f_title_tfidf_char`, `f_title_jaccard`,
`f_title_ratio`: AUC 0.994–0.996, MRR@5 0.994). Milestone 2's citation-context feature `f_ctx_tfidf` adds a
genuine topical signal (mean 0.1575 on positives vs 0.0455 on negatives, AUC = 0.7599), whereas the
experimental order feature `f_pos_diff` carries almost no signal (AUC = 0.5138, below the 0.55 usefulness
threshold).
