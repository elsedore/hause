"""Create a compact, filtered DVF table for later analysis and modeling."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from collections import Counter
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "Valeur fonciere",
    "Surface reelle bati",
    "Nombre pieces principales",
]
OUTPUT_COLUMNS = [
    "Date mutation",
    "Valeur fonciere",
    "Type local",
    "Surface reelle bati",
    "Nombre pieces principales",
    "Code postal",
    "Code departement",
    "Code commune",
]
OUTPUT_NAMES = {
    "Date mutation": "sale_date",
    "Valeur fonciere": "sale_price_eur",
    "Type local": "property_type",
    "Surface reelle bati": "built_area_m2",
    "Nombre pieces principales": "rooms",
    "Code postal": "postal_code",
    "Code departement": "department_code",
    "Code commune": "commune_code",
}


def fingerprint_row(values: tuple[str, ...]) -> bytes:
    """Return a SHA-256 fingerprint of every source field in one row."""
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="big"))
        digest.update(encoded)
    return digest.digest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/ValeursFoncieres-2025.txt"),
        help="Path to the original pipe-delimited DVF text file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/dvf_eligible_rows_2025.csv"),
        help="Path for the derived CSV file.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Number of source rows loaded per chunk.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(f"Input dataset not found: {args.input}")
    if args.chunksize < 1:
        raise ValueError("chunksize must be greater than zero")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    seen_fingerprints: set[bytes] = set()
    totals = Counter()
    property_types = Counter()

    temp_handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{args.output.name}.",
        suffix=".tmp",
        dir=args.output.parent,
        delete=False,
    )
    temp_path = Path(temp_handle.name)

    try:
        with temp_handle:
            wrote_header = False
            for chunk_number, chunk in enumerate(
                pd.read_csv(
                    args.input,
                    sep="|",
                    dtype="string",
                    keep_default_na=False,
                    chunksize=args.chunksize,
                ),
                start=1,
            ):
                totals["source_rows"] += len(chunk)
                has_required_values = chunk[REQUIRED_COLUMNS].apply(
                    lambda column: column.str.strip().ne("")
                ).all(axis=1)
                eligible = (
                    chunk["Nature mutation"].eq("Vente")
                    & chunk["Type local"].isin(["Maison", "Appartement"])
                    & has_required_values
                )
                selected = chunk.loc[eligible]
                totals["eligible_rows"] += len(selected)
                property_types.update(selected["Type local"].value_counts().to_dict())

                unique_mask = []
                for row in selected.itertuples(index=False, name=None):
                    fingerprint = fingerprint_row(row)
                    is_new = fingerprint not in seen_fingerprints
                    unique_mask.append(is_new)
                    if is_new:
                        seen_fingerprints.add(fingerprint)

                unique_rows = selected.loc[unique_mask, OUTPUT_COLUMNS].copy()
                totals["strict_duplicates_removed"] += len(selected) - len(unique_rows)
                totals["rooms_zero_kept"] += int(
                    unique_rows["Nombre pieces principales"].eq("0").sum()
                )

                unique_rows["Date mutation"] = pd.to_datetime(
                    unique_rows["Date mutation"],
                    format="%d/%m/%Y",
                    errors="raise",
                ).dt.strftime("%Y-%m-%d")
                unique_rows["Valeur fonciere"] = pd.to_numeric(
                    unique_rows["Valeur fonciere"].str.replace(",", ".", regex=False),
                    errors="raise",
                )
                for column in [
                    "Surface reelle bati",
                    "Nombre pieces principales",
                ]:
                    numeric_values = pd.to_numeric(unique_rows[column], errors="raise")
                    if numeric_values.mod(1).eq(0).all():
                        numeric_values = numeric_values.astype("int64")
                    unique_rows[column] = numeric_values

                unique_rows = unique_rows.rename(columns=OUTPUT_NAMES)
                totals["output_rows"] += len(unique_rows)
                unique_rows.to_csv(
                    temp_handle,
                    index=False,
                    header=not wrote_header,
                )
                wrote_header = True

                if chunk_number % 10 == 0:
                    print(f"Scanned {totals['source_rows']:,} source rows")

        os.replace(temp_path, args.output)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    print(f"Output: {args.output}")
    print(f"Rows matching the requested criteria: {totals['eligible_rows']:,}")
    print(f"Strict duplicate rows removed: {totals['strict_duplicates_removed']:,}")
    print(f"Rows written: {totals['output_rows']:,}")
    print(f"Rows with zero rooms retained: {totals['rooms_zero_kept']:,}")
    print(f"Property types: {dict(property_types)}")


if __name__ == "__main__":
    main()
