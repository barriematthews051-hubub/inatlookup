import csv
import math
import os

import numpy as np
from scipy.optimize import minimize


INPUT_FILE = os.path.join(
    "research",
    "data",
    "family_stage1_decomposition.csv",
)


RIDGE_PENALTY = 1e-4


MODELS = [
    (
        "Capacity",
        [
            "external_capacity",
        ],
    ),
    (
        "Identifiability",
        [
            "identifiability_score",
        ],
    ),
    (
        "Workload",
        [
            "log_workload",
        ],
    ),
    (
        "Capacity + Ident",
        [
            "external_capacity",
            "identifiability_score",
        ],
    ),
    (
        "Capacity + Workload",
        [
            "external_capacity",
            "log_workload",
        ],
    ),
    (
        "Ident + Workload",
        [
            "identifiability_score",
            "log_workload",
        ],
    ),
    (
        "All three",
        [
            "external_capacity",
            "identifiability_score",
            "log_workload",
        ],
    ),
]


OUTCOMES = [
    (
        "STAGE 1A RAW REACH",
        "raw_reach_count",
        None,
    ),
    (
        "STAGE 1A TOP-1 REACH",
        "top1_reach_count",
        None,
    ),
    (
        "STAGE 1A TOP-5 REACH",
        "top5_reach_count",
        None,
    ),
    (
        "STAGE 1B RAW CONVERSION",
        "external_id_count",
        "raw_reach_count",
    ),
    (
        "STAGE 1B TOP-1 CONVERSION",
        "external_id_count",
        "top1_reach_count",
    ),
    (
        "STAGE 1B TOP-5 CONVERSION",
        "external_id_count",
        "top5_reach_count",
    ),
]


def sigmoid(value):
    value = np.clip(
        value,
        -35.0,
        35.0,
    )

    return (
        1.0
        / (
            1.0
            + np.exp(
                -value
            )
        )
    )


def standardize(x):
    mean = np.mean(
        x,
        axis=0,
    )

    sd = np.std(
        x,
        axis=0,
        ddof=0,
    )

    if np.any(
        sd == 0
    ):
        raise ValueError(
            "Zero-variance predictor."
        )

    return (
        (
            x
            - mean
        )
        / sd,
        mean,
        sd,
    )


def fit_binomial(
    x_standardized,
    successes,
    trials,
):
    design = np.column_stack(
        [
            np.ones(
                len(
                    x_standardized
                )
            ),
            x_standardized,
        ]
    )

    pooled = (
        np.sum(successes)
        / np.sum(trials)
    )

    pooled = np.clip(
        pooled,
        1e-6,
        1 - 1e-6,
    )

    initial = np.zeros(
        design.shape[1]
    )

    initial[0] = math.log(
        pooled
        / (
            1.0
            - pooled
        )
    )

    def objective(beta):
        eta = design @ beta

        value = np.sum(
            trials
            * np.logaddexp(
                0.0,
                eta,
            )
            - successes
            * eta
        )

        value += (
            0.5
            * RIDGE_PENALTY
            * np.sum(
                beta[1:] ** 2
            )
        )

        return float(value)

    def gradient(beta):
        eta = design @ beta

        probability = sigmoid(
            eta
        )

        grad = (
            design.T
            @ (
                trials
                * probability
                - successes
            )
        )

        grad[1:] += (
            RIDGE_PENALTY
            * beta[1:]
        )

        return grad

    result = minimize(
        objective,
        initial,
        jac=gradient,
        method="BFGS",
        options={
            "gtol": 1e-7,
            "maxiter": 20000,
        },
    )

    if result.success:
        return result.x

    result = minimize(
        objective,
        result.x,
        jac=gradient,
        method="L-BFGS-B",
        options={
            "ftol": 1e-12,
            "gtol": 1e-7,
            "maxiter": 20000,
            "maxls": 100,
        },
    )

    if result.success:
        return result.x

    result = minimize(
        objective,
        result.x,
        method="Powell",
        options={
            "xtol": 1e-9,
            "ftol": 1e-9,
            "maxiter": 50000,
        },
    )

    if result.success:
        return result.x

    raise RuntimeError(
        f"Model failed: "
        f"{result.message}"
    )


