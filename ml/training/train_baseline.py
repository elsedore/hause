"""Train and evaluate a first housing-price baseline on a time holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    OneHotEncoder,
    StandardScaler,
    TargetEncoder,
)

NUMERIC_FEATURES = ["built_area_m2", "rooms"]
CATEGORICAL_FEATURES = [
    "property_type",
    "department_code",
    "commune_id",
    "postal_code",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/dvf_single_home_candidates_2025.csv"),
        help="Candidate dataset created by prepare_single_home_candidates.py.",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("ml/models/baseline_ridge.joblib"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("ml/evaluation/baseline_metrics.json"),
    )
    parser.add_argument(
        "--hgb-model-output",
        type=Path,
        default=Path("ml/models/baseline_hist_gradient_boosting.joblib"),
    )
    parser.add_argument(
        "--refit-ridge-on-full-year",
        action="store_true",
        help=(
            "After evaluation, refit Ridge on all 2025 candidate rows and save "
            "a separate final artifact."
        ),
    )
    parser.add_argument(
        "--final-model-output",
        type=Path,
        default=Path("ml/models/ridge_2025_full.joblib"),
    )
    parser.add_argument(
        "--final-metadata-output",
        type=Path,
        default=Path("ml/evaluation/ridge_2025_full_metadata.json"),
    )
    return parser.parse_args()


def metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae_eur": float(mean_absolute_error(actual, predicted)),
        "median_absolute_error_eur": float(
            median_absolute_error(actual, predicted)
        ),
        "mean_error_eur": float(np.mean(predicted - actual.to_numpy())),
        "rmse_eur": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
    }


def main() -> None:
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(
            f"Candidate data not found: {args.input}. "
            "Run the candidate preparation script first."
        )

    data = pd.read_csv(args.input, parse_dates=["sale_date"], low_memory=False)
    data["commune_id"] = (
        data["department_code"].astype("string").str.strip()
        + "-"
        + data["commune_code"].astype("string").str.strip()
    )
    for column in CATEGORICAL_FEATURES:
        data[column] = data[column].fillna("__missing__").astype(str)
    train_mask = data["sale_date"] < pd.Timestamp("2025-10-01")
    train = data.loc[train_mask].copy()
    test = data.loc[~train_mask].copy()
    if train.empty or test.empty:
        raise ValueError(
            "Both the Jan-Sep train period and Oct-Dec holdout are required"
        )

    features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    x_train, x_test = train[features], test[features]
    y_train, y_test = train["sale_price_eur"], test["sale_price_eur"]

    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            (
                "log",
                FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            ),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            (
                "impute",
                SimpleImputer(strategy="constant", fill_value="__missing__"),
            ),
            (
                "one_hot",
                OneHotEncoder(
                    handle_unknown="infrequent_if_exist",
                    min_frequency=50,
                    dtype=np.float32,
                ),
            ),
        ]
    )
    preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        sparse_threshold=1.0,
    )
    ridge_pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessing),
            ("ridge", Ridge(alpha=10.0, solver="lsqr")),
        ]
    )
    model = TransformedTargetRegressor(
        regressor=ridge_pipeline,
        func=np.log1p,
        inverse_func=np.expm1,
    )

    tree_numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
        ]
    )
    tree_categorical_pipeline = Pipeline(
        steps=[
            (
                "impute",
                SimpleImputer(strategy="constant", fill_value="__missing__"),
            ),
            (
                "target_encode",
                TargetEncoder(
                    target_type="continuous",
                    smooth="auto",
                    cv=KFold(n_splits=5, shuffle=True, random_state=42),
                ),
            ),
        ]
    )
    tree_preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", tree_numeric_pipeline, NUMERIC_FEATURES),
            (
                "categorical",
                tree_categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
        ],
        verbose_feature_names_out=False,
    )
    hgb_regressor = Pipeline(
        steps=[
            ("preprocess", tree_preprocessing),
            (
                "hist_gradient_boosting",
                HistGradientBoostingRegressor(
                    learning_rate=0.08,
                    max_iter=120,
                    max_leaf_nodes=31,
                    l2_regularization=1.0,
                    early_stopping=True,
                    random_state=42,
                ),
            ),
        ]
    )
    hgb_model = TransformedTargetRegressor(
        regressor=hgb_regressor,
        func=np.log1p,
        inverse_func=np.expm1,
    )

    print(f"Training rows: {len(train):,}")
    print(f"Holdout rows: {len(test):,}")
    print("Fitting median, Ridge, and histogram gradient boosting…", flush=True)
    dummy = DummyRegressor(strategy="median").fit(x_train, y_train)
    model.fit(x_train, y_train)
    tree_features = features
    hgb_model.fit(x_train[tree_features], y_train)

    dummy_predictions = dummy.predict(x_test)
    medians_by_type = train.groupby("property_type")["sale_price_eur"].median()
    type_median_predictions = test["property_type"].map(medians_by_type).to_numpy()
    ridge_predictions = model.predict(x_test)
    hgb_predictions = hgb_model.predict(x_test[tree_features])
    results: dict[str, object] = {
        "dataset": str(args.input),
        "target": "sale_price_eur",
        "date_feature_used": False,
        "temporal_split": {
            "train_start": str(train["sale_date"].min().date()),
            "train_end": str(train["sale_date"].max().date()),
            "test_start": str(test["sale_date"].min().date()),
            "test_end": str(test["sale_date"].max().date()),
        },
        "row_counts": {"train": len(train), "holdout": len(test)},
        "features": features,
        "hgb_features": tree_features,
        "hgb_categorical_encoding": "cross-fitted target encoding",
        "candidate_grouping_caveat": (
            "Groups use consecutive source rows with the same date and price; "
            "this is a heuristic, not a stable transaction identifier."
        ),
        "metrics": {
            "global_median_baseline": metrics(y_test, dummy_predictions),
            "property_type_median_baseline": metrics(
                y_test, type_median_predictions
            ),
            "ridge_log_target": metrics(y_test, ridge_predictions),
            "hist_gradient_boosting_log_target": metrics(
                y_test, hgb_predictions
            ),
        },
        "ridge_metrics_by_property_type": {},
        "hgb_metrics_by_property_type": {},
    }
    by_type: dict[str, dict[str, float]] = {}
    for property_type, indices in test.groupby("property_type").groups.items():
        actual = y_test.loc[indices]
        predictions = model.predict(x_test.loc[indices])
        by_type[str(property_type)] = metrics(actual, predictions)
    results["ridge_metrics_by_property_type"] = by_type
    hgb_by_type: dict[str, dict[str, float]] = {}
    for property_type, indices in test.groupby("property_type").groups.items():
        hgb_by_type[str(property_type)] = metrics(
            y_test.loc[indices], hgb_predictions[test.index.get_indexer(indices)]
        )
    results["hgb_metrics_by_property_type"] = hgb_by_type

    error_frame = pd.DataFrame(
        {"actual": y_test, "predicted": ridge_predictions}, index=test.index
    )
    error_frame["price_band"] = pd.qcut(
        error_frame["actual"], q=5, duplicates="drop"
    )
    results["ridge_metrics_by_actual_price_band"] = {}
    results["hgb_metrics_by_actual_price_band"] = {}
    for price_band, group in error_frame.groupby("price_band", observed=True):
        results["ridge_metrics_by_actual_price_band"][str(price_band)] = {
            "rows": len(group),
            "median_actual_price_eur": float(group["actual"].median()),
            **metrics(group["actual"], group["predicted"].to_numpy()),
        }
        group_indices = group.index
        test_positions = test.index.get_indexer(group_indices)
        results["hgb_metrics_by_actual_price_band"][str(price_band)] = {
            "rows": len(group),
            "median_actual_price_eur": float(group["actual"].median()),
            **metrics(
                group["actual"], hgb_predictions[test_positions]
            ),
        }
    results["unseen_category_share_in_holdout"] = {
        column: float(
            (~x_test[column].isin(x_train[column].unique())).mean()
        )
        for column in CATEGORICAL_FEATURES
    }

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    dump(model, args.model_output)
    args.hgb_model_output.parent.mkdir(parents=True, exist_ok=True)
    dump(hgb_model, args.hgb_model_output)
    args.metrics_output.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if args.refit_ridge_on_full_year:
        final_model = clone(model)
        final_model.fit(data[features], data["sale_price_eur"])
        args.final_model_output.parent.mkdir(parents=True, exist_ok=True)
        args.final_metadata_output.parent.mkdir(parents=True, exist_ok=True)
        dump(final_model, args.final_model_output)
        final_metadata = {
            "model_family": "Ridge regression with log-transformed target",
            "dataset": str(args.input),
            "training_rows": len(data),
            "training_start": str(data["sale_date"].min().date()),
            "training_end": str(data["sale_date"].max().date()),
            "target": "sale_price_eur",
            "features": features,
            "date_feature_used": False,
            "fixed_training_millesime": 2025,
            "includes_previous_holdout_period": True,
            "evaluation_note": (
                "The temporal holdout metrics in baseline_metrics.json were "
                "measured before this refit. This full-year artifact has no "
                "independent 2025 holdout score."
            ),
        }
        args.final_metadata_output.write_text(
            json.dumps(final_metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Full-year Ridge model saved to {args.final_model_output}")
        print(f"Full-year model metadata saved to {args.final_metadata_output}")
    print(json.dumps(results["metrics"], indent=2))
    print(f"Model saved to {args.model_output}")
    print(f"Tree model saved to {args.hgb_model_output}")
    print(f"Metrics saved to {args.metrics_output}")


if __name__ == "__main__":
    main()
