# Data

`raw/` contains original, unmodified datasets; `processed/` is reserved for
derived data. The local `ValeursFoncieres-2025.txt` file has the schema of the
French DVF (Demandes de valeurs foncières) export. It is UTF-8, pipe-delimited,
and uses a comma as the decimal separator. The large source file is excluded
from Git.

The initial analysis cohort keeps only exact `Vente` rows for houses or
apartments with a non-empty sale price, built area, and room count. This is a
row-level filter; it does not yet guarantee one row per property or sale. A room
count of zero is retained when the built area is present; only missing required
values are excluded.

DVF describes real-estate dispositions using one or more rows. The price can be
repeated across rows for several premises or land-use records. The public file
also leaves document-reference fields empty, so the disposition number alone
is not a globally unique sale identifier. See
[`notebooks/01_data_exploration.ipynb`](../notebooks/01_data_exploration.ipynb)
for the initial investigation. A candidate feature-and-cadastral signature
repeats on 150,885 eligible rows, but cannot be treated as a definitive local
ID; the public data lacks `Identifiant local` and repeated parcel features may
refer to separate premises. We will audit these cases before dropping rows.

The raw export stays unchanged. The future model table should keep only its
target, house features, selected location fields, and any temporary columns
needed to group and audit records; unused source columns will be left out of
that derived table. Run `python ml/preprocessing/prepare_dvf.py` to create
`processed/dvf_eligible_rows_2025.csv`. It compares SHA-256 fingerprints of all
43 source fields before removing exact row duplicates, then writes eight
columns: sale date, sale price, property type, built area, room count, postal
code, department code, and commune code.

This strict source-row policy removed 50,179 rows and retained 1,061,104. Some
rows become identical after projection to the eight output columns because
their other source fields differed; they remain in the file under the agreed
strict-only deduplication rule. The model will need to account for these
repeated feature/target rows during evaluation.

## Candidate cohort: one residential row

The product goal is to estimate the price of a single house or apartment. The
raw 2025 export has no document identifier, and `No disposition` is not unique
by itself. The public [DVF derived-data script](https://github.com/datagouv/dvf/blob/master/improve-csv.js)
creates a non-stable `id_mutation` by incrementing when the consecutive source
rows change date or price. This is a useful grouping heuristic, not a verified
sale identifier: adjacent sales with the same date and price can be merged.

`python ml/preprocessing/prepare_single_home_candidates.py` applies that
consecutive date-and-price grouping directly to the unmodified source. It
retains a group only when it contains exactly one distinct `Maison` or
`Appartement` row, no other built-local type except `Dépendance`, and the
residential row has a price, built area, and room count. Strict residential
duplicate rows are ignored before counting. Blank-type rows, including
associated land records, may still share the sale price. The original filtered
table remains unchanged; the derived candidate file is
`processed/dvf_single_home_candidates_2025.csv` and is ignored by Git.

This rule yielded 735,202 candidate rows (381,036 houses and 354,166
apartments), about 69.3% of the original eligible cohort. Treat this as a
conservative candidate set, not ground truth: the heuristic may merge
independent adjacent sales, and land records can still share a sale price with
the one residential row. Extreme prices can also describe unusually large
homes or land packages rather than corrupt rows. See
[`notebooks/03_single_home_cohort.ipynb`](../notebooks/03_single_home_cohort.ipynb)
for the comparison and
[`notebooks/05_error_analysis.ipynb`](../notebooks/05_error_analysis.ipynb)
for the residual and high-price analysis. Do not remove values solely because
they are far from the median; test an explicit land-area feature and additional
years before changing the target cohort.

Official source and documentation:

- [DVF dataset on data.gouv.fr](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres)
- [Official DVF file notice](https://www.data.gouv.fr/api/1/datasets/r/d573456c-76eb-4276-b91c-e6b9c89d6656)
- [Reuse terms](https://www.data.gouv.fr/api/1/datasets/r/99549bdd-91f1-4a99-ac00-855b9a14e5f6)

Follow the official reuse terms: processing must not enable re-identification,
and DVF records must not be indexed by external search engines. Do not commit
large or licensed datasets; record their source and download instructions here.
