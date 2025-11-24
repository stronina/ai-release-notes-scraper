import datetime as dt
import logging
import os
from typing import Iterable, List

import requests
from bs4 import BeautifulSoup
from pyairtable import ApiError, Table

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_airtable_table() -> Table:
    missing = [name for name in ["AIRTABLE_TOKEN", "AIRTABLE_BASE", "AIRTABLE_TABLE"] if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return Table(os.environ["AIRTABLE_TOKEN"], os.environ["AIRTABLE_BASE"], os.environ["AIRTABLE_TABLE"])


def get_existing_ids(table: Table) -> set[str]:
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


def create_records(table: Table, records: Iterable[dict]) -> None:
    for rec in records:
        try:
            table.create(rec)
        except ApiError as exc:
            logger.error("Failed to create Airtable record %s: %s", rec.get("External ID"), exc)


def main() -> None:
    table = get_airtable_table()

    existing = get_existing_ids(table)

    all_data = []
    all_data.extend(fetch_chatgpt())

    new_records = [rec for rec in all_data if rec["External ID"] not in existing]

    if not new_records:
        logger.info("No new records found")
        return

    create_records(table, new_records)


if __name__ == "__main__":
    main()
