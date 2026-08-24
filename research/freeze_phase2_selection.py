import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    REPO_ROOT
    / "research"
    / "data"
)

INPUT_PATH = (
    DATA_DIR
    / "candidate_family_screen_stage3.csv"
)

OUTPUT_PATH = (
    DATA_DIR
    / "candidate_family_phase2_selection.csv"
)


SELECTIONS = {
    "Formicidae": {
        "common_name": "ants",
        "phase2_selected": 1,
        "selection_role":
            "Medium workload, high richness insect contrast; "
            "complements existing Diptera and Staphylinidae.",
        "reserve_rank": "",
    },
    "Libellulidae": {
        "common_name": "skimmers and perchers",
        "phase2_selected": 1,
        "selection_role":
            "Conspicuous, visually tractable insect contrast "
            "with Formicidae and difficult existing insect families.",
        "reserve_rank": "",
    },
    "Orchidaceae": {
        "common_name": "orchid family",
        "phase2_selected": 1,
        "selection_role":
            "High-workload, high-richness, relatively visually "
            "tractable plant; controlled contrast with Poaceae.",
        "reserve_rank": "",
    },
    "Poaceae": {
        "common_name": "grass family",
        "phase2_selected": 1,
        "selection_role":
            "High-workload, high-richness, photographically "
            "difficult plant; controlled contrast with Orchidaceae.",
        "reserve_rank": "",
    },
    "Russulaceae": {
        "common_name": "russula and milkcap family",
        "phase2_selected": 1,
        "selection_role":
            "Low-workload, medium-richness, specialist-dependent "
            "macrofungus with low owner species starting rate.",
        "reserve_rank": "",
    },
    "Parmeliaceae": {
        "common_name": "shield lichen family",
        "phase2_selected": 1,
        "selection_role":
            "Lichen identification community distinct from "
            "macrofungi; medium workload and medium richness.",
        "reserve_rank": "",
    },
    "Salticidae": {
        "common_name": "jumping spiders",
        "phase2_selected": 1,
        "selection_role":
            "Popular, visually distinctive, high-richness spider; "
            "controlled contrast with Lycosidae.",
        "reserve_rank": "",
    },
    "Lycosidae": {
        "common_name": "wolf spiders",
        "phase2_selected": 1,
        "selection_role":
            "Lower expected visual identifiability and coarser "
            "owner starting ranks; contrast with Salticidae.",
        "reserve_rank": "",
    },
    "Anatidae": {
        "common_name": "ducks, geese and swans",
        "phase2_selected": 1,
        "selection_role":
            "Very high observation workload but low species "
            "richness; strong vertebrate benchmark.",
        "reserve_rank": "",
    },
    "Colubridae": {
        "common_name": "colubrid snakes",
        "phase2_selected": 1,
        "selection_role":
            "Medium workload and richness vertebrate contrast "
            "with the low-richness, high-volume Anatidae.",
        "reserve_rank": "",
    },
    "Limacidae": {
        "common_name": "keeled slugs",
        "phase2_selected": 1,
        "selection_role":
            "Low-workload, low-richness, photographically "
            "difficult terrestrial invertebrate.",
        "reserve_rank": "",
    },
    "Asteriidae": {
        "common_name": "common sea stars",
        "phase2_selected": 1,
        "selection_role":
            "Low-workload, low-richness marine invertebrate "
            "with a distinct observer and identifier community.",
        "reserve_rank": "",
    },

    # Reserves
    "Apidae": {
        "common_name": "bees",
        "phase2_selected": 0,
        "selection_role":
            "Reserve insect family.",
        "reserve_rank": 1,
    },
    "Cyperaceae": {
        "common_name": "sedge family",
        "phase2_selected": 0,
        "selection_role":
            "Reserve difficult vascular plant family.",
        "reserve_rank": 2,
    },
    "Boletaceae": {
        "common_name": "bolete family",
        "phase2_selected": 0,
        "selection_role":
            "Reserve macrofungus family.",
        "reserve_rank": 3,
    },
    "Araneidae": {
        "common_name": "orb-weaver spiders",
        "phase2_selected": 0,
        "selection_role":
            "Reserve spider family.",
        "reserve_rank": 4,
    },
    "Accipitridae": {
        "common_name": "hawks, eagles and allies",
        "phase2_selected": 0,
        "selection_role":
            "Reserve vertebrate family.",
        "reserve_rank": 5,
    },
    "Muricidae": {
        "common_name": "murex and rock snails",
        "phase2_selected": 0,
        "selection_role":
            "Reserve other-invertebrate family.",
        "reserve_rank": 6,
    },
}


