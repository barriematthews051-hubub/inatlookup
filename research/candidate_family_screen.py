import csv
import gzip
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

TAXA_PATH = Path(
    r"K:\inat-open-data\taxa.csv.gz"
)



OUTPUT_PATH = (
    REPO_ROOT
    / "research"
    / "data"
    / "candidate_family_screen.csv"
)

COUNT_CACHE_PATH = (
    REPO_ROOT
    / "research"
    / "cache"
    / "candidate_family_counts.json"
)

API_BASE = (
    "https://api.inaturalist.org/v1/observations"
)

REQUEST_DELAY = 1.1

MONTHS = [
    ("2025-01", "2025-01-01", "2025-01-31"),
    ("2025-02", "2025-02-01", "2025-02-28"),
    ("2025-03", "2025-03-01", "2025-03-31"),
    ("2025-04", "2025-04-01", "2025-04-30"),
    ("2025-05", "2025-05-01", "2025-05-31"),
    ("2025-06", "2025-06-01", "2025-06-30"),
]



CANDIDATES = [
    # Insects
    {
        "family": "Syrphidae",
        "broad_group": "Insects",
        "existing_pilot": 1,
        "identifiability": "medium",
    },
    {
        "family": "Asilidae",
        "broad_group": "Insects",
        "existing_pilot": 1,
        "identifiability": "medium",
    },
    {
        "family": "Geometridae",
        "broad_group": "Insects",
        "existing_pilot": 1,
        "identifiability": "medium",
    },
    {
        "family": "Nymphalidae",
        "broad_group": "Insects",
        "existing_pilot": 1,
        "identifiability": "high",
    },
    {
        "family": "Staphylinidae",
        "broad_group": "Insects",
        "existing_pilot": 1,
        "identifiability": "low",
    },
    {
        "family": "Apidae",
        "broad_group": "Insects",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Formicidae",
        "broad_group": "Insects",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Libellulidae",
        "broad_group": "Insects",
        "existing_pilot": 0,
        "identifiability": "high",
    },

    # Vascular plants
    {
        "family": "Asteraceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 1,
        "identifiability": "medium",
    },
    {
        "family": "Orchidaceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 0,
        "identifiability": "high",
    },
    {
        "family": "Poaceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 0,
        "identifiability": "low",
    },
    {
        "family": "Cyperaceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 0,
        "identifiability": "low",
    },
    {
        "family": "Fabaceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Rosaceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Ericaceae",
        "broad_group": "Vascular plants",
        "existing_pilot": 0,
        "identifiability": "medium",
    },

    # Fungi / lichens
    {
        "family": "Agaricaceae",
        "broad_group": "Fungi / lichens",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Russulaceae",
        "broad_group": "Fungi / lichens",
        "existing_pilot": 0,
        "identifiability": "low",
    },
    {
        "family": "Boletaceae",
        "broad_group": "Fungi / lichens",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Polyporaceae",
        "broad_group": "Fungi / lichens",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Parmeliaceae",
        "broad_group": "Fungi / lichens",
        "existing_pilot": 0,
        "identifiability": "low",
    },
    {
        "family": "Physciaceae",
        "broad_group": "Fungi / lichens",
        "existing_pilot": 0,
        "identifiability": "low",
    },

    # Arachnids
    {
        "family": "Salticidae",
        "broad_group": "Arachnids",
        "existing_pilot": 0,
        "identifiability": "high",
    },
    {
        "family": "Araneidae",
        "broad_group": "Arachnids",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Lycosidae",
        "broad_group": "Arachnids",
        "existing_pilot": 0,
        "identifiability": "low",
    },
    {
        "family": "Thomisidae",
        "broad_group": "Arachnids",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Theridiidae",
        "broad_group": "Arachnids",
        "existing_pilot": 0,
        "identifiability": "low",
    },

    # Vertebrates
    {
        "family": "Anatidae",
        "broad_group": "Vertebrates",
        "existing_pilot": 0,
        "identifiability": "high",
    },
    {
        "family": "Accipitridae",
        "broad_group": "Vertebrates",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Corvidae",
        "broad_group": "Vertebrates",
        "existing_pilot": 0,
        "identifiability": "high",
    },
    {
        "family": "Sciuridae",
        "broad_group": "Vertebrates",
        "existing_pilot": 0,
        "identifiability": "high",
    },
    {
        "family": "Colubridae",
        "broad_group": "Vertebrates",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Hylidae",
        "broad_group": "Vertebrates",
        "existing_pilot": 0,
        "identifiability": "medium",
    },

    # Other invertebrates
    {
        "family": "Helicidae",
        "broad_group": "Other invertebrates",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Limacidae",
        "broad_group": "Other invertebrates",
        "existing_pilot": 0,
        "identifiability": "low",
    },
    {
        "family": "Muricidae",
        "broad_group": "Other invertebrates",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
    {
        "family": "Asteriidae",
        "broad_group": "Other invertebrates",
        "existing_pilot": 0,
        "identifiability": "medium",
    },
]


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def is_active(value):
    value = clean(value).lower()

    return value in {
        "1",
        "true",
        "t",
        "yes",
    }


def resolve_candidate_families():
    print(
        "Pass 1: resolving candidate family IDs..."
    )

    wanted_names = {
        item["family"]
        for item in CANDIDATES
    }

    matches = defaultdict(list)

    with gzip.open(
        TAXA_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            name = clean(row["name"])

            if name not in wanted_names:
                continue

            if clean(row["rank"]) != "family":
                continue

            matches[name].append(row)

    resolved = {}

    for item in CANDIDATES:
        name = item["family"]
        candidates = matches.get(name, [])

        active = [
            row
            for row in candidates
            if is_active(row["active"])
        ]

        if len(active) == 1:
            resolved[name] = active[0]

        elif len(active) == 0:
            print(
                f"  WARNING: no active family "
                f"found for {name}"
            )

        else:
            print(
                f"  WARNING: multiple active "
                f"family records found for {name}"
            )

    print(
        f"Resolved active families: "
        f"{len(resolved)} / "
        f"{len(CANDIDATES)}"
    )

    return resolved


def ancestry_ids(value):
    value = clean(value)

    if not value:
        return set()

    return {
        part
        for part in value.split("/")
        if part
    }


def load_count_cache():
    if not COUNT_CACHE_PATH.exists():
        return {}

    with COUNT_CACHE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def save_count_cache(cache):
    COUNT_CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with COUNT_CACHE_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            cache,
            handle,
            indent=2,
            sort_keys=True,
        )


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "inatlookup-research-pilot/0.4 "
                "candidate-family-screen"
            ),
        },
    )

    delays = [
        5,
        10,
        20,
        40,
        60,
    ]

    for attempt in range(
        len(delays) + 1
    ):
        try:
            with urllib.request.urlopen(
                request,
                timeout=60,
            ) as response:
                payload = json.load(
                    response
                )

            time.sleep(
                REQUEST_DELAY
            )

            return payload

        except urllib.error.HTTPError as exc:
            if (
                exc.code == 429
                and attempt < len(delays)
            ):
                delay = delays[attempt]

                print(
                    f"    HTTP 429; retrying "
                    f"in {delay}s..."
                )

                time.sleep(delay)
                continue

            raise


