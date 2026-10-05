import type { CommuneOption, DepartmentOption } from "../types/prediction";

async function getJson<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new Error("Impossible de charger le référentiel géographique.");
  }

  if (!response.ok) {
    throw new Error(
      response.status === 503
        ? "Le référentiel géographique est temporairement indisponible. Réessayez plus tard."
        : "Impossible de charger les choix géographiques.",
    );
  }
  return (await response.json()) as T;
}

export function getDepartments(): Promise<DepartmentOption[]> {
  return getJson<DepartmentOption[]>("/api/v1/locations/departments");
}

export function getCommunes(departmentCode: string): Promise<CommuneOption[]> {
  return getJson<CommuneOption[]>(
    `/api/v1/locations/departments/${encodeURIComponent(departmentCode)}/communes`,
  );
}
