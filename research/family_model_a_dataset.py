import csv
import os


OUTPUT_FILE = os.path.join(
    "research",
    "data",
    "family_model_a_dataset.csv",
)


# These structural variables were fixed during the Phase 2
# candidate-screening / selection stage, before Phase 2
# identification outcomes were examined.
#
# identifiability:
#   low = 1
#   medium = 2
#   high = 3
#
# owner_* percentages and photo variables come from the
# frozen 100-observation candidate screening samples.

FAMILIES = [
    {
        "family": "Syrphidae",
        "taxon_id": 49995,
        "workload_6mo": 157169,
        "min_monthly_workload": 6635,
        "genus_richness": 267,
        "species_richness": 4086,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 59,
        "owner_genus_pct": 22,
        "owner_higher_pct": 15,
        "owner_none_pct": 4,
        "mean_photos": 1.89,
        "photos_4plus_pct": 12,
        "external_id_rate": 81.6,
    },
    {
        "family": "Asilidae",
        "taxon_id": 47982,
        "workload_6mo": 33960,
        "min_monthly_workload": 1847,
        "genus_richness": 435,
        "species_richness": 3175,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 26,
        "owner_genus_pct": 38,
        "owner_higher_pct": 33,
        "owner_none_pct": 3,
        "mean_photos": 1.69,
        "photos_4plus_pct": 6,
        "external_id_rate": 87.4,
    },
    {
        "family": "Geometridae",
        "taxon_id": 49530,
        "workload_6mo": 403107,
        "min_monthly_workload": 29208,
        "genus_richness": 2050,
        "species_richness": 24189,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 65,
        "owner_genus_pct": 24,
        "owner_higher_pct": 8,
        "owner_none_pct": 3,
        "mean_photos": 1.24,
        "photos_4plus_pct": 1,
        "external_id_rate": 56.4,
    },
    {
        "family": "Nymphalidae",
        "taxon_id": 47922,
        "workload_6mo": 491683,
        "min_monthly_workload": 42134,
        "genus_richness": 588,
        "species_richness": 6474,
        "identifiability": "high",
        "identifiability_score": 3,
        "owner_species_pct": 76,
        "owner_genus_pct": 13,
        "owner_higher_pct": 9,
        "owner_none_pct": 2,
        "mean_photos": 1.63,
        "photos_4plus_pct": 5,
        "external_id_rate": 84.8,
    },
    {
        "family": "Staphylinidae",
        "taxon_id": 47951,
        "workload_6mo": 49630,
        "min_monthly_workload": 3018,
        "genus_richness": 1509,
        "species_richness": 9799,
        "identifiability": "low",
        "identifiability_score": 1,
        "owner_species_pct": 42,
        "owner_genus_pct": 27,
        "owner_higher_pct": 28,
        "owner_none_pct": 3,
        "mean_photos": 2.09,
        "photos_4plus_pct": 14,
        "external_id_rate": 61.8,
    },
    {
        "family": "Asteraceae",
        "taxon_id": 47604,
        "workload_6mo": 1553138,
        "min_monthly_workload": 92686,
        "genus_richness": 1715,
        "species_richness": 25896,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 64,
        "owner_genus_pct": 21,
        "owner_higher_pct": 10,
        "owner_none_pct": 5,
        "mean_photos": 1.91,
        "photos_4plus_pct": 10,
        "external_id_rate": 58.4,
    },
    {
        "family": "Formicidae",
        "taxon_id": 47336,
        "workload_6mo": 237256,
        "min_monthly_workload": 17381,
        "genus_richness": 356,
        "species_richness": 11281,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 49,
        "owner_genus_pct": 31,
        "owner_higher_pct": 16,
        "owner_none_pct": 4,
        "mean_photos": 1.96,
        "photos_4plus_pct": 8,
        "external_id_rate": 78.4,
    },
    {
        "family": "Libellulidae",
        "taxon_id": 47819,
        "workload_6mo": 163692,
        "min_monthly_workload": 13024,
        "genus_richness": 141,
        "species_richness": 1040,
        "identifiability": "high",
        "identifiability_score": 3,
        "owner_species_pct": 74,
        "owner_genus_pct": 12,
        "owner_higher_pct": 9,
        "owner_none_pct": 5,
        "mean_photos": 1.55,
        "photos_4plus_pct": 6,
        "external_id_rate": 89.8,
    },
    {
        "family": "Orchidaceae",
        "taxon_id": 47217,
        "workload_6mo": 298543,
        "min_monthly_workload": 21635,
        "genus_richness": 707,
        "species_richness": 18890,
        "identifiability": "high",
        "identifiability_score": 3,
        "owner_species_pct": 71,
        "owner_genus_pct": 19,
        "owner_higher_pct": 6,
        "owner_none_pct": 4,
        "mean_photos": 1.90,
        "photos_4plus_pct": 10,
        "external_id_rate": 83.8,
    },
    {
        "family": "Poaceae",
        "taxon_id": 47434,
        "workload_6mo": 469508,
        "min_monthly_workload": 31712,
        "genus_richness": 794,
        "species_richness": 8425,
        "identifiability": "low",
        "identifiability_score": 1,
        "owner_species_pct": 67,
        "owner_genus_pct": 12,
        "owner_higher_pct": 17,
        "owner_none_pct": 4,
        "mean_photos": 1.78,
        "photos_4plus_pct": 9,
        "external_id_rate": 50.2,
    },
    {
        "family": "Russulaceae",
        "taxon_id": 48340,
        "workload_6mo": 29577,
        "min_monthly_workload": 2251,
        "genus_richness": 8,
        "species_richness": 1609,
        "identifiability": "low",
        "identifiability_score": 1,
        "owner_species_pct": 39,
        "owner_genus_pct": 49,
        "owner_higher_pct": 10,
        "owner_none_pct": 2,
        "mean_photos": 2.68,
        "photos_4plus_pct": 25,
        "external_id_rate": 47.2,
    },
    {
        "family": "Parmeliaceae",
        "taxon_id": 54321,
        "workload_6mo": 99528,
        "min_monthly_workload": 12181,
        "genus_richness": 85,
        "species_richness": 1722,
        "identifiability": "low",
        "identifiability_score": 1,
        "owner_species_pct": 56,
        "owner_genus_pct": 28,
        "owner_higher_pct": 15,
        "owner_none_pct": 1,
        "mean_photos": 1.57,
        "photos_4plus_pct": 5,
        "external_id_rate": 46.8,
    },
    {
        "family": "Salticidae",
        "taxon_id": 48139,
        "workload_6mo": 168617,
        "min_monthly_workload": 11788,
        "genus_richness": 680,
        "species_richness": 6406,
        "identifiability": "high",
        "identifiability_score": 3,
        "owner_species_pct": 49,
        "owner_genus_pct": 27,
        "owner_higher_pct": 18,
        "owner_none_pct": 6,
        "mean_photos": 2.19,
        "photos_4plus_pct": 15,
        "external_id_rate": 73.2,
    },
    {
        "family": "Lycosidae",
        "taxon_id": 47416,
        "workload_6mo": 72777,
        "min_monthly_workload": 4183,
        "genus_richness": 135,
        "species_richness": 2407,
        "identifiability": "low",
        "identifiability_score": 1,
        "owner_species_pct": 39,
        "owner_genus_pct": 15,
        "owner_higher_pct": 40,
        "owner_none_pct": 6,
        "mean_photos": 1.94,
        "photos_4plus_pct": 8,
        "external_id_rate": 64.6,
    },
    {
        "family": "Anatidae",
        "taxon_id": 6912,
        "workload_6mo": 550648,
        "min_monthly_workload": 63062,
        "genus_richness": 60,
        "species_richness": 195,
        "identifiability": "high",
        "identifiability_score": 3,
        "owner_species_pct": 87,
        "owner_genus_pct": 6,
        "owner_higher_pct": 6,
        "owner_none_pct": 1,
        "mean_photos": 1.44,
        "photos_4plus_pct": 6,
        "external_id_rate": 90.6,
    },
    {
        "family": "Colubridae",
        "taxon_id": 26504,
        "workload_6mo": 143068,
        "min_monthly_workload": 7905,
        "genus_richness": 263,
        "species_richness": 2168,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 81,
        "owner_genus_pct": 5,
        "owner_higher_pct": 9,
        "owner_none_pct": 5,
        "mean_photos": 1.96,
        "photos_4plus_pct": 12,
        "external_id_rate": 97.0,
    },
    {
        "family": "Limacidae",
        "taxon_id": 62471,
        "workload_6mo": 15880,
        "min_monthly_workload": 881,
        "genus_richness": 12,
        "species_richness": 67,
        "identifiability": "low",
        "identifiability_score": 1,
        "owner_species_pct": 69,
        "owner_genus_pct": 17,
        "owner_higher_pct": 13,
        "owner_none_pct": 1,
        "mean_photos": 1.82,
        "photos_4plus_pct": 9,
        "external_id_rate": 61.4,
    },
    {
        "family": "Asteriidae",
        "taxon_id": 47671,
        "workload_6mo": 15906,
        "min_monthly_workload": 1429,
        "genus_richness": 40,
        "species_richness": 161,
        "identifiability": "medium",
        "identifiability_score": 2,
        "owner_species_pct": 80,
        "owner_genus_pct": 9,
        "owner_higher_pct": 7,
        "owner_none_pct": 4,
        "mean_photos": 1.32,
        "photos_4plus_pct": 3,
        "external_id_rate": 96.2,
    },
]


