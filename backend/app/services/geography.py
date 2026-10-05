"""Cached access to the official French geographic reference API."""

import json
import re
from functools import lru_cache
from urllib.error import URLError
from urllib.request import urlopen

from backend.app.schemas.locations import CommuneOption, DepartmentOption

GEO_API = "https://geo.api.gouv.fr"
_DEPARTMENT_PATTERN = re.compile(r"^[0-9A-Z]{2,3}$")
_POSTAL_PATTERN = re.compile(r"^[0-9]{5}$")


class GeographyProviderError(RuntimeError):
    """Raised when the official geographic reference cannot be loaded."""


def _get_json(url: str) -> list[dict[str, object]]:
    try:
        with urlopen(url, timeout=8) as response:  # noqa: S310
            payload = json.load(response)
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise GeographyProviderError(
            "The French geographic reference is temporarily unavailable."
        ) from error

    if not isinstance(payload, list):
        raise GeographyProviderError("Unexpected geographic reference response.")
    return payload


@lru_cache(maxsize=1)
def get_departments() -> tuple[DepartmentOption, ...]:
    """Return departments from the official Géo API (cached per process)."""
    rows = _get_json(f"{GEO_API}/departements?fields=code,nom&format=json")
    return tuple(
        sorted(
            (
                DepartmentOption(code=str(row["code"]), name=str(row["nom"]))
                for row in rows
                if row.get("code") and row.get("nom")
            ),
            key=lambda department: department.name.casefold(),
        )
    )


def _dvf_commune_code(department_code: str, insee_code: object) -> str | None:
    """Convert a full INSEE commune code to the suffix used in DVF."""
    full_code = str(insee_code)
    if not full_code.startswith(department_code):
        return None
    suffix = full_code[len(department_code) :]
    return suffix if suffix and len(suffix) <= 3 else None


@lru_cache(maxsize=200)
def get_department_communes(department_code: str) -> tuple[CommuneOption, ...]:
    """Return communes and their postal codes, cached by department."""
    if not _DEPARTMENT_PATTERN.fullmatch(department_code):
        return ()

    url = (
        f"{GEO_API}/departements/{department_code}/communes"
        "?fields=code,nom,codeDepartement,codesPostaux&format=json"
    )
    rows = _get_json(url)
    communes: list[CommuneOption] = []
    for row in rows:
        if not row.get("code") or not row.get("nom"):
            continue
        code = _dvf_commune_code(department_code, row["code"])
        if code is None:
            continue
        raw_postal_codes = row.get("codesPostaux", [])
        postal_codes = sorted(
            {
                str(postal_code)
                for postal_code in raw_postal_codes
                if _POSTAL_PATTERN.fullmatch(str(postal_code))
            }
            if isinstance(raw_postal_codes, list)
            else set()
        )
        if postal_codes:
            communes.append(
                CommuneOption(
                    commune_code=code,
                    name=str(row["nom"]),
                    postal_codes=postal_codes,
                )
            )

    return tuple(sorted(communes, key=lambda commune: commune.name.casefold()))