def observation_count(
    taxon_id,
    created_d1,
    created_d2,
):
    params = {
        "taxon_id": taxon_id,
        "created_d1": created_d1,
        "created_d2": (
            f"{created_d2}T23:59:59"
        ),
        "per_page": 1,
    }

    url = (
        API_BASE
        + "?"
        + urllib.parse.urlencode(params)
    )

    payload = fetch_json(url)

    return int(
        payload["total_results"]
    )


def fetch_monthly_counts(resolved):
    print(
        "\nPass 3: fetching Jan-Jun 2025 "
        "created-observation counts..."
    )

    cache = load_count_cache()

    counts = {}

    for item in CANDIDATES:
        family = item["family"]
        taxon = resolved.get(family)

        if taxon is None:
            continue

        taxon_id = clean(
            taxon["taxon_id"]
        )

        family_counts = {}

        print(
            f"\n{family} ({taxon_id})"
        )

        for month, start, end in MONTHS:
            key = (
                f"{taxon_id}|{start}|{end}"
            )

            if key in cache:
                count = int(
                    cache[key]
                )

                print(
                    f"  {month}: "
                    f"{count:,} "
                    f"(cached)"
                )

            else:
                count = observation_count(
                    taxon_id,
                    start,
                    end,
                )

                cache[key] = count
                save_count_cache(cache)

                print(
                    f"  {month}: "
                    f"{count:,}"
                )

            family_counts[
                month
            ] = count

        counts[family] = family_counts

    return counts









