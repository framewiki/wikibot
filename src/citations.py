import logging
import re
import requests
from pathlib import Path

import bs4
import markdown

logger = logging.getLogger(__name__)


def check_citations(page: Path) -> None:
    # Read markdown, strip frontmatter, convert to html for parsing.
    contents = page.read_text()
    contents = re.sub(r"(?s)^---\n.*?\n---\n", "", contents, count=1)
    contents = markdown.markdown(contents, extensions=["footnotes"])

    # Loop over every footnote.
    doc = bs4.BeautifulSoup(contents, features="html.parser")
    footnotes = doc.find("div", class_="footnote")
    if not footnotes:
        logger.info(f"No footnotes found in {page.name}")
        return
    for note in footnotes.find_all("li"):
        links = note.find_all(
            "a", href=lambda href: href and href.startswith(("http://", "https://"))
        )

        # Make sure there is at least one link.
        if len(links) == 0:
            logger.warning(f"Footnote in {page.name} has no links. Skipping.")
            continue

        url = links[0].get("href")
        logger.debug(f"Checking citation {url}")

        # Check if there is an archive link.
        archive_link_present = False
        for link in links:
            if link.get("href").startswith("https://web.archive.org"):
                archive_link_present = True  # If there is an archive link, the footnote is fine.
                logger.debug(f"Found archive link in citation {url}")
                break
        if archive_link_present:
            continue

        logger.debug(f"No archive link found in citation {url}. Attempting fix.")

        # Check if the link is broken. If not, create a new archive.
        if requests.get(url).ok:
            archive_url = requests.get(f"https://web.archive.org/save/{url}", timeout=600).url
            logger.info(f"Created new archive link for {url}")

        # If the link is broken, check if there is an existing archive.
        else:
            archive = requests.get(f"https://archive.org/wayback/available?url={url}")
            snapshots = archive.json()["archived_snapshots"]
            closest = snapshots.get("closest")
            if closest and closest["available"] is True:
                archive_url = closest["url"]
                logger.info(f"Found existing archive link for {url}")
            else:
                logger.warning(
                    f"Footnote in {page.name} contains broken link to {url}. No archived copy is available."
                )
                continue

        # Put archive_url on the page.
        with page.open("r") as file:
            lines = file.readlines()
        modified_lines = []
        for line in lines:
            if url in line:
                line = f"{line.rstrip()} [Archived]({archive_url}) \n"
            modified_lines.append(line)
        with page.open("w") as file:
            file.writelines(modified_lines)
