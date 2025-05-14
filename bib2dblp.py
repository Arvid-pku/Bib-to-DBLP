import bibtexparser
import requests
import time
import logging
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import homogenize_latex_encoding

# Configure logging
logging.basicConfig(filename="dblp_update.log", level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

def search_dblp_entry(title, key, max_retries=5, delay=2):
    """Search DBLP for a given paper title and return the BibTeX entry."""
    params = {"q": title, "format": "json"}
    attempt = 0
    while attempt < max_retries:
        try:
            resp = requests.get("https://dblp.org/search/publ/api", params=params)
            if resp.status_code != 200:
                msg = f"Attempt {attempt+1}: Failed to search DBLP for key: {key}, title: {title}"
                print(msg)
                logging.warning(msg)
                attempt += 1
                time.sleep(delay)
                continue

            data = resp.json()
            hits = data.get("result", {}).get("hits", {}).get("hit", [])
            if not hits:
                msg = f"No results found on DBLP for key: {key}, title: {title}"
                print(msg)
                logging.info(msg)
                return None

            dblp_url = hits[0]["info"].get("url")
            if dblp_url:
                bibtex_url = dblp_url + ".bib"
                bibtex_resp = requests.get(bibtex_url)
                if bibtex_resp.status_code == 200:
                    return bibtex_resp.text
        except Exception as e:
            msg = f"Attempt {attempt+1}: Error occurred while searching for key: {key}, title: {title} - {e}"
            print(msg)
            logging.error(msg)

        attempt += 1
        time.sleep(delay)

    msg = f"All {max_retries} attempts failed for key: {key}, title: {title}"
    print(msg)
    logging.error(msg)
    return None


def update_bib_file(input_file, output_file):
    with open(input_file, encoding="utf-8") as bibtex_file:
        parser = BibTexParser()
        parser.customization = homogenize_latex_encoding
        bib_database = bibtexparser.load(bibtex_file, parser=parser)

    updated_entries = []
    failed_keys = []

    for entry in bib_database.entries:
        title = entry.get("title", "").replace("{", "").replace("}", "")
        original_key = entry.get("ID")
        if not title or not original_key:
            continue
        msg = f"Searching DBLP for key: {original_key}, title: {title}"
        print(msg)
        logging.info(msg)
        new_bibtex = search_dblp_entry(title, original_key)
        if new_bibtex:
            new_db = bibtexparser.loads(new_bibtex)
            if new_db.entries:
                new_entry = new_db.entries[0]
                new_entry["ID"] = original_key  # preserve original citation key
                updated_entries.append(new_entry)
            else:
                msg = f"No parsed BibTeX found for key: {original_key}, title: {title}"
                print(msg)
                logging.warning(msg)
                updated_entries.append(entry)
                failed_keys.append(original_key)
        else:
            msg = f"Keeping original entry for key: {original_key}, title: {title}"
            print(msg)
            logging.info(msg)
            updated_entries.append(entry)
            failed_keys.append(original_key)
        time.sleep(1)  # Add delay between entries

    new_bib_database = bibtexparser.bibdatabase.BibDatabase()
    new_bib_database.entries = updated_entries

    with open(output_file, "w", encoding="utf-8") as bibfile:
        bibtexparser.dump(new_bib_database, bibfile)

    if failed_keys:
        with open("failed_keys.txt", "w", encoding="utf-8") as f:
            for key in failed_keys:
                f.write(key + "\n")


if __name__ == "__main__":
    input_bib = "custom_old.bib"   # 替换为你的原始 bib 文件
    output_bib = "custom_updated.bib"  # 输出新文件
    update_bib_file(input_bib, output_bib)
    print("更新完成！")
    logging.info("BibTeX 更新完成")
