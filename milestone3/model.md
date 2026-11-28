# 2.4 Models, selection, post-processing and MRR@5

*Author: Lưu Minh Quân · code: `src/23_model.ipynb` (8 offline tests)*

## 2.4.1 Problem framing and candidate scorers

Each labelled BibTeX entry is treated as a **learning-to-rank query** over the $n$ arXiv references of its
own publication. The top 5 candidates (`cand_1` … `cand_5`, padded with `null` when $n < 5$) are written to
`predictions.parquet`. We compare three classical model families across a **14-configuration grid**:

| Family | Configurations | Description |
|---|---:|---|
| `baseline` | 1 | Unlearned linear score: $10 \cdot \text{f\_arxiv\_eq} + 3 \cdot \text{f\_doi\_eq} + \text{f\_title\_tfidf\_char}$ |
| `logreg` | 9 | Pointwise `StandardScaler` + `LogisticRegression(class_weight="balanced")`, $C \in \{0.1, 1.0, 10.0\} \times \text{manual\_weight} \in \{1, 3, 5\}$; `NaN` filled by train median + `*_missing` flags |
| `ranker` | 4 | Listwise `LGBMRanker(objective="lambdarank")` grouped per entry, `num_leaves` $\in \{15, 31\} \times \text{manual\_weight} \in \{1, 3\}$, learning rate 0.05, up to 500 trees with early stopping on valid |

Manual entries are weighted by `manual_weight` relative to automatic entries so that the 12 train manual
publications are not drowned out by the 3,745 automatic ones.

## 2.4.2 Model selection and post-processing

Because the validation set holds only 8 publications (4 manual + 4 automatic), `select_model()` evaluates
every configuration on two scores:

1. **5-fold `GroupKFold` CV** grouped by publication on `train` (no publication appears in both a training
   and a held-out fold);
2. **Validation MRR@5** on the 8 held-out `valid` publications.

Configurations are ranked by `choice_score = (cv_mrr5 + valid_mrr5) / 2`, breaking ties in favour of the
simpler, faster model. Train rows of `predictions.parquet` use **out-of-fold** scores so no paper is ever
ranked by a model that trained on it.

Two optional post-processing steps are also evaluated:

1. **Exact arXiv rule (`post_arxiv_rule`):** any candidate with `f_arxiv_eq = 1` is forced to rank 1.
2. **One-to-one Hungarian assignment (`post_assignment`):** `scipy.optimize.linear_sum_assignment` on
   paper-normalized scores $[0, 1]$ promotes an assigned reference to rank 1 if its normalized score is at
   least $\tau \times$ the row's maximum ($\tau$ tuned on `valid`).

**Selection outcome.** All 14 configurations achieved **valid MRR@5 = 1.0000** and 5-fold CV MRR@5 between
0.99898 and **0.99998** (`logs/m3_model_selection.csv`). **`baseline`** ranked first (`choice_score = 0.999991`)
and ran in **31.8 s** (versus 244–266 s for `logreg` and 337–348 s for `ranker`), so `baseline` was selected.
Tuning $\tau$ on `valid` showed no gain over `no_assignment = 1.0000`, so **`tau = None`** (no Hungarian
re-assignment needed). The full model step (grid selection, refitting, ablation, LOPO and writing
`predictions.parquet`) completed in **4,019.5 s** (67.0 min).

## 2.4.3 Evaluation metrics: `skip` vs `zero`

The official evaluation metric is Mean Reciprocal Rank at 5:

$$
\text{MRR@5} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}
$$

with $1/\text{rank}_i = 0$ if the true reference is not in the top 5. Following Q&A M3 #4, an entry that has
no matching arXiv reference in Semantic Scholar is **not** a valid sample in $Q$, so our main metric is
**`nil_mode_main = "skip"`** (counting only matched entries):

