import requests

names = [
    "Asilidae",
    "Geometridae",
    "Nymphalidae",
    "Staphylinidae",
    "Asteraceae",
]

url = "https://api.inaturalist.org/v1/taxa"

for name in names:
    response = requests.get(
        url,
        params={
            "q": name,
            "rank": "family",
            "per_page": 10,
        },
        timeout=60,
    )

    response.raise_for_status()
    data = response.json()

    matches = [
        taxon
        for taxon in data["results"]
        if taxon["name"] == name
    ]

    print()
    print(name)

    if not matches:
        print("  Exact match not found")
        continue

    for taxon in matches:
        print("  ID:", taxon["id"])
        print("  Name:", taxon["name"])
        print("  Rank:", taxon["rank"])
        print(
            "  Common name:",
            taxon.get(
                "preferred_common_name"
            )
        )