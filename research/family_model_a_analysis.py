import math

import numpy as np
import pandas as pd

from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import StandardScaler


INPUT_FILE = (
    "research/data/"
    "family_model_a_dataset.csv"
)

STRUCTURE_FILE = (
    "research/data/"
    "family_identifier_structure.csv"
)


def load_data():
    df = pd.read_csv(INPUT_FILE)

    structure_df = pd.read_csv(
        STRUCTURE_FILE
    )

    df = df.merge(
        structure_df[
            [
                "family",
                "external_identifications_2024",
                "unique_external_identifiers_2024",
                "external_ids_per_observation_2024",
                "external_ids_per_identifier_2024",
                "top1_external_id_share_2024",
                "top5_external_id_share_2024",
                "top10_external_id_share_2024",
                "top20_external_id_share_2024",
            ]
        ],
        on="family",
        how="left",
        validate="one_to_one",
    )

    df[
        "log_unique_external_identifiers"
    ] = np.log10(
        df[
            "unique_external_identifiers_2024"
        ]
    )

    df["log_workload"] = np.log10(
        df["workload_6mo"]
    )

    df["log_species_richness"] = np.log10(
        df["species_richness"]
    )

    df["log_genus_richness"] = np.log10(
        df["genus_richness"]
    )

    df["log_obs_per_species"] = np.log10(
        df["observations_per_species"]
    )

    df["external_id_fraction"] = (
        df["external_id_rate"] / 100
    )

    return df


def print_correlations(df):
    predictors = [
        (
            "log_workload",
            "Log workload",
        ),
        (
            "log_species_richness",
            "Log species richness",
        ),
        (
            "log_genus_richness",
            "Log genus richness",
        ),
        (
            "log_obs_per_species",
            "Log observations/species",
        ),
        (
            "species_per_genus",
            "Species/genus",
        ),
        (
            "identifiability_score",
            "Identifiability",
        ),
        (
            "owner_species_pct",
            "Owner species %",
        ),
        (
            "owner_higher_pct",
            "Owner higher %",
        ),
        (
            "mean_photos",
            "Mean photos",
        ),
        (
            "photos_4plus_pct",
            "4+ photos %",
        ),
        (
            "external_ids_per_observation_2024",
            "2024 external IDs/obs",
        ),
        (
            "log_unique_external_identifiers",
            "Log unique ext identifiers",
        ),
        (
            "external_ids_per_identifier_2024",
            "External IDs/identifier",
        ),
        (
            "top5_external_id_share_2024",
            "Top-5 external ID share",
        ),
    ]
    print()
    print("FAMILY-LEVEL CORRELATIONS")
    print("=========================")
    print()

    header = (
        f"{'Predictor':27}"
        f"{'Pearson r':>12}"
        f"{'p':>10}"
        f"{'Spearman r':>13}"
        f"{'p':>10}"
    )

    print(header)
    print("-" * len(header))

    for column, label in predictors:
        x = df[column].to_numpy()
        y = df["external_id_rate"].to_numpy()

        pearson_r, pearson_p = pearsonr(
            x,
            y,
        )

        spearman_r, spearman_p = spearmanr(
            x,
            y,
        )

        print(
            f"{label:27}"
            f"{pearson_r:12.3f}"
            f"{pearson_p:10.3f}"
            f"{spearman_r:13.3f}"
            f"{spearman_p:10.3f}"
        )


def fit_full_model(
    df,
    predictors,
):
    x = df[predictors].to_numpy()
    y = df["external_id_rate"].to_numpy()

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)

    model = LinearRegression()
    model.fit(
        x_scaled,
        y,
    )

    predicted = model.predict(
        x_scaled
    )

    return {
        "r2": r2_score(
            y,
            predicted,
        ),
        "coefficients": dict(
            zip(
                predictors,
                model.coef_,
            )
        ),
        "intercept": model.intercept_,
    }


def lofo_predictions(
    df,
    predictors,
):
    actual = []
    predicted = []
    families = []

    for test_index in range(len(df)):
        train_df = df.drop(
            index=df.index[test_index]
        )
        test_df = df.iloc[
            [test_index]
        ]

        x_train = train_df[
            predictors
        ].to_numpy()

        y_train = train_df[
            "external_id_rate"
        ].to_numpy()

        x_test = test_df[
            predictors
        ].to_numpy()

        scaler = StandardScaler()

        x_train_scaled = (
            scaler.fit_transform(
                x_train
            )
        )

        x_test_scaled = (
            scaler.transform(
                x_test
            )
        )

        model = LinearRegression()

        model.fit(
            x_train_scaled,
            y_train,
        )

        prediction = model.predict(
            x_test_scaled
        )[0]

        actual.append(
            test_df[
                "external_id_rate"
            ].iloc[0]
        )

        predicted.append(
            prediction
        )

        families.append(
            test_df[
                "family"
            ].iloc[0]
        )

    actual = np.array(actual)
    predicted = np.array(predicted)

    return {
        "families": families,
        "actual": actual,
        "predicted": predicted,
        "mae": mean_absolute_error(
            actual,
            predicted,
        ),
        "rmse": math.sqrt(
            mean_squared_error(
                actual,
                predicted,
            )
        ),
        "r2": r2_score(
            actual,
            predicted,
        ),
    }


