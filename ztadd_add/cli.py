#!/usr/bin/env python3
"""
Search Crossref by title, fetch BibTeX, convert it to Zotero item JSON,
check for duplicates, and create the item using the pyzotero CLI.

Usage:
    ztadd "Paper title" [--collection COLLECTION_KEY]

The pyzotero CLI must already be configured with your Zotero credentials.
"""

import argparse
import copy
import json
import os
import subprocess
import sysconfig
import tempfile
from pathlib import Path

import requests
import bibtexparser
from bibtexparser.bparser import BibTexParser


ITEM_TYPE_MAP = {
    "article": "journalArticle",
    "inproceedings": "conferencePaper",
    "conference": "conferencePaper",
    "book": "book",
    "proceedings": "book",
    "incollection": "bookSection",
    "inbook": "bookSection",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "techreport": "report",
    "misc": "document",
    "online": "webpage",
    "unpublished": "manuscript",
}

COMMON_FIELDS = {
    "title": "title",
    "publisher": "publisher",
    "volume": "volume",
    "number": "issue",
    "pages": "pages",
    "doi": "DOI",
    "url": "url",
    "abstract": "abstractNote",
    "isbn": "ISBN",
    "issn": "ISSN",
    "language": "language",
}

TYPE_FIELDS = {
    "journalArticle": {"journal": "publicationTitle"},
    "conferencePaper": {"booktitle": "proceedingsTitle"},
    "bookSection": {"booktitle": "bookTitle"},
    "thesis": {"school": "university"},
    "report": {"institution": "institution"},
}

_TEMPLATE_CACHE = {}


def get_pyzotero_executable():
    """Find pyzotero in the same Python environment as this CLI."""
    scripts_dir = Path(sysconfig.get_path("scripts"))
    candidates = ["pyzotero.exe", "pyzotero"] if os.name == "nt" else ["pyzotero"]

    for name in candidates:
        executable = scripts_dir / name
        if executable.is_file():
            return str(executable)

    raise SystemExit(
        "Could not find the pyzotero executable in this Python environment. "
        "Reinstall the package or check that pyzotero is installed."
    )


def get_item_template(item_type):
    """Fetch Zotero's canonical template for an item type."""
    if item_type in _TEMPLATE_CACHE:
        return copy.deepcopy(_TEMPLATE_CACHE[item_type])

    response = requests.get(
        "https://api.zotero.org/items/new",
        params={"itemType": item_type},
        timeout=20,
    )
    response.raise_for_status()
    template = response.json()
    _TEMPLATE_CACHE[item_type] = template
    return copy.deepcopy(template)


def parse_authors(value, creator_type="author"):
    """Convert BibTeX author/editor names into Zotero creator dictionaries."""
    creators = []
    for raw in value.split(" and "):
        raw = raw.strip().strip("{}")
        if not raw:
            continue

        if "," in raw:
            last, first = (part.strip() for part in raw.split(",", 1))
        else:
            parts = raw.split()
            if len(parts) == 1:
                last, first = parts[0], ""
            else:
                first, last = " ".join(parts[:-1]), parts[-1]

        creators.append({
            "creatorType": creator_type,
            "firstName": first,
            "lastName": last,
        })
    return creators


def build_zotero_item(entry):
    entry_type = (entry.get("ENTRYTYPE") or "misc").lower()
    item_type = ITEM_TYPE_MAP.get(entry_type, "document")
    item = get_item_template(item_type)

    mapping = dict(COMMON_FIELDS)
    mapping.update(TYPE_FIELDS.get(item_type, {}))

    for bib_key, zotero_key in mapping.items():
        if entry.get(bib_key) and zotero_key in item:
            value = entry[bib_key]
            if bib_key == "pages":
                value = value.replace("--", "-").replace("–", "-")
            item[zotero_key] = value

    if entry.get("journal") and "publicationTitle" in item:
        item["publicationTitle"] = entry["journal"]

    if entry.get("booktitle"):
        for key in ("proceedingsTitle", "bookTitle"):
            if key in item:
                item[key] = entry["booktitle"]
                break

    if entry.get("eventtitle") and "conferenceName" in item:
        item["conferenceName"] = entry["eventtitle"]

    creators = []
    if entry.get("author"):
        creators.extend(parse_authors(entry["author"]))
    if entry.get("editor"):
        creators.extend(parse_authors(entry["editor"], "editor"))
    item["creators"] = creators

    if entry.get("date"):
        item["date"] = entry["date"]
    elif entry.get("year"):
        item["date"] = entry["year"]

    return item


