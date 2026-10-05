import { PredictionForm } from "../components/PredictionForm";

export function HomePage() {
  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="House Price Prediction, accueil">
          <span className="brand-mark" aria-hidden="true">
            H
          </span>
          <span>HAUSE<span className="brand-dot">.</span></span>
        </a>
        <span className="topbar-note">HOUSE PRICE PREDICTION</span>
        {/* <span className="topbar-note">@elsdore</span> */}
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span /> ESTIMATION IMMOBILIÈRE · FRANCE</p>
          <h1>Un lieu à vous.<br /><em>Une valeur à estimer.</em></h1>
          <p className="hero-description">
            Découvrez une estimation du prix de vente à partir des
            caractéristiques du logement et des transactions observées.
          </p>
          <div className="hero-footnote">
            <span className="footnote-icon" aria-hidden="true">↳</span>
            <span>Une première expérience autour des données DVF, millésime 2025.</span>
          </div>
        </div>

        <PredictionForm />
      </section>

      <footer className="page-footer">
        <a href="https://www.linkedin.com/in/elsadore/" target="_blank" rel="noopener noreferrer">
          <span className="footer-link">@elsadore</span>
        </a>
        <span>Copyrights @2026</span>
      </footer>
    </main>
  );
}
