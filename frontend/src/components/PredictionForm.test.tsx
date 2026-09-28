import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PredictionForm } from "./PredictionForm";

describe("PredictionForm", () => {
  it("submits the property details and displays the estimated price", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        predicted_price_eur: 417_971.97,
        model_vintage: 2025,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PredictionForm />);
    await user.click(screen.getByRole("button", { name: "Estimer le prix" }));

    expect(await screen.findByRole("status")).toHaveTextContent(/417\s*972/);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/predictions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          property_type: "Appartement",
          built_area_m2: 75,
          rooms: 3,
          department_code: "75",
          commune_code: "056",
          postal_code: "75006",
        }),
      }),
    );
  });

  it("shows a helpful message when the model API is unavailable", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ detail: "The prediction model is not available." }),
      }),
    );

    render(<PredictionForm />);
    await user.click(screen.getByRole("button", { name: "Estimer le prix" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le modèle de prédiction est indisponible.",
    );
  });
});
