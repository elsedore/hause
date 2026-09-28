"""Create a conservative candidate cohort with one residential row per DVF group."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

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
RESIDENTIAL_TYPES = {"Maison", "Appartement"}
REQUIRED_COLUMNS = {
    "Valeur fonciere",
    "Surface reelle bati",
    "Nombre pieces principales",
}


def fingerprint_row(values: list[str]) -> bytes:
    """Hash every field without ambiguity from separators between field values."""
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="big"))
        digest.update(encoded)
    return digest.digest()


def price_key(raw_price: str) -> str:
    """Normalize a DVF price like the public derived-data grouping does."""
    normalized = raw_price.strip().replace(",", ".")
    if not normalized:
        return ""
    try:
        return str(Decimal(normalized).normalize())
    except InvalidOperation:
        return normalized


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
        default=Path("data/processed/dvf_single_home_candidates_2025.csv"),
        help="Path for the derived candidate CSV file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(f"Input dataset not found: {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
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
    totals = Counter()
    seen_fingerprints: set[bytes] = set()
    group_key: tuple[str, str] | None = None
    group_rows: list[dict[str, str]] = []
    group_has_other_local = [False]
    output_columns = [OUTPUT_NAMES[column] for column in OUTPUT_COLUMNS]

    def write_group(writer: csv.DictWriter) -> None:
        if not group_rows:
            group_has_other_local[0] = False
            return
        totals["candidate_groups"] += 1
        if len(group_rows) == 1:
            totals["single_residential_groups"] += 1
            row = group_rows[0]
            if group_has_other_local[0]:
                totals["groups_with_other_built_locals"] += 1
                totals["eligible_rows_excluded_with_other_locals"] += int(
                    row["is_eligible"]
                )
            elif row["is_eligible"]:
                output = row["output"]
                output["sale_date"] = datetime.strptime(
                    output["sale_date"], "%d/%m/%Y"
                ).strftime("%Y-%m-%d")
                output["sale_price_eur"] = output["sale_price_eur"].replace(
                    ",", "."
                )
                output["built_area_m2"] = str(
                    Decimal(output["built_area_m2"].replace(",", "."))
                )
                output["rooms"] = str(int(Decimal(output["rooms"])))
                writer.writerow(output)
                totals["candidate_rows"] += 1
                totals[f"candidate_{row['property_type'].lower()}s"] += 1
        else:
            totals["groups_with_multiple_residential_rows"] += 1
            totals["rows_in_multiple_residential_groups"] += len(group_rows)
            totals["eligible_rows_in_multiple_residential_groups"] += sum(
                row["is_eligible"] for row in group_rows
            )
        group_rows.clear()
        group_has_other_local[0] = False

    try:
        with args.input.open(encoding="utf-8", newline="") as source, temp_handle:
            reader = csv.reader(source, delimiter="|")
            header = next(reader)
            index = {name: header.index(name) for name in header}
            writer = csv.DictWriter(temp_handle, fieldnames=output_columns)
            writer.writeheader()

            for values in reader:
                totals["source_rows"] += 1
                date = values[index["Date mutation"]]
                price = values[index["Valeur fonciere"]]
                next_key = (date, price_key(price))
                if next_key != group_key:
                    write_group(writer)
                    group_key = next_key

                property_type = values[index["Type local"]]
                is_sale = values[index["Nature mutation"]] == "Vente"
                if property_type in RESIDENTIAL_TYPES and not is_sale:
                    group_has_other_local[0] = True
                elif property_type and property_type not in {
                    *RESIDENTIAL_TYPES,
                    "Dépendance",
                }:
                    group_has_other_local[0] = True
                if (
                    not is_sale
                    or property_type not in RESIDENTIAL_TYPES
                ):
                    continue

                is_eligible = all(
                    values[index[column]].strip() for column in REQUIRED_COLUMNS
                )
                fingerprint = fingerprint_row(values)
                if fingerprint in seen_fingerprints:
                    totals["strict_duplicates_removed"] += 1
                    totals["eligible_duplicates_removed"] += int(is_eligible)
                    continue
                seen_fingerprints.add(fingerprint)
                totals["distinct_residential_rows"] += 1
                totals["eligible_rows_before_grouping"] += int(is_eligible)

                output = {
                    OUTPUT_NAMES[column]: values[index[column]]
                    for column in OUTPUT_COLUMNS
                }
                group_rows.append(
                    {
                        "is_eligible": is_eligible,
                        "output": output,
                        "property_type": property_type,
                    }
                )

            write_group(writer)

        os.replace(temp_path, args.output)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    print(f"Output: {args.output}")
    print(f"Source rows scanned: {totals['source_rows']:,}")
    print(f"Distinct residential sale rows: {totals['distinct_residential_rows']:,}")
    print(f"Strict duplicates removed: {totals['strict_duplicates_removed']:,}")
    print(
        "Eligible strict duplicates removed: "
        f"{totals['eligible_duplicates_removed']:,}"
    )
    print(f"Eligible rows before grouping: {totals['eligible_rows_before_grouping']:,}")
    print(f"Candidate groups: {totals['candidate_groups']:,}")
    print(f"Groups with one residential row: {totals['single_residential_groups']:,}")
    print(
        "Groups with multiple residential rows: "
        f"{totals['groups_with_multiple_residential_rows']:,}"
    )
    print(
        "Single-residence groups with other built locals: "
        f"{totals['groups_with_other_built_locals']:,}"
    )
    print(
        "Eligible rows excluded with other built locals: "
        f"{totals['eligible_rows_excluded_with_other_locals']:,}"
    )
    print(
        "Eligible rows in multi-residential groups: "
        f"{totals['eligible_rows_in_multiple_residential_groups']:,}"
    )
    print(f"Candidate rows written: {totals['candidate_rows']:,}")
    print(
        "Candidate houses / apartments: "
        f"{totals['candidate_maisons']:,} / "
        f"{totals['candidate_appartements']:,}"
    )


if __name__ == "__main__":
    main()
