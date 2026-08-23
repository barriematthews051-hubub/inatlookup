import argparse
import csv
import os
import re
import time

import requests


DATA_DIR = "research/data"

TAXA_API_URL = (
    "https://api.inaturalist.org/"
    "v1/taxa"
)

TAXA_PER_BATCH = 100
REQUEST_DELAY = 1.0


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Enrich a taxon pilot sample "
            "with Community Taxon name and rank."
        )
    )

    parser.add_argument(
        "--taxon-id",
        type=int,
        required=True,
        help="iNaturalist taxon ID.",
    )

    parser.add_argument(
        "--taxon-name",
        required=True,
        help="Taxon name, e.g. Syrphidae.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=500,
        help="Pilot sample size. Default: 500.",
    )

    return parser.parse_args()


def slugify(text):
    text = text.strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    )

    return text.strip("_")


def load_rows(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(
            csv.DictReader(f)
        )


def api_get(params):
    response = requests.get(
        TAXA_API_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    time.sleep(
        REQUEST_DELAY
    )

    return data


def fetch_taxa(taxon_ids):
    taxa = {}

    batches = [
        taxon_ids[
            i:i + TAXA_PER_BATCH
        ]
        for i in range(
            0,
            len(taxon_ids),
            TAXA_PER_BATCH
        )
    ]

    print(
        "Unique community taxa:",
        len(taxon_ids)
    )

    print(
        "Taxon batches:",
        len(batches)
    )

    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        ids_text = ",".join(
            str(x)
            for x in batch
        )

        print(
            f"Fetching taxon batch "
            f"{batch_number}/"
            f"{len(batches)}"
        )

        data = api_get(
            {
                "id": ids_text,
                "per_page": 200,
            }
        )

        print(
            "  Returned:",
            len(data["results"])
        )

        for taxon in data["results"]:
            taxa[
                str(taxon["id"])
            ] = taxon

    return taxa


def main():
    args = parse_args()

    slug = slugify(
        args.taxon_name
    )

    input_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}.csv"
    )

    output_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"enriched.csv"
    )

    if not os.path.exists(
        input_file
    ):
        raise RuntimeError(
            f"Pilot file not found: "
            f"{input_file}"
        )

    rows = load_rows(
        input_file
    )

    print(
        "Taxon:",
        args.taxon_name
    )

    print(
        "Taxon ID:",
        args.taxon_id
    )

    print(
        "Observations:",
        len(rows)
    )

    community_taxon_ids = sorted(
        {
            int(
                row["community_taxon_id"]
            )
            for row in rows
            if row["community_taxon_id"]
        }
    )

    taxa = fetch_taxa(
        community_taxon_ids
    )

    no_community_taxon = 0
    unresolved_taxon_ids = 0

    enriched_rows = []

    for row in rows:

        community_taxon_id = (
            row["community_taxon_id"]
        )

        if not community_taxon_id:

            no_community_taxon += 1

            row[
                "community_taxon_name"
            ] = ""

            row[
                "community_taxon_rank"
            ] = ""

        else:

            taxon = taxa.get(
                community_taxon_id
            )

            if taxon is None:

                unresolved_taxon_ids += 1

                row[
                    "community_taxon_name"
                ] = ""

                row[
                    "community_taxon_rank"
                ] = ""

            else:

                row[
                    "community_taxon_name"
                ] = taxon.get(
                    "name",
                    ""
                )

                row[
                    "community_taxon_rank"
                ] = taxon.get(
                    "rank",
                    ""
                )

        enriched_rows.append(
            row
        )

    fieldnames = list(
        enriched_rows[0].keys()
    )

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(
            enriched_rows
        )

    print()
    print(
        "Enrichment complete"
    )

    print(
        "Rows written:",
        len(enriched_rows)
    )

    print(
        "No community taxon:",
        no_community_taxon
    )

    print(
        "Unresolved taxon IDs:",
        unresolved_taxon_ids
    )

    print(
        "Output:",
        output_file
    )


if __name__ == "__main__":
    main()