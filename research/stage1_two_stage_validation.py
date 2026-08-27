import csv
import math
import os

import numpy as np

from family_stage1_model_comparison import (
    fit_binomial,
    predict,
    standardize,
)


INPUT_FILE = os.path.join(
    "research",
    "data",
    "family_stage1_decomposition.csv",
)


PREDICTORS = {
    "Capacity": [
        "external_capacity",
    ],

    "Capacity + Ident": [
        "external_capacity",
        "identifiability_score",
    ],

    "Capacity + Workload": [
        "external_capacity",
        "log_workload",
    ],

    "All three": [
        "external_capacity",
        "identifiability_score",
        "log_workload",
    ],
}


DIRECT_MODELS = [
    "Capacity",
    "Capacity + Ident",
    "Capacity + Workload",
    "All three",
]


TWO_STAGE_MODELS = [
    (
        "Capacity -> Capacity",
        "Capacity",
        "Capacity",
    ),
    (
        "Capacity -> Capacity+Ident",
        "Capacity",
        "Capacity + Ident",
    ),
    (
        "Cap+Workload -> Capacity",
        "Capacity + Workload",
        "Capacity",
    ),
    (
        "Cap+Workload -> Cap+Ident",
        "Capacity + Workload",
        "Capacity + Ident",
    ),
    (
        "All three -> All three",
        "All three",
        "All three",
    ),
]


def load_rows():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    if len(rows) != 18:
        raise ValueError(
            "Expected 18 families, "
            f"found {len(rows)}"
        )

    return rows


def make_x(
    rows,
    predictor_name,
):
    fields = PREDICTORS[
        predictor_name
    ]

    return np.asarray(
        [
            [
                float(row[field])
                for field in fields
            ]
            for row in rows
        ],
        dtype=float,
    )


def fit_predict_held_out(
    x,
    successes,
    trials,
    held_out,
):
    mask = np.ones(
        len(successes),
        dtype=bool,
    )

    mask[held_out] = False

    x_train = x[mask]

    (
        x_train_std,
        mean,
        sd,
    ) = standardize(
        x_train
    )

    x_test_std = (
        x[[held_out]]
        - mean
    ) / sd

    beta = fit_binomial(
        x_train_std,
        successes[mask],
        trials[mask],
    )

    return predict(
        beta,
        x_test_std,
    )[0]


def metrics(
    observed,
    predicted,
):
    errors = (
        observed
        - predicted
    )

    mae = np.mean(
        np.abs(errors)
    )

    rmse = math.sqrt(
        np.mean(
            errors ** 2
        )
    )

    denominator = np.sum(
        (
            observed
            - np.mean(observed)
        ) ** 2
    )

    r2 = (
        1.0
        - np.sum(
            errors ** 2
        )
        / denominator
    )

    bias = np.mean(
        predicted
        - observed
    )

    return (
        mae,
        rmse,
        r2,
        bias,
    )


def direct_predictions(
    rows,
    model_name,
    external,
):
    x = make_x(
        rows,
        model_name,
    )

    trials = np.full(
        len(rows),
        500.0,
    )

    predictions = np.zeros(
        len(rows)
    )

    for held_out in range(
        len(rows)
    ):
        predictions[
            held_out
        ] = fit_predict_held_out(
            x,
            external,
            trials,
            held_out,
        )

    return predictions


def two_stage_predictions(
    rows,
    reach_model,
    conversion_model,
    external,
    reach,
):
    reach_x = make_x(
        rows,
        reach_model,
    )

    conversion_x = make_x(
        rows,
        conversion_model,
    )

    reach_trials = np.full(
        len(rows),
        500.0,
    )

    predicted_reach = np.zeros(
        len(rows)
    )

    predicted_conversion = np.zeros(
        len(rows)
    )

    for held_out in range(
        len(rows)
    ):
        predicted_reach[
            held_out
        ] = fit_predict_held_out(
            reach_x,
            reach,
            reach_trials,
            held_out,
        )

        predicted_conversion[
            held_out
        ] = fit_predict_held_out(
            conversion_x,
            external,
            reach,
            held_out,
        )

    predicted_external = (
        predicted_reach
        * predicted_conversion
    )

    return (
        predicted_external,
        predicted_reach,
        predicted_conversion,
    )