def load_rows():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing Stage-3 screen: "
            f"{INPUT_PATH}"
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    if len(rows) != 36:
        raise ValueError(
            f"Expected 36 candidate families, "
            f"found {len(rows)}"
        )

    return rows


def freeze_selection(rows):
    output = []

    selected_count = 0
    reserve_count = 0

    for row in rows:
        family = row["family"]

        decision = SELECTIONS.get(
            family
        )

        frozen = dict(row)

        if decision is None:
            frozen["common_name"] = ""
            frozen["phase2_selected"] = 0
            frozen["selection_role"] = (
                "Not selected for Phase 2."
            )
            frozen["reserve_rank"] = ""

        else:
            frozen["common_name"] = (
                decision["common_name"]
            )
            frozen["phase2_selected"] = (
                decision[
                    "phase2_selected"
                ]
            )
            frozen["selection_role"] = (
                decision[
                    "selection_role"
                ]
            )
            frozen["reserve_rank"] = (
                decision[
                    "reserve_rank"
                ]
            )

            if (
                decision[
                    "phase2_selected"
                ]
                == 1
            ):
                selected_count += 1

            if (
                decision[
                    "reserve_rank"
                ]
                != ""
            ):
                reserve_count += 1

        output.append(
            frozen
        )

    if selected_count != 12:
        raise ValueError(
            f"Expected 12 selected families, "
            f"found {selected_count}"
        )

    if reserve_count != 6:
        raise ValueError(
            f"Expected 6 reserve families, "
            f"found {reserve_count}"
        )

    return output


def write_output(rows):
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


def print_selection(rows):
    selected = [
        row
        for row in rows
        if row[
            "phase2_selected"
        ]
        == 1
    ]

    reserves = sorted(
        [
            row
            for row in rows
            if row[
                "reserve_rank"
            ]
            != ""
        ],
        key=lambda row: int(
            row["reserve_rank"]
        ),
    )

    print(
        "\nPHASE 2 SELECTION FROZEN"
    )
    print(
        "========================"
    )

    print(
        "\nSelected new families:"
    )

    for row in selected:
        common = row[
            "common_name"
        ]

        print(
            f"  {row['family']}"
            f" ({common})"
        )

    print(
        f"\nSelected count: "
        f"{len(selected)}"
    )

    print(
        "\nReserve families:"
    )

    for row in reserves:
        print(
            f"  {row['reserve_rank']}. "
            f"{row['family']} "
            f"({row['common_name']})"
        )

    print(
        "\nSelection was frozen using only:"
    )
    print(
        "  taxonomy and richness"
    )
    print(
        "  Jan-Jun 2025 observation workload"
    )
    print(
        "  predefined identifiability"
    )
    print(
        "  first owner identification rank"
    )
    print(
        "  photo-count structure"
    )

    print(
        "\nNo Phase-2 external-ID or "
        "community-taxon outcomes were "
        "used in selection."
    )


def main():
    rows = load_rows()

    frozen = freeze_selection(
        rows
    )

    write_output(
        frozen
    )

    print_selection(
        frozen
    )

    print(
        "\nFrozen selection written to:"
    )
    print(
        f"  {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()