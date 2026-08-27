import csv
import glob
import json
import math
import os
from collections import Counter

import numpy as np
from scipy.optimize import minimize


DATA_DIR = os.path.join(
    "research",
    "data",
)

CACHE_FILE = os.path.join(
    "research",
    "cache",
    "public_interactions_9000.json",
)

MODEL_A_FILE = os.path.join(
    DATA_DIR,
    "family_model_a_dataset.csv",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "family_stage1_decomposition.csv",
)


FAMILIES = [
    ("Syrphidae", "hoverflies"),
    ("Asilidae", "robber flies"),
    ("Geometridae", "geometer moths"),
    ("Nymphalidae", "brush-footed butterflies"),
    ("Staphylinidae", "rove beetles"),
    ("Asteraceae", "daisy/sunflower family"),
    ("Formicidae", "ants"),
    ("Libellulidae", "skimmers and perchers"),
    ("Orchidaceae", "orchid family"),
    ("Poaceae", "grass family"),
    ("Russulaceae", "russulas and milkcaps"),
    ("Parmeliaceae", "shield lichens"),
    ("Salticidae", "jumping spiders"),
    ("Lycosidae", "wolf spiders"),
    ("Anatidae", "ducks, geese and swans"),
    ("Colubridae", "colubrid snakes"),
    ("Limacidae", "keeled slugs"),
    ("Asteriidae", "common sea stars"),
]


PREDICTOR_NAMES = [
    "external_capacity",
    "identifiability_score",
    "log_workload",
]


# Very small L2 penalty on predictor
# coefficients only. This stabilizes
# near-separated LOFO binomial fits
# without materially changing estimates.
RIDGE_PENALTY = 1e-4


def percent(
    numerator,
    denominator,
):
    if not denominator:
        return 0.0

    return (
        numerator
        / denominator
        * 100
    )


def normalize(text):
    return "".join(
        char.lower()
        for char in str(text)
        if char.isalnum()
    )


