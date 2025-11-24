import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Table
import datetime as dt

AIRTABLE_TOKEN = os.environ["AIRTABLE_TOKEN"]
AIRTABLE_BASE = os.environ["AIRTABLE_BASE"]
TABLE_NAME = os.environ["AIRTABLE_TABLE"]

table = Table(AIRTABLE_TOKEN, AIRTABLE_BASE, TABLE_NAME)

def get_existing_ids():
    ids = set()
    for page in table.iterate():
        for record in page:
            ext = record["fields"].get("External ID")
            if ext:
                ids.add(ext)
    return ids


# ====== ПРИМЕР ПАРСЕРА ДЛЯ ChatGPT Release Notes ======
def fetch_chatgpt():
    url = "https://help.openai.com/en/articles/6825453-chatgpt-release-notes"
    r = requests.get(url, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    # Примерная структура — позже можно уточнять
    for h2 in soup.find_all("h2"):
        date_text = h2.get_text(strip=True)
        try:
            date = dt.datetime.strptime(date_text, "%B %d, %Y").date()
        except:
            continue

        node = h2.find_next_sibling()
        while node and node.name != "h2":
            if node.name == "h3":
                title = node.get_text(strip=True)
                desc_nodes = []
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


def main():
    existing = get_existing_ids()

    all_data = []
    all_data.extend(fetch_chatgpt())

    for rec in all_data:
        if rec["External ID"] not in existing:
            table.create(rec)


if __name__ == "__main__":
    main()
