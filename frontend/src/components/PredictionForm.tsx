import { useState, type FormEvent } from "react";
import { predictPrice } from "../services/api";
import type {
  PredictionRequest,
  PredictionResponse,
  PropertyType,
} from "../types/prediction";

const initialValues: PredictionRequest = {
  property_type: "Appartement",
  built_area_m2: 75,
  rooms: 3,
  department_code: "75",
  commune_code: "056",
  postal_code: "75006",
};

const currency = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export function PredictionForm() {
  const [values, setValues] = useState(initialValues);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function updateField<K extends keyof PredictionRequest>(
    field: K,
    value: PredictionRequest[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setResult(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setResult(null);
    setError(null);

    try {
      setResult(await predictPrice(values));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Une erreur inattendue est survenue.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="estimator" aria-labelledby="estimator-title">
      <div className="section-heading">
        <span className="step-label">Estimation · modèle 2025</span>
        <h2 id="estimator-title">Décrivez le logement</h2>
        <p>Une première estimation, basée sur les ventes DVF de 2025.</p>
      </div>

      <form className="prediction-form" onSubmit={handleSubmit}>
        <label>
          Type de bien
          <select
            value={values.property_type}
            onChange={(event) =>
              updateField("property_type", event.target.value as PropertyType)
            }
          >
            <option value="Appartement">Appartement</option>
            <option value="Maison">Maison</option>
          </select>
        </label>

        <label>
          Surface bâtie
          <span className="input-with-unit">
            <input
              type="number"
              min="1"
              max="10000"
              step="0.1"
              required
              value={values.built_area_m2}
              onChange={(event) =>
                updateField("built_area_m2", Number(event.target.value))
              }
            />
            <span>m²</span>
          </span>
        </label>

        <label>
          Nombre de pièces
          <input
            type="number"
            min="0"
            max="100"
            step="1"
            required
            value={values.rooms}
            onChange={(event) => updateField("rooms", Number(event.target.value))}
          />
        </label>

        <div className="field-row">
          <label>
            Département
            <input
              type="text"
              maxLength={3}
              required
              placeholder="75"
              value={values.department_code}
              onChange={(event) =>
                updateField("department_code", event.target.value)
              }
            />
          </label>
          <label>
            Code commune
            <input
              type="text"
              maxLength={3}
              required
              placeholder="056"
              value={values.commune_code}
              onChange={(event) =>
                updateField("commune_code", event.target.value)
              }
            />
          </label>
        </div>

        <label>
          Code postal <span className="optional">(facultatif)</span>
          <input
            type="text"
            maxLength={10}
            placeholder="75006"
            value={values.postal_code ?? ""}
            onChange={(event) =>
              updateField("postal_code", event.target.value || undefined)
            }
          />
        </label>

        <button type="submit" disabled={isLoading}>
          {isLoading ? "Estimation en cours…" : "Estimer le prix"}
          {!isLoading && <span aria-hidden="true">↗</span>}
        </button>
      </form>

      {error && (
        <p className="feedback error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <div className="feedback result" role="status" aria-live="polite">
          <span>Prix estimé</span>
          <strong>{currency.format(result.predicted_price_eur)}</strong>
          <small>Estimation indicative · données {result.model_vintage}</small>
        </div>
      )}
      <p className="disclaimer">
        Cette estimation est fondée sur le marché observé en 2025. Elle ne
        constitue ni une expertise immobilière ni une prévision de prix futurs.
      </p>
    </section>
  );
}
