# 1. Overview

*Author: La Anh Hào · code: `src/20_m3_data.ipynb` – `src/26_export_hf.ipynb`*

## 1.1 Goal and scope

Milestone 3 links the structured corpus built in Milestones 1 and 2: for every publication, each standardized
**BibTeX entry** extracted in Milestone 2 (`bibtex` table) is matched against the **arXiv-keyed references**
crawled for that same publication in Milestone 1 (`references` table, via Semantic Scholar). For a paper with
$m$ BibTeX entries and $n$ arXiv references, candidate pairs form an $m \times n$ matrix within that paper;
each labelled entry has at most one true reference, and the model outputs a ranked top-5 candidate list
scored by **MRR@5**.

The pipeline runs end to end on **CPU-only Google Colab** using classical methods only (no external API calls,
no pretrained language models, no LLMs) and exports the full project corpus into **six sharded Parquet
tables** per member for publication on Hugging Face.

## 1.2 Team roles

| Member | Name | Assigned arXiv ID range | Milestone 3 ownership |
|---|---|---|---|
| TV1 | La Anh Hào | `2603.20580` – `2603.25579` | Input tables (`20_m3_data`), end-to-end runner (`25_run_m3`), Hugging Face export (`26_export_hf`) |
| TV2 | Võ Nguyễn Vân Anh | `2609.32834` – `2609.37833` | Manual sheets, validation, automatic matcher and split (`21_labeling`) |
| TV3 | Lưu Minh Quân | `2605.17338` – `2605.22337` | Cleaning, candidate pairs and 25 features (`22_features`), models, evaluation and `predictions` (`23_model`) |
| TV4 | Phạm Tấn Nhật Thịnh | `2605.07338` – `2605.12337` | Requirement verification (`24_analysis`), report and final A2 poster |

All four members manually labelled 5 publications from their own ID range (20 publications in total).

## 1.3 Requirements of the statement and Q&A

Every rule from the [Milestone 3 statement](https://hcmus-cs-ta.github.io/lab-book/intro-ds/statement/matching/)
and the instructor's Q&A (Milestone 3 #1–#7) is verified programmatically by `24_analysis` (**23/23 PASS**,
chapter [4](results.ipynb)):

| Requirement (statement & Q&A) | How our pipeline meets it | Described in |
|---|---|---|
| ≥ 5 manual publications **per member** (20 total), ≥ 20 matched pairs per manual paper, ≥ 400 pairs total (Q&A #1, #4) | 20 manual papers (5 per member), 807 entries, **628 matched pairs** (minimum 21 per paper) | [2.2](labeling.md), [3.2](statistics.ipynb) |
| A hand-labelled paper never enters automatic labelling (Q&A #4) | Both the 20 active manual papers and 10 replaced sheets (`labels/manual_old/`) are excluded before auto-labelling | [2.2](labeling.md) |
| Fixed rule-based automatic matcher covering ≥ 10% of each member's remaining papers (Q&A #4) | 4-rule cascade (`arxiv`, `doi`, `title_exact`, `title_fuzzy`) tuned on train manual papers; **3,753 auto papers** (17.6%–20.3% per member; 18.8% overall) | [2.2](labeling.md), [3.3](statistics.ipynb) |
| Pooled train / valid / test split: test = $k$ manual + $k$ auto, valid = $k$ manual + $k$ auto ($k=4$) (Q&A #4) | Seed 42 split (`split.json`): test = 4 manual + 4 auto, valid = 4 manual + 4 auto, train = 12 manual + 3,745 auto | [2.2](labeling.md) |
| Classical ML on Colab CPU only; no external API or pretrained model (Q&A #4) | Unsupervised TF-IDF fitted on our own corpus + `rapidfuzz` + scikit-learn / LightGBM on CPU Colab | [2.3](features.md), [2.4](model.md) |
| Feature justification with data analysis; M2 hierarchy features allowed | 25 features across 8 groups (incl. M2 `f_ctx_tfidf` and `f_n_cites`), each measured by positive/negative means, AUC and single-feature MRR@5 | [2.3](features.md), [3.4](statistics.ipynb) |
| Candidates from the paper's own references; `null` when < 5; $Q$ of MRR@5 holds only entries with a true reference (Q&A #4) | `nil_mode_main = "skip"`; `predictions` has 81,329 rows (entries with a true reference) across 3,733 papers, validated by `check_predictions` | [2.4](model.md), [4](results.ipynb) |
| Extra experiments / analysis alongside main MRR@5 (Q&A #7) | NIL-detection precision/recall curve, `mrr5_zero`, 5-variant ablation, 16-paper LOPO, 14-config selection grid, saturation analysis | [2.4](model.md), [4](results.ipynb) |
| Shared pipeline, individual Hugging Face dataset per member with 6 sharded Parquet tables (Q&A #2, #5) | `26_export_hf` splits all 6 tables strictly by member ID range (5,000 papers each, 0 rows outside ranges) with explicit Arrow schemas | [2.5](pipeline.md), [4.5](results.ipynb) |

## 1.4 End-to-end pipeline

`src/25_run_m3.ipynb` chains the six Milestone 3 steps in order and logs every run to `logs/m3_run.json`:

```text
Milestone 1 (data/raw/*/references.json) + Milestone 2 (data/parsed/*.json, parser 13.9 locked)
   │
   ▼
[20_m3_data]     entries (766,398) · refs (383,562) · pubs (20,000; 15,040 eligible)
   │
   ▼
[21_labeling]    20 manual sheets (628 pairs) + 3,753 auto papers (80,701 pairs) + split.json (seed 42)
   │
   ▼
[22_features]    4,821,691 candidate pairs × 25 features (cleaned titles, authors, IDs, context, M2 hierarchy)
   │
   ▼
[23_model]       14 configs (5-fold GroupKFold + valid) → baseline chosen → predictions.parquet (81,329 rows)
   │
   ▼
[24_analysis]    23/23 statement & Q&A requirement checks PASS (logs/m3_requirements.json)
   │
   ▼
[26_export_hf]   6 sharded Parquet tables per member (papers, references, elements, hierarchy, bibtex, predictions)
```

## 1.5 Published Hugging Face datasets

Each member hosts their own 5,000-paper slice as a public Hugging Face dataset with the six required Parquet
configs (`papers`, `references`, `elements`, `hierarchy`, `bibtex`, `predictions`) and a YAML dataset card:

| Member | Name | arXiv ID range | Hugging Face dataset |
|---|---|---|---|
| TV1 | La Anh Hào | `2603.20580` – `2603.25579` | <https://huggingface.co/datasets/Harkone2212/NMKHDL-Group10-LaAnhHao-24127361> |
| TV2 | Võ Nguyễn Vân Anh | `2609.32834` – `2609.37833` | *[Link to be added by TV2]* |
| TV3 | Lưu Minh Quân | `2605.17338` – `2605.22337` | *[Link to be added by TV3]* |
| TV4 | Phạm Tấn Nhật Thịnh | `2605.07338` – `2605.12337` | *[Link to be added by TV4]* |

Chapter [2](data.md) details each stage of the pipeline, chapter [3](statistics.ipynb) analyses the inputs,
labels and features, chapter [4](results.ipynb) reports model selection, MRR@5, saturation analysis,
requirement checks and export counts, and chapter [5](conclusion.ipynb) summarises conclusions and next steps.
