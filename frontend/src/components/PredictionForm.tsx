import { useEffect, useRef, useState, type FormEvent } from "react";
import { predictPrice } from "../services/api";
import { getCommunes, getDepartments } from "../services/locations";
import { SearchableSelect } from "./SearchableSelect";
import type {
  CommuneOption,
  DepartmentOption,
  PredictionRequest,
  PredictionResponse,
  PropertyType,
} from "../types/prediction";

const initialValues: PredictionRequest = {
  property_type: "Appartement",
  built_area_m2: 75,
  rooms: 3,
  department_code: "",
  commune_code: "",
  postal_code: "",
};

const currency = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export function PredictionForm() {
  const [values, setValues] = useState(initialValues);
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [communes, setCommunes] = useState<CommuneOption[]>([]);
  const [isLoadingDepartments, setIsLoadingDepartments] = useState(true);
  const [isLoadingCommunes, setIsLoadingCommunes] = useState(false);
  const [locationsError, setLocationsError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const resultDialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = resultDialog.current;
    if (!dialog) return;
    if (result && !dialog.open) dialog.showModal();
    if (!result && dialog.open) dialog.close();
  }, [result]);

  useEffect(() => {
    let active = true;
    getDepartments()
      .then((options) => {
        if (active) setDepartments(options);
      })
      .catch((caught: unknown) => {
        if (active) {
          setLocationsError(
            caught instanceof Error ? caught.message : "Impossible de charger les départements.",
          );
        }
      })
      .finally(() => {
        if (active) setIsLoadingDepartments(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!values.department_code) {
      setCommunes([]);
      return;
    }

    let active = true;
    setCommunes([]);
    setIsLoadingCommunes(true);
    setLocationsError(null);
    getCommunes(values.department_code)
      .then((options) => {
        if (active) setCommunes(options);
      })
      .catch((caught: unknown) => {
        if (active) {
          setLocationsError(
            caught instanceof Error ? caught.message : "Impossible de charger les communes.",
          );
        }
      })
      .finally(() => {
        if (active) setIsLoadingCommunes(false);
      });
    return () => {
      active = false;
    };
  }, [values.department_code]);

  const selectedCommune = communes.find(
    (commune) => commune.commune_code === values.commune_code,
  );

  function updateField<K extends keyof PredictionRequest>(
    field: K,
    value: PredictionRequest[K],
  ) {
    setValues((current) => ({ ...current, [field]: value }));
    setResult(null);
    setError(null);
  }

  function selectDepartment(code: string) {
    setValues((current) => ({
      ...current,
      department_code: code,
      commune_code: "",
      postal_code: "",
    }));
    setResult(null);
    setError(null);
  }

  function selectCommune(code: string) {
    setValues((current) => ({ ...current, commune_code: code, postal_code: "" }));
    setResult(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!values.department_code || !values.commune_code || !values.postal_code) {
      setError("Sélectionnez un département, une commune et un code postal dans les listes.");
      return;
    }
    setIsLoading(true);
    setResult(null);
    setError(null);

    try {
      setResult(await predictPrice(values));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Une erreur inattendue est survenue.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="estimator" aria-labelledby="estimator-title">
      <div className="section-heading">
        {/* <span className="step-label">Estimation · modèle 2025</span> */}
        <h2 id="estimator-title">Décrivez votre bien</h2>
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
              min="0.1"
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

        <label>
          Département
          <SearchableSelect
            label="Département"
            options={departments.map((department) => ({
              value: department.code,
              label: `${department.code} · ${department.name}`,
            }))}
            value={values.department_code}
            placeholder={
              isLoadingDepartments ? "Chargement des départements…" : "Rechercher un département"
            }
            required
            disabled={isLoadingDepartments || departments.length === 0}
            onChange={selectDepartment}
          />
        </label>

        <label>
          Commune
          <SearchableSelect
            label="Commune"
            options={communes.map((commune) => ({
              value: commune.commune_code,
              label: commune.name,
            }))}
            value={values.commune_code}
            placeholder={
              !values.department_code
                ? "Choisir d’abord un département"
                : isLoadingCommunes
                  ? "Chargement des communes…"
                  : "Rechercher une commune"
            }
            required
            disabled={!values.department_code || isLoadingCommunes || communes.length === 0}
            onChange={selectCommune}
          />
        </label>

        <label>
          Code postal
          <SearchableSelect
            label="Code postal"
            options={(selectedCommune?.postal_codes ?? []).map((postalCode) => ({
              value: postalCode,
              label: postalCode,
            }))}
            value={values.postal_code}
            placeholder="Rechercher un code postal"
            required
            disabled={!selectedCommune}
            onChange={(postalCode) => updateField("postal_code", postalCode)}
          />
        </label>

        <button
          type="submit"
          disabled={
            isLoading ||
            isLoadingDepartments ||
            isLoadingCommunes ||
            Boolean(locationsError)
          }
        >
          {isLoading ? "Estimation en cours…" : "Estimer le prix"}
          {!isLoading && <span aria-hidden="true">↗</span>}
        </button>
      </form>

      {locationsError && (
        <p className="feedback error" role="alert">
          {locationsError}
        </p>
      )}
      {error && (
        <p className="feedback error" role="alert">
          {error}
        </p>
      )}
      <dialog
        ref={resultDialog}
        className="result-dialog"
        aria-labelledby="result-dialog-title"
        onClose={() => setResult(null)}
      >
        {result && (
          <>
            <span className="dialog-eyebrow">Estimation indicative · données {result.model_vintage}</span>
            <h2 id="result-dialog-title">Prix estimé</h2>
            <p className="dialog-price">{currency.format(result.predicted_price_eur)}</p>
            <div className="explanation" aria-label="Explication de l’estimation">
              <h3>Comment cette estimation a été calculée</h3>
              <p>
                Le modèle a comparé les informations de votre logement aux
                ventes enregistrées en 2025. Voici les éléments qui ont le plus
                influencé son résultat :
              </p>
              <ul>
                {result.explanations.map((explanation) => (
                  <li key={explanation.factor}>
                    {explanation.factor} a contribué à une estimation{" "}
                    {explanation.direction === "hausse" ? "plus élevée" : "plus basse"}.
                  </li>
                ))}
              </ul>
              <p className="dialog-note">
                Ces éléments montrent des tendances observées dans les ventes,
                pas des causes certaines. La proximité du métro n’est pas prise
                en compte dans cette version.
              </p>
            </div>
            <button
              className="dialog-close"
              type="button"
              onClick={() => {
                resultDialog.current?.close();
                setResult(null);
              }}
            >
              Fermer
            </button>
          </>
        )}
      </dialog>
      <p className="disclaimer">
        Les choix géographiques proviennent du référentiel officiel{" "}
        <a href="https://geo.api.gouv.fr/" target="_blank" rel="noreferrer">
          Géo API
        </a>
        . Cette estimation est fondée sur le marché observé en 2025. Elle ne
        constitue ni une expertise immobilière ni une prévision de prix futurs.
      </p>
    </section>
  );
}
