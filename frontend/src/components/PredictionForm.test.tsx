import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PredictionForm } from "./PredictionForm";

const departments = [{ code: "75", name: "Paris" }];
const communes = [
  { commune_code: "056", name: "Paris 6e", postal_codes: ["75006", "75007"] },
];

async function selectLocation(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByRole("combobox", { name: "Département" }), "Paris");
  await user.click(await screen.findByRole("option", { name: "75 · Paris" }));
  expect(screen.getByRole("combobox", { name: "Département" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await user.type(await screen.findByRole("combobox", { name: "Commune" }), "Paris 6");
  await user.click(await screen.findByRole("option", { name: "Paris 6e" }));
  expect(screen.getByRole("combobox", { name: "Commune" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await user.type(await screen.findByRole("combobox", { name: "Code postal" }), "75006");
  await user.click(await screen.findByRole("option", { name: "75006" }));
  expect(screen.getByRole("combobox", { name: "Code postal" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal");
  Reflect.deleteProperty(HTMLDialogElement.prototype, "close");
});

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
});

describe("PredictionForm", () => {
  it("uses dependent official location choices and displays the estimate", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => departments,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => communes,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
        predicted_price_eur: 417_971.97,
        model_vintage: 2025,
        explanations: [
          {
            factor: "La surface du logement",
            direction: "hausse",
            contribution_percent: 12.4,
          },
        ],
        }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<PredictionForm />);
    await selectLocation(user);
    await user.click(screen.getByRole("button", { name: "Estimer le prix" }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(/417\s*972/);
    expect(dialog).toHaveTextContent(
      "La surface du logement a contribué à une estimation plus élevée.",
    );
    await user.click(screen.getByRole("button", { name: "Fermer" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
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
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true, json: async () => departments })
        .mockResolvedValueOnce({ ok: true, json: async () => communes })
        .mockResolvedValueOnce({
          ok: false,
          status: 503,
          json: async () => ({ detail: "The prediction model is not available." }),
        }),
    );

    render(<PredictionForm />);
    await selectLocation(user);
    await user.click(screen.getByRole("button", { name: "Estimer le prix" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le modèle de prédiction est indisponible.",
    );
  });
});
