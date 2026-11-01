# Group 17 — DSAI5101 Midterm Code Submission

Cat Image Arena: data quality, cat preference rankings, image-level disagreement,
human preference differences, and model comparison. This archive contains the
five members' implementations, original course CSVs, shared cleaned data, saved
validation split, tests, and reference tables/figures. It is a standalone code
submission; the presentation/report is submitted separately.

## 1. Reproduce the submitted results

Extract the ZIP first. Open a terminal in `Group_17_Code/`. Use **Python 3.12**
(verified with 3.12.14). No Git checkout, editable installation, notebook server,
GPU, image download, pretrained weights, or external API is required for this run.
Internet access is needed only to install the Python dependencies.

Windows PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock.txt
.venv/Scripts/python scripts/validate_submission.py
```

macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python scripts/validate_submission.py
```

`validate_submission.py` checks the archive manifest and installed versions,
reruns members 2–5 from the supplied cleaned data, runs the 37 unit/source tests
and project checks, and compares all four regenerated numerical summaries with
the reference summaries. It fails with a nonzero exit status if a check fails.
The transcript and machine-readable results are written to
`outputs/project_checks/submission_validation.log` and
`outputs/project_checks/submission_validation.json`.

Run this command **before editing files or regenerating outputs**: the initial
manifest check verifies the files as delivered. After making intentional edits,
use the ordinary analysis and checking commands below instead.

The full analysis usually takes a few minutes on a recent CPU; allow 5–15 minutes
on slower machines. No GPU is used. The exact measured runtime, CPU description,
Python version, and platform of our clean-environment verification are recorded
in `SUBMISSION_VALIDATION.json` when present. Peak memory was not benchmarked.

## 2. Execution order and output locations

| Part | Entry point | Main outputs |
|---|---|---|
| 1. Cleaning and data quality | `scripts/run_data_preparation.py` | `data/processed/`, `data/splits/`, `outputs/data_preparation/` |
| 2. Win rates and Bradley–Terry | `scripts/run_cat_ranking.py` | `outputs/cat_ranking/` |
| 3. Within-cat image disagreement | `scripts/run_image_analysis.py` | `outputs/image_analysis/` |
| 4. Human-group comparisons | `scripts/run_human_preferences.py` | `outputs/human_preferences/` |
| 5. Nested models and robustness | `scripts/run_model_comparison.py` | `outputs/model_comparison/` |

After activating the environment (or using its Python path explicitly):

```bash
python scripts/run_all.py
python scripts/check_project.py
```

`run_all.py` runs parts 2, 3, 4, 5 in that order and overwrites their result
directories and generated report sections. Part 1's delivered data, tables and
figures are included; its **complete raw-image audit is an optional separate
reproduction**, described below. `check_project.py --rerun` combines the two
commands above. Paths resolve relative to the project, so script execution does
not depend on the terminal's working directory. The notebook is an optional
demonstration; none of the submitted results depends on saved cell outputs.

## 3. Inputs, split, methods, and fixed settings

- `data/raw/train.csv`: 24,896 labeled response records. `test.csv`: 6,224 rows
  with withheld outcomes. `test_example.csv` contains example predictions, **not
  true labels**; it is never used for fitting or evaluating predictions.
- `data/processed/`: the authoritative cleaned training table, test features,
  and descriptive image-pair summary. Cleaning retains all training records,
  missing human attributes, and flagged content duplicates; no imputation.
- `data/splits/validation_split.csv`: fixed split by unordered image pair;
  19,981 training and 4,915 validation records. Do not randomly re-split rows.
  Cats and images can occur on both sides of this split.
- Part 2 uses only `between_cats` records for empirical win rates and a
  Bradley–Terry model. Its full-data ranking is descriptive.
- Part 3 uses `within_cat` records. It canonicalizes image orientation, counts
  repeated-pair agreement, uses 19,999 global and 9,999 within-cat conditional
  permutations, 10,000 cat-cluster bootstrap samples, exact binomial tests and
  multiple-testing adjustments, plus graph and sensitivity diagnostics.
- Part 4 compares group-specific cat win rates and BT rankings and uses
  cat-pair-stratified score tests with Holm adjustment across six human fields.