def load_model_a_predictors():
    rows = {}

    with open(
        MODEL_A_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        fieldnames = (
            reader.fieldnames
            or []
        )

        normalized = {
            normalize(field):
                field
            for field
            in fieldnames
        }

        if (
            "identifiabilityscore"
            not in normalized
        ):
            raise ValueError(
                "Could not find "
                "identifiability_score "
                f"in {MODEL_A_FILE}. "
                f"Columns: {fieldnames}"
            )

        if (
            "workload6mo"
            not in normalized
        ):
            raise ValueError(
                "Could not find "
                "workload_6mo "
                f"in {MODEL_A_FILE}. "
                f"Columns: {fieldnames}"
            )

        ident_field = (
            normalized[
                "identifiabilityscore"
            ]
        )

        workload_field = (
            normalized[
                "workload6mo"
            ]
        )

        for row in reader:
            family = row["family"]

            workload = float(
                row[
                    workload_field
                ]
            )

            if workload <= 0:
                raise ValueError(
                    f"{family}: workload "
                    f"must be positive, "
                    f"found {workload}"
                )

            rows[family] = {
                "identifiability_score":
                    float(
                        row[
                            ident_field
                        ]
                    ),

                "workload_6mo":
                    workload,

                "log_workload":
                    math.log(
                        workload
                    ),
            }

    return rows


def capacity_column_score(
    filename,
    column,
):
    name = normalize(
        column
    )

    score = 0

    if "external" in name:
        score += 10

    if (
        "identification" in name
        or "identifications" in name
        or "ids" in name
    ):
        score += 5

    if (
        "perobservation" in name
        or "perobs" in name
    ):
        score += 15

    if "2024" in name:
        score += 3

    if any(
        bad in name
        for bad in [
            "rate",
            "percent",
            "share",
            "unique",
            "top1",
            "top5",
            "top10",
            "top20",
        ]
    ):
        score -= 20

    basename = normalize(
        os.path.basename(
            filename
        )
    )

    if (
        "familyidentifierstructure"
        in basename
    ):
        score += 10

    return score


def find_external_capacity():
    candidates = []

    for filename in glob.glob(
        os.path.join(
            DATA_DIR,
            "*.csv",
        )
    ):
        try:
            with open(
                filename,
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                reader = csv.reader(
                    handle
                )

                header = next(
                    reader,
                    [],
                )

        except Exception:
            continue

        if "family" not in header:
            continue

        for column in header:
            score = (
                capacity_column_score(
                    filename,
                    column,
                )
            )

            if score >= 25:
                candidates.append(
                    (
                        score,
                        filename,
                        column,
                    )
                )

    if not candidates:
        external_columns = []

        for filename in glob.glob(
            os.path.join(
                DATA_DIR,
                "*.csv",
            )
        ):
            try:
                with open(
                    filename,
                    "r",
                    encoding="utf-8",
                    newline="",
                ) as handle:
                    reader = csv.reader(
                        handle
                    )

                    header = next(
                        reader,
                        [],
                    )

            except Exception:
                continue

            for column in header:
                if (
                    "external"
                    in normalize(column)
                ):
                    external_columns.append(
                        (
                            filename,
                            column,
                        )
                    )

        raise ValueError(
            "Could not automatically find "
            "the 2024 external IDs per "
            "observation column.\n"
            "External-looking columns found:\n"
            + "\n".join(
                f"  {filename}: {column}"
                for filename, column
                in external_columns
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2],
        )
    )

    score, filename, column = (
        candidates[0]
    )

    values = {}

    with open(
        filename,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row in reader:
            family = row.get(
                "family"
            )

            if family:
                value = row.get(
                    column
                )

                if (
                    value is not None
                    and str(value).strip()
                ):
                    values[
                        family
                    ] = float(
                        value
                    )

    missing = [
        family
        for family, _
        in FAMILIES
        if family not in values
    ]

    if missing:
        raise ValueError(
            f"Capacity source "
            f"{filename}, column "
            f"{column}, is missing "
            f"families: {missing}"
        )

    return (
        filename,
        column,
        values,
    )


def load_interaction_records():
    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(
            handle
        )

    result = {}

    for record in (
        data["records"].values()
    ):
        if (
            record.get("status")
            != "ok"
        ):
            continue

        family = record[
            "family"
        ]

        result.setdefault(
            family,
            []
        ).append(
            record
        )

    return result


def reviewer_ids(record):
    return {
        int(value)
        for value in record.get(
            "reviewer_no_id_user_ids",
            [],
        )
    }


def family_outcomes(
    rows,
):
    if len(rows) != 500:
        raise ValueError(
            "Expected 500 observations "
            f"but found {len(rows)}"
        )

    external = sum(
        bool(
            row[
                "external_id_present"
            ]
        )
        for row in rows
    )

    no_id_rows = [
        row
        for row in rows
        if not row[
            "external_id_present"
        ]
    ]

    counter = Counter()

    for row in no_id_rows:
        for user_id in reviewer_ids(
            row
        ):
            counter[
                user_id
            ] += 1

    ranked = (
        counter.most_common()
    )

    top1 = (
        {ranked[0][0]}
        if ranked
        else set()
    )

    top5 = {
        user_id
        for user_id, count
        in ranked[:5]
    }

    def reach_count(
        excluded,
    ):
        reached_no_id = sum(
            bool(
                reviewer_ids(row)
                - excluded
            )
            for row in no_id_rows
        )

        return (
            external
            + reached_no_id
        )

    raw_reach = reach_count(
        set()
    )

    top1_reach = reach_count(
        top1
    )

    top5_reach = reach_count(
        top5
    )

    return {
        "external":
            external,

        "raw_reach":
            raw_reach,

        "top1_reach":
            top1_reach,

        "top5_reach":
            top5_reach,

        "raw_conversion":
            (
                external
                / raw_reach
            ),

        "top1_conversion":
            (
                external
                / top1_reach
            ),

        "top5_conversion":
            (
                external
                / top5_reach
            ),

        "dominant_reviewer":
            (
                ranked[0][0]
                if ranked
                else None
            ),

        "dominant_reviewer_count":
            (
                ranked[0][1]
                if ranked
                else 0
            ),
    }


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


def standardize(
    x,
):
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
            "A predictor has zero "
            "standard deviation."
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

    def objective(
        beta,
    ):
        eta = design @ beta

        # Stable grouped-binomial
        # negative log likelihood:
        #
        # n * log(1 + exp(eta))
        # - y * eta
        #
        # np.logaddexp prevents numerical
        # overflow for large eta.
        value = np.sum(
            trials
            * np.logaddexp(
                0.0,
                eta,
            )
            - successes
            * eta
        )

        # Do not penalize the intercept.
        value += (
            0.5
            * RIDGE_PENALTY
            * np.sum(
                beta[1:] ** 2
            )
        )

        return float(value)

    def gradient(
        beta,
    ):
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

    # First choice: BFGS with the
    # analytic gradient.
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

    # Second attempt: L-BFGS-B.
    result2 = minimize(
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

    if result2.success:
        return result2.x

    # Last-resort derivative-free
    # optimizer. There are only four
    # coefficients, so this is still
    # inexpensive.
    best_start = (
        result2.x
        if np.isfinite(
            objective(
                result2.x
            )
        )
        else initial
    )

    result3 = minimize(
        objective,
        best_start,
        method="Powell",
        options={
            "xtol": 1e-9,
            "ftol": 1e-9,
            "maxiter": 50000,
        },
    )

    if result3.success:
        return result3.x

    raise RuntimeError(
        "Penalized binomial model "
        "failed after BFGS, "
        "L-BFGS-B and Powell. "
        f"BFGS: {result.message}; "
        f"L-BFGS-B: {result2.message}; "
        f"Powell: {result3.message}"
    )



def predict_probability(
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
        train_mask = np.ones(
            len(successes),
            dtype=bool,
        )

        train_mask[
            held_out
        ] = False

        x_train = x[
            train_mask
        ]

        x_test = x[
            [held_out]
        ]

        (
            x_train_standardized,
            mean,
            sd,
        ) = standardize(
            x_train
        )

        x_test_standardized = (
            x_test
            - mean
        ) / sd

        beta = fit_binomial(
            x_train_standardized,
            successes[
                train_mask
            ],
            trials[
                train_mask
            ],
        )

        predictions[
            held_out
        ] = (
            predict_probability(
                beta,
                x_test_standardized,
            )[0]
        )

    return predictions


def prediction_metrics(
    observed,
    predicted,
):
    error = (
        predicted
        - observed
    )

    mae = np.mean(
        np.abs(error)
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
                (
                    observed
                    - predicted
                ) ** 2
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


def run_model(
    title,
    families,
    x,
    successes,
    trials,
    show_residuals=False,
):
    observed = (
        successes
        / trials
    )

    (
        x_standardized,
        mean,
        sd,
    ) = standardize(
        x
    )

    beta = fit_binomial(
        x_standardized,
        successes,
        trials,
    )

    fitted = (
        predict_probability(
            beta,
            x_standardized,
        )
    )

    lofo = lofo_predictions(
        x,
        successes,
        trials,
    )

    (
        mae,
        rmse,
        r2,
    ) = prediction_metrics(
        observed,
        lofo,
    )

    print()
    print(title)
    print(
        "-" * len(title)
    )

    print(
        f"  Overall observed rate: "
        f"{percent(
            np.sum(successes),
            np.sum(trials)
        ):.1f}%"
    )

    print()
    print(
        "  STANDARDIZED COEFFICIENTS"
    )

    print(
        f"    Intercept: "
        f"{beta[0]:+.3f}"
    )

    for index, name in enumerate(
        PREDICTOR_NAMES,
        start=1,
    ):
        odds_ratio = math.exp(
            beta[index]
        )

        print(
            f"    {name:24} "
            f"{beta[index]:+8.3f}  "
            f"OR/SD={odds_ratio:7.3f}"
        )

    print()
    print(
        "  LEAVE-ONE-FAMILY-OUT"
    )

    print(
        f"    MAE:  "
        f"{mae * 100:.2f} pp"
    )

    print(
        f"    RMSE: "
        f"{rmse * 100:.2f} pp"
    )

    print(
        f"    R2:   "
        f"{r2:.3f}"
    )

    if show_residuals:
        residual_rows = []

        for (
            family,
            actual,
            prediction,
        ) in zip(
            families,
            observed,
            lofo,
        ):
            residual_rows.append(
                (
                    abs(
                        actual
                        - prediction
                    ),
                    family,
                    actual,
                    prediction,
                    (
                        actual
                        - prediction
                    ),
                )
            )

        residual_rows.sort(
            reverse=True
        )

        print()
        print(
            "  LOFO RESIDUALS "
            "(largest first)"
        )

        for (
            absolute,
            family,
            actual,
            prediction,
            residual,
        ) in residual_rows:
            print(
                f"    {family:15} "
                f"actual={actual * 100:5.1f}% "
                f"pred={prediction * 100:5.1f}% "
                f"resid={residual * 100:+6.1f} pp"
            )

    return {
        "beta":
            beta,

        "fitted":
            fitted,

        "lofo":
            lofo,

        "observed":
            observed,

        "mae":
            mae,

        "rmse":
            rmse,

        "r2":
            r2,
    }


def main():
    model_a = (
        load_model_a_predictors()
    )

    (
        capacity_file,
        capacity_column,
        capacity_values,
    ) = find_external_capacity()

    interactions = (
        load_interaction_records()
    )

    print()
    print(
        "FAMILY STAGE-1 DECOMPOSITION"
    )
    print(
        "============================"
    )

    print()
    print(
        "Predictors:"
    )

    print(
        "  2024 external identifier "
        "capacity"
    )

    print(
        "  identifiability score"
    )

    print(
        "  log 6-month workload"
    )

    print()
    print(
        "External-capacity source:"
    )

    print(
        f"  File:   "
        f"{capacity_file}"
    )

    print(
        f"  Column: "
        f"{capacity_column}"
    )

    families = []
    common_names = []
    predictor_rows = []
    outcome_rows = []

    for family, common_name in FAMILIES:
        if family not in model_a:
            raise ValueError(
                f"{family} missing "
                f"from {MODEL_A_FILE}"
            )

        if family not in interactions:
            raise ValueError(
                f"{family} missing "
                "from interaction cache"
            )

        outcomes = family_outcomes(
            interactions[
                family
            ]
        )

        families.append(
            family
        )

        common_names.append(
            common_name
        )

        predictor_rows.append(
            [
                capacity_values[
                    family
                ],
                model_a[
                    family
                ][
                    "identifiability_score"
                ],
                model_a[
                    family
                ][
                    "log_workload"
                ],
            ]
        )

        outcome_rows.append(
            outcomes
        )

    x = np.asarray(
        predictor_rows,
        dtype=float,
    )

    external = np.asarray(
        [
            row["external"]
            for row in outcome_rows
        ],
        dtype=float,
    )

    raw_reach = np.asarray(
        [
            row["raw_reach"]
            for row in outcome_rows
        ],
        dtype=float,
    )

    top1_reach = np.asarray(
        [
            row["top1_reach"]
            for row in outcome_rows
        ],
        dtype=float,
    )

    top5_reach = np.asarray(
        [
            row["top5_reach"]
            for row in outcome_rows
        ],
        dtype=float,
    )

    all_500 = np.full(
        len(families),
        500.0,
    )

    print()
    print(
        "FAMILY OUTCOMES"
    )
    print(
        "==============="
    )

    print()
    print(
        f"{'Family':15}"
        f"{'Ext ID':>9}"
        f"{'RawReach':>10}"
        f"{'Top1':>9}"
        f"{'Top5':>9}"
        f"{'RawConv':>10}"
        f"{'Top5Conv':>10}"
    )

    print(
        "-" * 72
    )

    for (
        family,
        outcomes,
    ) in zip(
        families,
        outcome_rows,
    ):
        print(
            f"{family:15}"
            f"{outcomes['external']:4}/500"
            f"{outcomes['raw_reach']:5}/500"
            f"{outcomes['top1_reach']:5}/500"
            f"{outcomes['top5_reach']:5}/500"
            f"{outcomes['raw_conversion'] * 100:9.1f}%"
            f"{outcomes['top5_conversion'] * 100:9.1f}%"
        )

    stage1a_raw = run_model(
        "STAGE 1A - RAW REVIEW-BASED REACH",
        families,
        x,
        raw_reach,
        all_500,
        show_residuals=True,
    )

    stage1a_top1 = run_model(
        "STAGE 1A - TOP-1 SENSITIVITY REACH",
        families,
        x,
        top1_reach,
        all_500,
    )

    stage1a_top5 = run_model(
        "STAGE 1A - TOP-5 SENSITIVITY REACH",
        families,
        x,
        top5_reach,
        all_500,
    )

    stage1b_raw = run_model(
        "STAGE 1B - RAW ID CONVERSION",
        families,
        x,
        external,
        raw_reach,
        show_residuals=True,
    )

    stage1b_top1 = run_model(
        "STAGE 1B - TOP-1 SENSITIVITY CONVERSION",
        families,
        x,
        external,
        top1_reach,
    )

    stage1b_top5 = run_model(
        "STAGE 1B - TOP-5 SENSITIVITY CONVERSION",
        families,
        x,
        external,
        top5_reach,
    )

    fields = [
        "family",
        "common_name",
        "external_capacity",
        "identifiability_score",
        "workload_6mo",
        "log_workload",
        "external_id_count",
        "raw_reach_count",
        "top1_reach_count",
        "top5_reach_count",
        "raw_reach_rate",
        "top1_reach_rate",
        "top5_reach_rate",
        "raw_conversion_rate",
        "top1_conversion_rate",
        "top5_conversion_rate",
        "stage1a_raw_lofo_prediction",
        "stage1b_raw_lofo_prediction",
        "dominant_reviewer",
        "dominant_reviewer_count",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        for index, family in enumerate(
            families
        ):
            outcomes = (
                outcome_rows[
                    index
                ]
            )

            writer.writerow(
                {
                    "family":
                        family,

                    "common_name":
                        common_names[
                            index
                        ],

                    "external_capacity":
                        x[index, 0],

                    "identifiability_score":
                        x[index, 1],

                    "workload_6mo":
                        model_a[
                            family
                        ][
                            "workload_6mo"
                        ],

                    "log_workload":
                        x[index, 2],

                    "external_id_count":
                        int(
                            external[
                                index
                            ]
                        ),

                    "raw_reach_count":
                        int(
                            raw_reach[
                                index
                            ]
                        ),

                    "top1_reach_count":
                        int(
                            top1_reach[
                                index
                            ]
                        ),

                    "top5_reach_count":
                        int(
                            top5_reach[
                                index
                            ]
                        ),

                    "raw_reach_rate":
                        raw_reach[
                            index
                        ] / 500,

                    "top1_reach_rate":
                        top1_reach[
                            index
                        ] / 500,

                    "top5_reach_rate":
                        top5_reach[
                            index
                        ] / 500,

                    "raw_conversion_rate":
                        external[
                            index
                        ] / raw_reach[
                            index
                        ],

                    "top1_conversion_rate":
                        external[
                            index
                        ] / top1_reach[
                            index
                        ],

                    "top5_conversion_rate":
                        external[
                            index
                        ] / top5_reach[
                            index
                        ],

                    "stage1a_raw_lofo_prediction":
                        stage1a_raw[
                            "lofo"
                        ][index],

                    "stage1b_raw_lofo_prediction":
                        stage1b_raw[
                            "lofo"
                        ][index],

                    "dominant_reviewer":
                        outcomes[
                            "dominant_reviewer"
                        ],

                    "dominant_reviewer_count":
                        outcomes[
                            "dominant_reviewer_count"
                        ],
                }
            )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "These are family-level "
        "descriptive/predictive models."
    )

    print(
        "With only 18 family units, "
        "do not interpret binomial "
        "sample size as 9,000 "
        "independent taxon-level units."
    )


if __name__ == "__main__":
    main()