- **Validation (`valid`, 8 papers, 318 matched entries):** MRR@5 = **1.0000**, Hit@1 = **1.0000**.
- **Test (`test`, 8 papers, 267 matched entries):** MRR@5 = **1.0000**, Hit@1 = **1.0000** (1.0000 across
  manual, auto, `.bib`, and `\bibitem` slices).
- **Train out-of-fold (3,757 papers, 80,744 matched entries):** MRR@5 = **0.99998**, Hit@1 = **0.99996**,
  Hit@5 = **1.00000**.

For transparency, we also log **`mrr5_zero`** (counting unmatched entries in $|Q|$ with score 0): **0.7244**
on `valid` (318 / 439) and **0.7629** on `test` (267 / 350). Because a ranking list cannot place a
non-existent reference in the top 5, `mrr5_zero` is mathematically bounded above by the share of entries that
have a true arXiv reference—and here equals that share exactly, measuring dataset coverage rather than model
quality.

## 2.4.4 Why MRR@5 saturates at 1.0—and where the real difficulty lies

An MRR@5 of 1.0000 on both validation and test does not mean entity resolution is trivial in general; the
data explain cleanly why **in-paper ranking of matched arXiv entries** saturates here:

1. **Explicit identifiers.** Across positive pairs, 37.0% carry an exact `arxiv_hint` (`f_arxiv_eq = 1`) and
   22.8% carry a matching DOI (`f_doi_eq = 1`), with 0.0% false positives on negative pairs.
2. **Near-verbatim titles.** Citations in LaTeX bibliographies quote titles almost word for word: on positive
   pairs the mean `f_title_ratio` is **0.9913** (vs 0.3937 on negatives) and mean `f_title_tfidf_char` is
   **0.9887** (vs 0.0971 on negatives), which is why even `title_only` ablation reaches 1.0000.
3. **Small within-paper candidate pools.** Candidates are restricted to the citing paper's own arXiv
   references—a median of **18** candidates per eligible paper (`m3_data_summary.json`, mean 19.19 across the
   corpus). Distinguishing the true cited paper among ~20 references in the same paper is far easier than
   searching a 2-million-paper index.
4. **Selection effect of confirmable positives.** By definition of the task, a positive pair is an entry that
   a human labeller or the deterministic rule matcher could match with near-certainty (the rule matcher agrees
   with manual labels at precision 1.0000 and recall 0.9952).

**What actually remains hard (and extra diagnostics per Q&A M3 #7).** Chapter [4](results.ipynb) therefore
pairs the official MRR@5 with five diagnostic analyses: (i) the **14-configuration model selection grid**,
(ii) **5-variant ablation** (`full`, `no_identifiers`, `no_hierarchy`, `no_postprocessing`, `title_only` — all
1.0000), (iii) **leave-one-publication-out (LOPO)** across 16 manual papers (1.0000 ± 0.0000), (iv)
`mrr5_zero` vs `mrr5_skip`, and (v) the **NIL-detection precision–recall curve** (`nil_detection_valid`).
Deciding *whether* a BibTeX entry belongs to the paper's arXiv reference list at all—calling NIL when its
best score falls below a threshold—is genuinely non-trivial: near the true ~27.6% NIL rate on `valid` (when
25.1% of entries are called NIL), precision is **0.991** and recall is **0.901**; pushing recall to 1.000
drops precision to 0.953 at threshold 1.0 and rapidly lower thereafter.

**Proposed future stress test (not run).** As discussed in Q&A M3 #7, a meaningful harder benchmark would
randomly mask identifiers (`url`, `doi`, `arxiv_hint`) and perturb titles (truncating subtitles, injecting
character noise, or stripping titles from a fraction of entries) inside `23_model` on Colab using
`pairs.parquet`, comparing `baseline`, `logreg`, and `LGBMRanker` when surface title overlap is degraded. That
experiment requires a fresh Colab run of `23_model` and is left as proposed future work; no synthetic numbers
are fabricated here.