def print_results(
    results,
):
    print()
    print(
        f"{'Model':31}"
        f"{'MAE pp':>9}"
        f"{'RMSE pp':>10}"
        f"{'LOFO R2':>10}"
        f"{'Bias pp':>9}"
    )

    print(
        "-" * 69
    )

    for (
        name,
        mae,
        rmse,
        r2,
        bias,
        predictions,
    ) in results:
        print(
            f"{name:31}"
            f"{mae * 100:9.2f}"
            f"{rmse * 100:10.2f}"
            f"{r2:10.3f}"
            f"{bias * 100:9.2f}"
        )


def print_residuals(
    title,
    rows,
    observed,
    predicted,
):
    residuals = []

    for (
        row,
        actual,
        prediction,
    ) in zip(
        rows,
        observed,
        predicted,
    ):
        residuals.append(
            (
                abs(
                    actual
                    - prediction
                ),
                row["family"],
                actual,
                prediction,
                (
                    actual
                    - prediction
                ),
            )
        )

    residuals.sort(
        reverse=True
    )

    print()
    print(title)
    print(
        "-" * len(title)
    )

    for (
        absolute,
        family,
        actual,
        prediction,
        residual,
    ) in residuals:
        print(
            f"  {family:15} "
            f"actual={actual * 100:5.1f}% "
            f"pred={prediction * 100:5.1f}% "
            f"resid={residual * 100:+6.1f} pp"
        )


def main():
    rows = load_rows()

    external = np.asarray(
        [
            float(
                row[
                    "external_id_count"
                ]
            )
            for row in rows
        ]
    )

    reach = np.asarray(
        [
            float(
                row[
                    "raw_reach_count"
                ]
            )
            for row in rows
        ]
    )

    observed_external = (
        external
        / 500.0
    )

    results = []

    print()
    print(
        "DIRECT VS TWO-STAGE "
        "EXTERNAL-ID PREDICTION"
    )

    print(
        "================================="
    )

    print()
    print(
        "All predictions are strict "
        "leave-one-family-out."
    )

    print()
    print(
        "Two-stage external-ID probability "
        "= predicted reach x predicted "
        "conversion given reach."
    )

    for model_name in (
        DIRECT_MODELS
    ):
        predictions = (
            direct_predictions(
                rows,
                model_name,
                external,
            )
        )

        (
            mae,
            rmse,
            r2,
            bias,
        ) = metrics(
            observed_external,
            predictions,
        )

        results.append(
            (
                "Direct: "
                + model_name,
                mae,
                rmse,
                r2,
                bias,
                predictions,
            )
        )

    for (
        label,
        reach_model,
        conversion_model,
    ) in TWO_STAGE_MODELS:
        (
            predictions,
            predicted_reach,
            predicted_conversion,
        ) = two_stage_predictions(
            rows,
            reach_model,
            conversion_model,
            external,
            reach,
        )

        (
            mae,
            rmse,
            r2,
            bias,
        ) = metrics(
            observed_external,
            predictions,
        )

        results.append(
            (
                "Two-stage: "
                + label,
                mae,
                rmse,
                r2,
                bias,
                predictions,
            )
        )

    print_results(
        results
    )

    best = min(
        results,
        key=lambda item:
            item[1],
    )

    best_r2 = max(
        results,
        key=lambda item:
            item[3],
    )

    print()
    print(
        f"Best MAE: "
        f"{best[0]} "
        f"({best[1] * 100:.2f} pp)"
    )

    print(
        f"Best R2:  "
        f"{best_r2[0]} "
        f"({best_r2[3]:.3f})"
    )

    best_direct = min(
        [
            result
            for result in results
            if result[0].startswith(
                "Direct:"
            )
        ],
        key=lambda item:
            item[1],
    )

    best_two_stage = min(
        [
            result
            for result in results
            if result[0].startswith(
                "Two-stage:"
            )
        ],
        key=lambda item:
            item[1],
    )

    print_residuals(
        "BEST DIRECT MODEL RESIDUALS",
        rows,
        observed_external,
        best_direct[5],
    )

    print_residuals(
        "BEST TWO-STAGE MODEL RESIDUALS",
        rows,
        observed_external,
        best_two_stage[5],
    )


if __name__ == "__main__":
    main()