- Part 5 compares cat-only, position, image, group-main, and group-by-cat models.
  Penalties are chosen inside the training portion by 5-fold image-pair-grouped
  cross-validation: image candidates `[0.3, 1, 3, 10]`, group-by-cat candidates
  `[1, 10, 100]`. It uses 2,000 validation metric bootstrap replicates and 200
  baseline ranking bootstrap replicates (60 additional replicates if a different
  extension is adopted). The delivered final model is the cat-only baseline.
- Base seed is **2026**; documented routines derive seeds 2027/2028 where needed.
  Shared settings are in `configs/default.json`; part 5's full default settings
  are in `src/cat_arena/model_comparison/analysis.py:DEFAULT_SETTINGS`.

The optimizer uses `ftol=1e-12`, `gtol=1e-8` and the shared 5,000-iteration
budget. If that budget is exhausted, part 5 continues the same objective from
the current coefficients with up to 20,000 additional iterations, 100,000
function evaluations and 50 L-BFGS history vectors, without relaxing either
tolerance. An unsuccessful fit still raises an error.

Useful reference checks: 21,893 between-cat and 3,003 within-cat records; part 3
has 1,132 within-cat image pairs and agreement `1547/2916 = 0.5305212620`;
primary permutation p-value `0.0008`; model M0 validation log loss
`0.6689043906`. Full summaries and parameters are in each module's `summary.json`
and `run_metadata.json`.

Locked versions of NumPy, pandas, SciPy, Matplotlib, Pillow and their dependencies
are in `requirements.lock.txt`. Exact integer counts and fixed random results
should reproduce in this environment. Other platforms/BLAS versions can produce
small optimizer differences; a cross-machine rerun changed extension log losses
by about `1.6e-6` or less without changing penalty selection, accuracy, the top ten,
or the adopted baseline model. The submission validator allows absolute numerical
differences up to `1e-5` in summary floats; integer counts and labels must match
exactly. Plot rendering/PDF metadata can vary across
platforms. The older migration check deliberately uses byte hashes for the
unchanged supplied data and part 1 reference outputs.

## 4. Optional: rebuild part 1 from CSVs and actual image files

The CSVs are included in this ZIP. The **1,558 source image files are not**:
download the course images using the link in [the dataset README](data/README_dataset.md)
and retain their directory layout, for example:

```text
data/raw/images/cat_000002/cat_000002_0001.jpg
```

Then, in a separate copy of the archive, run:

```bash
python scripts/run_all.py --prepare-data
python scripts/audit_data_preparation.py --rerun
```

This executes all five parts, including existence checks, Pillow verification
and full image decoding, and independently audits part 1. Missing or invalid
images cause an explicit failure. We did **not** rerun the full 1,558-image audit
while preparing this ZIP. Historical image-audit evidence is retained in
`docs/provenance/data_preparation/`; the test suite also exercises preparation
and independent auditing on a small synthetic-image fixture. Neither is claimed
to be a fresh full-dataset image audit. Part 1 figures can be regenerated by the
same preparation script once those images are present.

## 5. Folder guide and interpretation

```text
src/cat_arena/       reusable code, separated into five functional modules
scripts/            command-line entry points, verification and packaging
configs/            shared paths and random/optimizer settings
data/raw/           supplied course CSVs; optional downloaded images go here
data/processed/     common cleaned tables used by all analyses
data/splits/        saved grouped validation allocation
tests/              statistical, encoding, source and leakage checks
outputs/<module>/   reproducible tables, PNG/PDF figures, summaries and metadata
reports/sections/   analysis text; regenerated sections for members 2–5
reports/handoffs/   rationale and limitations passed between modules
docs/modules/       data dictionary, cleaning rules and method documentation
docs/provenance/    historical audit records and regression-check baselines
notebooks/          optional member 2 demonstration
README_TEAM.md      repository collaboration guide
SUBMISSION_MANIFEST.json   source revision and per-file SHA-256 hashes
```

There is no participant ID: records must not be interpreted as independent
people, and repeated-pair disagreement is not within-person inconsistency.
Image-level differences are distinct from cat identity preferences. The saved
split does not establish generalization to unseen cats/images/participants.
Full-data rankings and outcome-derived summaries are not validation features.
The test set has no true labels, so the reported performance is **validation**
performance. No test-set score or prediction submission is claimed here.

Attribution and method-specific limitations remain in the original module
documents and report sections. This ZIP makes no changes to the statistical
methods or supplied data. Course data and derived materials are for research and
education only. The separate final report is the authoritative group roster and
contribution statement.