def add_derived_variables(row):
    row = dict(row)

    row["mean_monthly_workload"] = (
        row["workload_6mo"] / 6
    )

    row["observations_per_species"] = (
        row["workload_6mo"]
        / row["species_richness"]
    )

    row["species_per_genus"] = (
        row["species_richness"]
        / row["genus_richness"]
    )

    return row


def main():
    rows = [
        add_derived_variables(row)
        for row in FAMILIES
    ]

    fields = [
        "family",
        "taxon_id",
        "workload_6mo",
        "mean_monthly_workload",
        "min_monthly_workload",
        "genus_richness",
        "species_richness",
        "observations_per_species",
        "species_per_genus",
        "identifiability",
        "identifiability_score",
        "owner_species_pct",
        "owner_genus_pct",
        "owner_higher_pct",
        "owner_none_pct",
        "mean_photos",
        "photos_4plus_pct",
        "external_id_rate",
    ]

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

    print()
    print("MODEL A FAMILY-LEVEL DATASET")
    print("============================")
    print()
    print(
        f"Families: {len(rows)}"
    )
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print()

    header = (
        f"{'Family':16}"
        f"{'Volume':>11}"
        f"{'Species':>10}"
        f"{'Obs/sp':>10}"
        f"{'Ident':>9}"
        f"{'Owner sp':>10}"
        f"{'Photos':>9}"
        f"{'Ext ID':>9}"
    )

    print(header)
    print("-" * len(header))

    for row in rows:
        print(
            f"{row['family']:16}"
            f"{row['workload_6mo']:11,d}"
            f"{row['species_richness']:10,d}"
            f"{row['observations_per_species']:10.1f}"
            f"{row['identifiability']:>9}"
            f"{row['owner_species_pct']:9.0f}%"
            f"{row['mean_photos']:9.2f}"
            f"{row['external_id_rate']:8.1f}%"
        )


if __name__ == "__main__":
    main()