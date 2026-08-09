# iNatLookup

**Fast reverse lookup for iNaturalist photos.**

iNatLookup takes an iNaturalist photo ID or photo URL and finds the parent observation using a locally stored binary index built from the iNaturalist Open Data photos table.

It is designed for situations where you have an iNaturalist photo ID but need to determine which observation it belongs to.

## What it does

Given a photo ID such as:

```text
455606536
```

or an iNaturalist photo URL such as:

```text
https://static.inaturalist.org/photos/455606536/original.jpeg
```

iNatLookup searches the local index and returns the observation UUID.

For a known photo, it can then query the iNaturalist API to display the observation ID and observation URL.

The binary index uses a header containing format information and sorted fixed-size records, allowing photo IDs to be located using binary search without loading the entire index into memory.

## Current version

**iNatLookup 0.3.0**

Index format: **v1**

## Requirements

- Python 3
- A locally available iNatLookup binary index
- Internet access is required only when using the API lookup after a photo has been found in the local index.

The production index is built from the iNaturalist Open Data photos table.

The production index used during development contains:

```text
475,206,174 records
```

The production index is **not included in this GitHub repository**.

## Single-photo lookup

### Photo ID

```cmd
python inatlookup.py 455606536
```

### Photo URL

```cmd
python inatlookup.py https://static.inaturalist.org/photos/455606536/original.jpeg
```

The program extracts the photo ID, searches the local index and, when found, queries the iNaturalist API for the observation.

Typical output includes:

```text
Photo ID: 455606536
Observation UUID: 9bcb94d0-cf6f-4ab0-9c5b-7301685acdb9
Observation ID : 254368720
Observation URL: https://www.inaturalist.org/observations/254368720
```

If the photo is not present in the index:

```text
Photo not found in index.
```

## Batch lookup

A text file containing photo IDs and/or iNaturalist photo URLs can be supplied as the input.

For example:

```cmd
python inatlookup.py photos.txt
```

Blank lines are ignored.

Each input record is classified as:

- `found`
- `not found`
- `invalid input`

Duplicate photo IDs are cached, so the binary index is searched only once for each unique photo ID.

The program reports statistics including:

```text
Input records
Valid inputs
Invalid input
Unique photos
Index lookups
Found in index
Not found
Unique observations
```

Results are written to:

```text
inatlookup_results.csv
```

A different output file can be specified with:

```cmd
python inatlookup.py photos.txt --output results.csv
```

or:

```cmd
python inatlookup.py photos.txt -o results.csv
```

The CSV contains:

```text
input
photo_id
observation_uuid
status
```

## Progress reporting

Batch processing reports progress every 10,000 input records.

For example:

```text
Processing: 10,000 records...
Processing: 20,000 records...
```

Duplicate inputs do not cause additional binary index lookups.

## Index information

Use:

```cmd
python inatlookup.py --info
```

This displays information such as:

```text
iNatLookup 0.3.0
Index format v1
Records : 475,206,174
```

## Version information

Use:

```cmd
python inatlookup.py --version
```

to display the program version.

## Selecting an index

By default, iNatLookup looks for:

```text
data\inatlookup.bin
```

A different index can be supplied with:

```cmd
python inatlookup.py --index path\to\inatlookup.bin 455606536
```

For example, the repository's small test index can be used with:

```cmd
python inatlookup.py --index tests\test_index.bin 455606536
```

## Index format

The current index format is version 1.

Each index contains:

```text
128-byte header
24-byte fixed-size records
```

Each record contains:

```text
8-byte photo ID
16-byte observation UUID
```

Records are sorted by photo ID.

The lookup process uses binary search, making it practical to search a very large index without loading all records into memory.

The header records information including:

- format version
- record count
- record size
- header size
- index build time

The reader validates the index format before performing lookups.

## Testing

The repository contains an automated test suite.

Run:

```cmd
python tests\test_lookup.py
```

The tests cover:

- known photo lookup
- missing photo lookup
- photo ID parsing
- photo URL parsing
- invalid input
- batch lookup
- CSV output
- duplicate lookup caching
- context-manager support
- invalid index format version
- invalid record size
- invalid header size

The tests use a small five-record index:

```text
tests\test_index.bin
```

This test index is only a small fixture and is **not** the production iNaturalist index.

It can be regenerated with:

```cmd
python tests\create_test_index.py
```

This means the automated test suite does not require the large production index.

## Project structure

The main project files are:

```text
inatlookup/
│
├── inatlookup.py
├── lookup.py
├── header.py
├── constants.py
├── version.py
│
├── tests/
│   ├── create_test_index.py
│   ├── test_index.bin
│   └── test_lookup.py
│
└── data/
    └── inatlookup.bin       # local production index, not included
```

### `inatlookup.py`

Command-line interface, photo ID/URL parsing, single lookup, batch lookup and CSV output.

### `lookup.py`

Reads the binary index and performs binary-search lookups.

### `header.py`

Creates and validates the binary index header.

### `constants.py`

Defines the current index format constants.

### `version.py`

Contains the program version.

### `tests/`

Contains the automated tests and the small reproducible test index.

## Why this exists

The iNaturalist photos data contains the relationship between photo IDs and observations, but a photo URL itself does not directly provide the observation ID.

For example:

```text
photo ID → observation UUID → observation
```

iNatLookup provides a fast local reverse lookup for that relationship.

Instead of repeatedly searching the large iNaturalist dataset, a sorted local binary index can be searched directly using the photo ID.

## Development status

iNatLookup is currently under active development.

Version 0.3 adds:

- command-line lookup
- index information
- batch photo lookup
- CSV output
- duplicate lookup caching
- progress reporting
- structured batch results
- index format validation
- context-manager support
- a lightweight automated test index

The project is primarily intended as a practical tool for working with large numbers of iNaturalist photo records.