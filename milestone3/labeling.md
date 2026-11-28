# 2.2 Manual and automatic labels, and train/valid/test split

*Author: Võ Nguyễn Vân Anh · code: `src/21_labeling.ipynb`*

Following the statement and the instructor's clarification (Q&A M3 #1, #4), a **label** is a matched
`(BibTeX entry, arXiv reference)` pair within the same publication. Entries whose cited work is not among the
paper's Semantic Scholar arXiv references receive no match (`null`) and are **not** counted towards the
manual pair quotas or the denominator $|Q|$ of MRR@5.

## 2.2.1 Manual labelling workflow

- **Stratified selection.** `pick_manual()` selects **5 publications per member** (20 for the group, seed 42)
  from each member's `MANUAL_POOL` slice (`labels/selection.csv`), stratifying across both bibliography
  sources (`.bib` files and `\bibitem` lists, giving 11 `.bib` and 9 `\bibitem` papers in the final set).
- **Two sheet formats.**
  - *Standard entry-oriented sheets* (`labels/todo/<member>/<fid>.csv`, one row per BibTeX entry): show the
    entry's title, up to 3 authors, year, venue, and three title-similarity hints (`hint_1..3`, ranked by
    `fuzz.token_set_ratio`), plus a companion `<fid>_refs.csv` listing every arXiv reference with its
    `arxiv.org/abs/<id>` link. Labellers can type `h1`, `h2`, or `h3` to accept a hint, paste an arXiv ID,
    or leave `ref_arxiv_id` blank for no match. Automatic labels are **never** shown on the sheets so that
    manual labels remain an independent benchmark of the automatic matcher.
  - *Reference-oriented ("by-ref") sheets (TV1).* For TV1's 5 papers, sheets were organized with one row per
    arXiv reference and the 3 closest BibTeX entries (`cand_1..3`), then mapped back to the standard
    entry-level CSV schema in `labels/manual/<fid>.csv`.
- **Google Sheets locale issue and fixes.** Opening raw CSVs in Google Sheets under the Vietnamese locale
  silently parsed dotted arXiv IDs as formatted numbers (e.g. `2603.20822` → `260.320.822`, or trailing zeros
  dropped like `2504.10000` → `2504.1`, and hyphenated keys turned into dates). We prevented and repaired
  this in two ways: using shorthand hint codes (`h1`/`h2`/`h3`), an explicit `arXiv:` prefix, or switching
  the spreadsheet locale to `en-US`, and adding `repair_arxiv_id()` and positional title recovery inside
  `read_manual()`.
- **Replaced papers (`labels/manual_old/`).** Ten initially sampled papers were replaced during labelling—either
  because they contained REVTeX `\bibitem` entries that were unreadable before parser 13.9, or because they
  had fewer than 20 matched pairs once Q&A M3 #4 clarified that the 20-label floor counts *matched pairs*
  rather than total entries. All 10 replaced sheets are preserved in `labels/manual_old/` and strictly
  excluded from automatic labelling (`hand_labelled_papers()`), ensuring no hand-inspected paper ever enters
  the automatic pool.
- **Borderline adjudication.** Every entry is marked with `confidence` (`sure` / `unsure`) and an optional
  `note`. Across all 807 manual entries, only **1 entry (0.12%)** was marked `unsure`: entry 10 of
  `2605.08524` (TV4), whose bibliography title referenced a GitHub repository corresponding to the cited
  arXiv paper; the team reviewed it and kept it matched with `confidence = unsure` and an explanatory note.

**Final manual ground truth** (`logs/m3_labels.json`): **20 papers** (5 per member), **807 entries**,
**628 matched pairs** (minimum **21** pairs in any single paper, exceeding the ≥ 20/paper and ≥ 400 total
quotas), with a no-match share of **22.18%** (179 unmatched entries).

## 2.2.2 Rule-based automatic matcher

Per Q&A M3 #4, automatic labels must come from a **fixed rule set** rather than the trained ML model (to avoid
circular evaluation). `auto_match_pub()` applies four high-precision rules in strict priority order on the
shared cleaned columns from `22_features`:

| Priority | Rule | Fires when | Score |
|---:|---|---|---:|
| 1 | `arxiv` | The entry's extracted `arxiv_hint` (`url`, `journal`, or `10.48550/arXiv.*` DOI) equals a reference's `ref_arxiv_id`. If `arxiv_hint` is present but *not* in the paper's references, the entry is immediately assigned `none` so later rules cannot contradict its own ID. | 100 |
| 2 | `doi` | Normalized entry DOI equals normalized reference DOI (`norm_doi`). | 100 |
| 3 | `title_exact` | Cleaned titles are identical, have at least `min_tokens` words, and uniquely identify one reference. | 100 |
| 4 | `title_fuzzy` | `fuzz.token_sort_ratio` ≥ `fuzzy`, no tie for best reference, title has ≥ `min_tokens` words, **and** either first-author surnames match or years differ by at most `year_tol`. | ratio |
| — | `none` | No rule fired. | 0 |

After rule matching, **one-to-one conflict resolution** ensures each reference is assigned to at most one
entry (stronger rule priority, then higher score, then earlier bibliography position wins; the losing entry
becomes `none`).

**Leak-free parameter tuning.** The manual validation and test papers are drawn *first* (section 2.2.3).
`tune_auto_params()` then grid-searches `fuzzy ∈ {80, 85, 90, 95}` × `min_tokens ∈ {3, 4, 5}` (with
`year_tol = 1`) on the **12 train manual papers only**, choosing the configuration with highest recall subject
to precision ≥ 95%. The winning parameters—**`fuzzy = 80, min_tokens = 3, year_tol = 1`**—achieved train
precision 1.0000 and recall 0.9972 (F1 = 0.9986).

**Validation against manual labels:**

- Over all **20 manual papers** (807 entries): **precision = 1.0000**, **recall = 0.9952**, **F1 = 0.9976**
  (625 correct matches, 0 wrong references, 0 false matches, 3 missed pairs, 179 both-none).
- Over the **8 held-out manual papers** (test + valid, 333 entries, never seen during tuning):
  **precision = 1.0000**, **recall = 0.9925**, **F1 = 0.9963** (entry accuracy 0.9940).

**Coverage.** The tuned matcher was applied to a seeded **25%** sample of eligible non-manual publications
(with a per-member floor enforcing ≥ 10% of all non-manual publications in each member's 5,000-ID range):
**3,753 papers** (18.8% of the 19,980 non-manual papers), **158,622 entries**, and **80,701 matched pairs**:

| Member | Auto papers | Share of member's non-manual papers |
|---|---:|---:|
| TV1 | 877 | 17.6% |
| TV2 | 888 | 17.8% |
| TV3 | 974 | 19.5% |
| TV4 | 1,014 | 20.3% |
| **Total** | **3,753** | **18.8%** |

## 2.2.3 Train / validation / test split

Following the group-scaled rule ($k = 4$ members, Q&A M3 #4), `make_split()` partitions the 3,773 labelled
publications at the **publication level** (seed 42, `labels/split.json`) so no paper ever crosses splits:

| Partition | Manual papers | Automatic papers | Total papers | Labelled entries | Matched pairs |
|---|---:|---:|---:|---:|---:|
| **Train** | 12 | 3,745 | 3,757 | 158,640 | 80,744 |
| **Validation** | 4 | 4 | 8 | 439 | 318 |
| **Test** | 4 | 4 | 8 | 350 | 267 |
| **Total** | **20** | **3,753** | **3,773** | **159,429** | **81,329** |

The exact test and validation publication IDs and full label statistics are shown in chapter
[3](statistics.ipynb).
