export type PropertyType = "Maison" | "Appartement";

export interface PredictionRequest {
  property_type: PropertyType;
  built_area_m2: number;
  rooms: number;
  department_code: string;
  commune_code: string;
  postal_code?: string;
}

export interface PredictionResponse {
  predicted_price_eur: number;
  model_vintage: number;
}