def count_descendants(resolved):
    print(
        "\nPass 2: counting active descendants..."
    )

    family_id_to_name = {
        clean(row["taxon_id"]): name
        for name, row in resolved.items()
    }

    counts = {
        name: {
            "active_descendants": 0,
            "active_genera": 0,
            "active_species": 0,
            "active_subspecies": 0,
        }
        for name in resolved
    }

    rows_read = 0

    with gzip.open(
        TAXA_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            rows_read += 1

            if not is_active(row["active"]):
                continue

            ancestors = ancestry_ids(
                row["ancestry"]
            )

            candidate_ids = (
                ancestors
                & family_id_to_name.keys()
            )

            if not candidate_ids:
                continue

            rank = clean(row["rank"])

            for family_id in candidate_ids:
                family_name = (
                    family_id_to_name[family_id]
                )

                counts[
                    family_name
                ]["active_descendants"] += 1

                if rank == "genus":
                    counts[
                        family_name
                    ]["active_genera"] += 1

                elif rank == "species":
                    counts[
                        family_name
                    ]["active_species"] += 1

                elif rank == "subspecies":
                    counts[
                        family_name
                    ]["active_subspecies"] += 1

    print(
        f"Taxa rows scanned: {rows_read:,}"
    )

    return counts


def build_output_rows(
    resolved,
    counts,
    monthly_counts,
):
    rows = []

    for item in CANDIDATES:
        name = item["family"]
        taxon = resolved.get(name)

        if taxon is None:
            rows.append({
                "family": name,
                "broad_group":
                    item["broad_group"],
                "existing_pilot":
                    item["existing_pilot"],
                "identifiability":
                    item["identifiability"],
                "resolved": 0,
                "taxon_id": "",
                "active": "",
                "rank_level": "",
                "active_descendants": "",
                "active_genera": "",
                "active_species": "",
                "active_subspecies": "",
                "species_per_genus": "",
                "jan_2025_created": "",
                "feb_2025_created": "",
                "mar_2025_created": "",
                "apr_2025_created": "",
                "may_2025_created": "",
                "jun_2025_created": "",
                "jan_jun_2025_created": "",
                "mean_monthly_created": "",
                "min_monthly_created": "",
                "eligible_monthly_100": "",
            })
            continue

        family_counts = counts[name]

        genera = family_counts[
            "active_genera"
        ]
        species = family_counts[
            "active_species"
        ]


        if genera:
            species_per_genus = (
                species / genera
            )
        else:
            species_per_genus = None

        month_counts = (
            monthly_counts.get(
                name,
                {},
            )
        )

        monthly_values = [
            month_counts.get(
                month,
                0,
            )
            for month, _, _ in MONTHS
        ]

        six_month_total = sum(
            monthly_values
        )

        mean_monthly = (
            six_month_total / 6
        )

        min_monthly = min(
            monthly_values
        )

        eligible_monthly_100 = int(
            min_monthly >= 100
        )

        rows.append({
            "family": name,
            "broad_group":
                item["broad_group"],
            "existing_pilot":
                item["existing_pilot"],
            "identifiability":
                item["identifiability"],
            "resolved": 1,
            "taxon_id":
                clean(taxon["taxon_id"]),
            "active":
                clean(taxon["active"]),
            "rank_level":
                clean(taxon["rank_level"]),
            "active_descendants":
                family_counts[
                    "active_descendants"
                ],
            "active_genera":
                genera,
            "active_species":
                species,
            "active_subspecies":
                family_counts[
                    "active_subspecies"
                ],


            "species_per_genus":
                (
                    f"{species_per_genus:.2f}"
                    if species_per_genus
                    is not None
                    else ""
                ),

            "jan_2025_created":
                month_counts.get(
                    "2025-01",
                    0,
                ),
            "feb_2025_created":
                month_counts.get(
                    "2025-02",
                    0,
                ),
            "mar_2025_created":
                month_counts.get(
                    "2025-03",
                    0,
                ),
            "apr_2025_created":
                month_counts.get(
                    "2025-04",
                    0,
                ),
            "may_2025_created":
                month_counts.get(
                    "2025-05",
                    0,
                ),
            "jun_2025_created":
                month_counts.get(
                    "2025-06",
                    0,
                ),

            "jan_jun_2025_created":
                six_month_total,

            "mean_monthly_created":
                f"{mean_monthly:.1f}",

            "min_monthly_created":
                min_monthly,

            "eligible_monthly_100":
                eligible_monthly_100,
        })





    return rows



def add_derived_metrics(rows):
    resolved_rows = [
        row
        for row in rows
        if row["resolved"] == 1
    ]

    for row in rows:
        if row["resolved"] != 1:
            row["observations_per_species"] = ""
            row["log10_six_month_volume"] = ""
            row["log10_species_richness"] = ""
            row["workload_tier"] = ""
            row["richness_tier"] = ""
            continue

        species = int(
            row["active_species"]
        )

        volume = int(
            row["jan_jun_2025_created"]
        )

        if species > 0:
            observations_per_species = (
                volume / species
            )

            row["observations_per_species"] = (
                f"{observations_per_species:.2f}"
            )

            row["log10_species_richness"] = (
                f"{math.log10(species):.3f}"
            )
        else:
            row["observations_per_species"] = ""
            row["log10_species_richness"] = ""

        if volume > 0:
            row["log10_six_month_volume"] = (
                f"{math.log10(volume):.3f}"
            )
        else:
            row["log10_six_month_volume"] = ""

        row["workload_tier"] = ""
        row["richness_tier"] = ""

    volume_values = sorted(
        int(
            row["jan_jun_2025_created"]
        )
        for row in resolved_rows
    )

    richness_values = sorted(
        int(
            row["active_species"]
        )
        for row in resolved_rows
    )

    n = len(resolved_rows)

    workload_low_cut = (
        volume_values[
            (n // 3) - 1
        ]
    )

    workload_high_cut = (
        volume_values[
            (2 * n // 3) - 1
        ]
    )

    richness_low_cut = (
        richness_values[
            (n // 3) - 1
        ]
    )

    richness_high_cut = (
        richness_values[
            (2 * n // 3) - 1
        ]
    )

    def tier(
        value,
        low_cut,
        high_cut,
    ):
        if value <= low_cut:
            return "low"

        if value <= high_cut:
            return "medium"

        return "high"

    for row in resolved_rows:
        volume = int(
            row["jan_jun_2025_created"]
        )

        species = int(
            row["active_species"]
        )

        row["workload_tier"] = tier(
            volume,
            workload_low_cut,
            workload_high_cut,
        )

        row["richness_tier"] = tier(
            species,
            richness_low_cut,
            richness_high_cut,
        )

    print(
        "\nDerived screening cut-points"
    )
    print(
        "============================"
    )
    print(
        f"Workload low <= "
        f"{workload_low_cut:,}"
    )
    print(
        f"Workload medium <= "
        f"{workload_high_cut:,}"
    )
    print(
        f"Workload high > "
        f"{workload_high_cut:,}"
    )

    print(
        f"Richness low <= "
        f"{richness_low_cut:,} species"
    )
    print(
        f"Richness medium <= "
        f"{richness_high_cut:,} species"
    )
    print(
        f"Richness high > "
        f"{richness_high_cut:,} species"
    )


def write_output(rows):
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows):
    print(
        "\nCANDIDATE FAMILY TAXONOMY SCREEN"
    )
    print(
        "================================"
    )



    print(
        f"{'Family':<18}"
        f"{'Species':>9}"
        f"{'Jan-Jun':>11}"
        f"{'Obs/Sp':>10}"
        f"{'Work':>9}"
        f"{'Rich':>9}"
        f"{'Ident':>9}"
    )

    print("-" * 75)







    for row in rows:
        print(
            f"{row['family']:<18}"
            f"{str(
                row['active_species']
            ):>9}"
            f"{str(
                row['jan_jun_2025_created']
            ):>11}"
            f"{str(
                row[
                    'observations_per_species'
                ]
            ):>10}"
            f"{str(
                row['workload_tier']
            ):>9}"
            f"{str(
                row['richness_tier']
            ):>9}"
            f"{str(
                row['identifiability']
            ):>9}"
        )









def main():
    if not TAXA_PATH.exists():
        raise FileNotFoundError(
            f"Missing taxa file: {TAXA_PATH}"
        )

    resolved = (
        resolve_candidate_families()
    )



    counts = count_descendants(
        resolved
    )

    monthly_counts = (
        fetch_monthly_counts(
            resolved
        )
    )




    rows = build_output_rows(
        resolved,
        counts,
        monthly_counts,
    )

    add_derived_metrics(
        rows
    )

    write_output(
        rows
    )




    print_summary(
        rows
    )

    print(
        "\nCandidate table written to:"
    )
    print(
        f"  {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()