def predict(
    beta,
    x_standardized,
):
    design = np.column_stack(
        [
            np.ones(
                len(
                    x_standardized
                )
            ),
            x_standardized,
        ]
    )

    return sigmoid(
        design @ beta
    )


def lofo_predictions(
    x,
    successes,
    trials,
):
    predictions = np.zeros(
        len(successes)
    )

    for held_out in range(
        len(successes)
    ):
        mask = np.ones(
            len(successes),
            dtype=bool,
        )

        mask[
            held_out
        ] = False

        x_train = x[
            mask
        ]

        x_test = x[
            [held_out]
        ]

        (
            x_train_std,
            mean,
            sd,
        ) = standardize(
            x_train
        )

        x_test_std = (
            x_test
            - mean
        ) / sd

        beta = fit_binomial(
            x_train_std,
            successes[
                mask
            ],
            trials[
                mask
            ],
        )

        predictions[
            held_out
        ] = predict(
            beta,
            x_test_std,
        )[0]

    return predictions


def metrics(
    observed,
    predicted,
):
    error = (
        observed
        - predicted
    )

    mae = np.mean(
        np.abs(
            error
        )
    )

    rmse = math.sqrt(
        np.mean(
            error ** 2
        )
    )

    denominator = np.sum(
        (
            observed
            - np.mean(
                observed
            )
        ) ** 2
    )

    if denominator:
        r2 = (
            1.0
            - np.sum(
                error ** 2
            )
            / denominator
        )
    else:
        r2 = float(
            "nan"
        )

    return (
        mae,
        rmse,
        r2,
    )


def load_data():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(
                handle
            )
        )

    if len(rows) != 18:
        raise ValueError(
            "Expected 18 family rows, "
            f"found {len(rows)}"
        )

    return rows


def run_outcome(
    rows,
    title,
    success_field,
    trial_field,
):
    print()
    print(title)
    print(
        "=" * len(title)
    )

    successes = np.asarray(
        [
            float(
                row[
                    success_field
                ]
            )
            for row in rows
        ]
    )

    if trial_field is None:
        trials = np.full(
            len(rows),
            500.0,
        )
    else:
        trials = np.asarray(
            [
                float(
                    row[
                        trial_field
                    ]
                )
                for row in rows
            ]
        )

    observed = (
        successes
        / trials
    )

    results = []

    for (
        model_name,
        predictors,
    ) in MODELS:
        x = np.asarray(
            [
                [
                    float(
                        row[
                            predictor
                        ]
                    )
                    for predictor
                    in predictors
                ]
                for row in rows
            ]
        )

        predicted = (
            lofo_predictions(
                x,
                successes,
                trials,
            )
        )

        (
            mae,
            rmse,
            r2,
        ) = metrics(
            observed,
            predicted,
        )

        results.append(
            (
                model_name,
                mae,
                rmse,
                r2,
            )
        )

    print()
    print(
        f"{'Model':23}"
        f"{'MAE pp':>10}"
        f"{'RMSE pp':>11}"
        f"{'LOFO R2':>10}"
    )

    print(
        "-" * 54
    )

    for (
        model_name,
        mae,
        rmse,
        r2,
    ) in results:
        print(
            f"{model_name:23}"
            f"{mae * 100:10.2f}"
            f"{rmse * 100:11.2f}"
            f"{r2:10.3f}"
        )

    best_mae = min(
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
        f"  Best MAE: "
        f"{best_mae[0]} "
        f"({best_mae[1] * 100:.2f} pp)"
    )

    print(
        f"  Best R2:  "
        f"{best_r2[0]} "
        f"({best_r2[3]:.3f})"
    )


def main():
    rows = load_data()

    print()
    print(
        "STAGE-1 PREDICTOR MODEL "
        "COMPARISON"
    )

    print(
        "============================="
    )

    print()
    print(
        "All performance measures are "
        "leave-one-family-out."
    )

    for (
        title,
        success_field,
        trial_field,
    ) in OUTCOMES:
        run_outcome(
            rows,
            title,
            success_field,
            trial_field,
        )


if __name__ == "__main__":
    main()