import type { PredictionRequest, PredictionResponse } from "../types/prediction";

export async function predictPrice(
  request: PredictionRequest,
): Promise<PredictionResponse> {
  let response: Response;
  try {
    response = await fetch("/api/v1/predictions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error(
      "Impossible de joindre l’API. Vérifiez qu’elle est démarrée sur le port 8000.",
    );
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : undefined;
    const message =
      response.status === 503
        ? "Le modèle de prédiction est indisponible. Vérifiez que l’API et le modèle sont démarrés."
        : typeof detail === "string"
          ? detail
          : "La demande n’a pas pu être traitée. Vérifiez les informations saisies.";
    throw new Error(message);
  }

  return (await response.json()) as PredictionResponse;
}
