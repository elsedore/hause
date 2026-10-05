export type PropertyType = "Maison" | "Appartement";

export interface PredictionRequest {
  property_type: PropertyType;
  built_area_m2: number;
  rooms: number;
  department_code: string;
  commune_code: string;
  postal_code: string;
}

export interface DepartmentOption {
  code: string;
  name: string;
}

export interface CommuneOption {
  commune_code: string;
  name: string;
  postal_codes: string[];
}

export interface PredictionResponse {
  predicted_price_eur: number;
  model_vintage: number;
  explanations: PredictionExplanation[];
}

export interface PredictionExplanation {
  factor: string;
  direction: "hausse" | "baisse";
  contribution_percent: number;
}