def parse_args():
    parser = argparse.ArgumentParser(
        prog="ztadd",
        description="Find a paper through Crossref and add it to Zotero.",
    )
    parser.add_argument("title", nargs="*", help="Paper title to search for")
    parser.add_argument(
        "--collection",
        help="Zotero collection key (not the collection's display name)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    title = " ".join(args.title).strip() or input("Paper title: ").strip()
    if not title:
        raise SystemExit("A paper title is required.")

    print("Searching Crossref...")
    search_response = requests.get(
        "https://api.crossref.org/works",
        params={"query.bibliographic": title, "rows": 1},
        timeout=20,
    )
    search_response.raise_for_status()
    results = search_response.json()["message"]["items"]

    if not results:
        raise SystemExit("No matching paper found.")

    paper = results[0]
    matched_title = (paper.get("title") or ["Unknown title"])[0]
    doi = paper.get("DOI")

    print("Match:", matched_title)
    print("DOI:", doi or "No DOI found")
    if not doi:
        raise SystemExit("No DOI found; cannot fetch BibTeX.")

    bibtex_response = requests.get(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/x-bibtex"},
        timeout=20,
    )
    bibtex_response.raise_for_status()

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    database = bibtexparser.loads(bibtex_response.text, parser=parser)

    if not database.entries:
        raise SystemExit("Could not parse the BibTeX response.")

    zotero_item = build_zotero_item(database.entries[0])
    search_title = zotero_item.get("title", "")
    search_doi = zotero_item.get("DOI", "")

    pyzotero = get_pyzotero_executable()

    print("\nChecking if item already exists in Zotero...")
    search_cmd = [pyzotero, "search", "-q", search_title, "--json"]
    if args.collection:
        search_cmd.extend(["--collection", args.collection])

    search_result = subprocess.run(
        search_cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    existing_item = None
    if search_result.returncode == 0 and search_result.stdout.strip():
        try:
            found_items = json.loads(search_result.stdout)
            if isinstance(found_items, dict) and "items" in found_items:
                found_items = found_items["items"]

            if isinstance(found_items, list):
                for found in found_items:
                    found_title = found.get("title", "")
                    found_doi = found.get("DOI", "")
                    if (
                        found_title.casefold() == search_title.casefold()
                        or (search_doi and found_doi == search_doi)
                    ):
                        existing_item = found
                        break
        except (json.JSONDecodeError, AttributeError, TypeError):
            print("Warning: Could not parse Zotero search results.")

    if existing_item:
        print("\nItem may already exist in Zotero:")
        print("Title:", existing_item.get("title", "Unknown"))
        print("Key:", existing_item.get("key", existing_item.get("itemKey", "Unknown")))
        choice = input("Add it anyway as a duplicate? (y/N): ").strip().lower()
        if choice not in ("y", "yes"):
            print("Aborted. Item was not added.")
            return
    elif search_result.returncode != 0:
        print("Warning: Zotero duplicate search failed.")
        if search_result.stderr.strip():
            print(search_result.stderr.strip())
        choice = input("Continue with item creation anyway? (y/N): ").strip().lower()
        if choice not in ("y", "yes"):
            print("Aborted. Item was not added.")
            return
    else:
        print("Item not found in Zotero. Proceeding.")

    creators = zotero_item.get("creators", [])
    author_names = [
        f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()
        for creator in creators
    ]

    print("\n" + "=" * 50)
    print("ITEM PREVIEW")
    print("=" * 50)
    print("Type:       ", zotero_item.get("itemType", "Unknown"))
    print("Title:      ", zotero_item.get("title", "Unknown"))
    print("Authors:    ", ", ".join(author_names) if author_names else "Unknown")
    print("Date/Year:  ", zotero_item.get("date", "Unknown"))
    print("DOI:        ", zotero_item.get("DOI", "None"))
    if args.collection:
        print("Collection: ", args.collection)
    print("=" * 50)

    confirm = input("\nAdd this item to Zotero? (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted. Item was not added to Zotero.")
        return

    with tempfile.TemporaryDirectory(prefix="ztadd-") as temp_dir:
        json_path = Path(temp_dir) / "items.json"
        json_path.write_text(
            json.dumps([zotero_item], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        create_cmd = [pyzotero, "createitem", str(json_path)]
        if args.collection:
            create_cmd.extend(["--collection", args.collection])

        print("\nCreating Zotero item...")
        result = subprocess.run(create_cmd, check=False)

    if result.returncode != 0:
        raise SystemExit(f"pyzotero createitem failed (exit {result.returncode}).")

    print("\nSuccessfully added to Zotero!")


if __name__ == "__main__":
    main()