def print_models(df):
    models = [
        (
            "Identifiability",
            [
                "identifiability_score",
            ],
        ),
        (
            "Owner species %",
            [
                "owner_species_pct",
            ],
        ),
        (
            "Log workload",
            [
                "log_workload",
            ],
        ),
        (
            "Log obs/species",
            [
                "log_obs_per_species",
            ],
        ),
        (
            "Identifiability + workload",
            [
                "identifiability_score",
                "log_workload",
            ],
        ),
        (
            "Identifiability + obs/species",
            [
                "identifiability_score",
                "log_obs_per_species",
            ],
        ),
        (
            "Identifiability + owner species",
            [
                "identifiability_score",
                "owner_species_pct",
            ],
        ),
        (
            "Workload + obs/species",
            [
                "log_workload",
                "log_obs_per_species",
            ],
        ),
        (
            "External capacity",
            [
                "external_ids_per_observation_2024",
            ],
        ),
        (
            "External capacity + identifiability",
            [
                "external_ids_per_observation_2024",
                "identifiability_score",
            ],
        ),
        (
            "External capacity + identifiability + workload",
            [
                "external_ids_per_observation_2024",
                "identifiability_score",
                "log_workload",
            ],
        ),
        (
            "Base + Top-5 concentration",
            [
                "external_ids_per_observation_2024",
                "identifiability_score",
                "log_workload",
                "top5_external_id_share_2024",
            ],
        ),
        (
            "Base + identifier breadth",
            [
                "external_ids_per_observation_2024",
                "identifiability_score",
                "log_workload",
                "log_unique_external_identifiers",
            ],
        ),
    ]
    print()
    print("PRE-SPECIFIED MODEL A FAMILY MODELS")
    print("===================================")
    print()

    header = (
        f"{'Model':34}"
        f"{'Fit R2':>9}"
        f"{'LOFO MAE':>11}"
        f"{'LOFO RMSE':>12}"
        f"{'LOFO R2':>10}"
    )

    print(header)
    print("-" * len(header))

    results = []

    for name, predictors in models:
        full = fit_full_model(
            df,
            predictors,
        )

        lofo = lofo_predictions(
            df,
            predictors,
        )

        results.append(
            (
                name,
                predictors,
                full,
                lofo,
            )
        )

        print(
            f"{name:34}"
            f"{full['r2']:9.3f}"
            f"{lofo['mae']:11.2f}"
            f"{lofo['rmse']:12.2f}"
            f"{lofo['r2']:10.3f}"
        )

    print()
    print("STANDARDIZED FULL-DATA COEFFICIENTS")
    print("===================================")

    for (
        name,
        predictors,
        full,
        lofo,
    ) in results:
        print()
        print(name)

        for predictor in predictors:
            coefficient = (
                full["coefficients"][
                    predictor
                ]
            )

            print(
                f"  {predictor:28}"
                f"{coefficient:8.2f}"
                " percentage points"
            )


def print_best_residuals(df):
    predictors = [
        "external_ids_per_observation_2024",
        "identifiability_score",
        "log_workload",
    ]

    lofo = lofo_predictions(
        df,
        predictors,
    )

    rows = []

    for (
        family,
        actual,
        predicted,
    ) in zip(
        lofo["families"],
        lofo["actual"],
        lofo["predicted"],
    ):
        rows.append(
            {
                "family": family,
                "actual": actual,
                "predicted": predicted,
                "error": actual - predicted,
            }
        )

    rows.sort(
        key=lambda row: abs(
            row["error"]
        ),
        reverse=True,
    )

    print()
    print(
        "LOFO RESIDUALS:"
        " EXTERNAL CAPACITY + IDENTIFIABILITY + WORKLOAD"
    )
    print(
        "================================"
        "====================="
    )
    print()

    header = (
        f"{'Family':17}"
        f"{'Actual':>10}"
        f"{'Predicted':>12}"
        f"{'Error':>10}"
    )

    print(header)
    print("-" * len(header))

    for row in rows:
        print(
            f"{row['family']:17}"
            f"{row['actual']:9.1f}%"
            f"{row['predicted']:11.1f}%"
            f"{row['error']:10.1f}"
        )


def main():
    df = load_data()

    print()
    print("MODEL A FAMILY-LEVEL ANALYSIS")
    print("=============================")
    print()
    print(
        f"Families: {len(df)}"
    )

    print_correlations(df)
    print_models(df)
    print_best_residuals(df)


if __name__ == "__main__":
    main()