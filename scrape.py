import argparse
import csv
import datetime as dt
import logging
import os
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from pyairtable import ApiError, Table

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_airtable_table() -> "Table":
    from pyairtable import Table

    missing = [name for name in ["AIRTABLE_TOKEN", "AIRTABLE_BASE", "AIRTABLE_TABLE"] if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Table(os.environ["AIRTABLE_TOKEN"], os.environ["AIRTABLE_BASE"], os.environ["AIRTABLE_TABLE"])


def get_existing_ids(table: "Table") -> set[str]:
    ids: set[str] = set()
    for page in table.iterate():
        for record in page:
            ext = record["fields"].get("External ID")
            if ext:
                ids.add(ext)
    return ids


# ====== ПРИМЕР ПАРСЕРА ДЛЯ ChatGPT Release Notes ======
def fetch_chatgpt() -> List[dict]:
    url = "https://help.openai.com/en/articles/6825453-chatgpt-release-notes"
    try:
        r = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "ai-release-notes-scraper/1.0"},
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to download ChatGPT release notes: %s", exc)
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    results: List[dict] = []

    # Примерная структура — позже можно уточнять
    for h2 in soup.find_all("h2"):
        date_text = h2.get_text(strip=True)
        try:
            date = dt.datetime.strptime(date_text, "%B %d, %Y").date()
        except ValueError:
            continue

        node = h2.find_next_sibling()
        while node and node.name != "h2":
            if node.name == "h3":
                title = node.get_text(strip=True)
                desc_nodes: List[str] = []
                nxt = node.find_next_sibling()
                while nxt and nxt.name not in ["h3", "h2"]:
                    desc_nodes.append(nxt.get_text(" ", strip=True))
                    nxt = nxt.find_next_sibling()
                desc = " ".join(desc_nodes).strip()

                results.append({
                    "Product": "ChatGPT",
                    "Feature name": title,
                    "Description": desc,
                    "Release date": date.isoformat(),
                    "Source URL": url,
                    "Source page": "ChatGPT Release Notes",
                    "External ID": f"chatgpt-{date.isoformat()}-{title}",
                })
            node = node.find_next_sibling()

    return results


FETCHERS: Dict[str, Callable[[], List[dict]]] = {
    "chatgpt": fetch_chatgpt,
}


def create_records(table: "Table", records: Iterable[dict]) -> None:
    from pyairtable import ApiError

    for rec in records:
        try:
            table.create(rec)
        except ApiError as exc:
            logger.error("Failed to create Airtable record %s: %s", rec.get("External ID"), exc)


def write_csv(path: str, records: Iterable[dict]) -> None:
    fieldnames = [
        "Product",
        "Feature name",
        "Description",
        "Release date",
        "Source URL",
        "Source page",
        "External ID",
    ]

    records_list = list(records)

    with open(path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in records_list:
            writer.writerow(row)
    logger.info("Saved %s records to %s", len(records_list), path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect release notes and push to Airtable/CSV")
    parser.add_argument(
        "--sources",
        help="Comma-separated list of sources to fetch (default: all)",
        default="",
    )
    parser.add_argument("--csv", dest="csv_path", help="Optional CSV output path")
    parser.add_argument(
        "--skip-airtable",
        action="store_true",
        help="Do not write records to Airtable (useful for local runs)",
    )
    return parser.parse_args()


def resolve_sources(selection: str) -> Dict[str, Callable[[], List[dict]]]:
    if not selection:
        return FETCHERS

    chosen = [name.strip().lower() for name in selection.split(",") if name.strip()]
    missing = [name for name in chosen if name not in FETCHERS]
    if missing:
        raise ValueError(f"Unknown sources requested: {', '.join(missing)}")

    return {name: FETCHERS[name] for name in chosen}


def main() -> None:
    args = parse_args()
    fetchers = resolve_sources(args.sources)

    airtable_table = None
    existing: set[str] = set()

    if not args.skip_airtable:
        try:
            airtable_table = get_airtable_table()
            existing = get_existing_ids(airtable_table)
        except RuntimeError as exc:
            logger.warning("Airtable is not configured: %s. Skipping Airtable upload.", exc)
            args.skip_airtable = True

    all_data: List[dict] = []
    for name, fetch in fetchers.items():
        logger.info("Fetching %s release notes", name)
        all_data.extend(fetch())

    new_records = [rec for rec in all_data if rec["External ID"] not in existing]

    if not new_records:
        logger.info("No new records found")
    else:
        logger.info("Collected %s new records", len(new_records))

    if args.csv_path:
        write_csv(args.csv_path, new_records or all_data)

    if args.skip_airtable:
        return

    if not new_records:
        return

    create_records(airtable_table, new_records)


if __name__ == "__main__":
    main()
