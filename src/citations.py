import logging
import re
import requests
import threading
import time
from pathlib import Path

import bs4
import markdown

logger = logging.getLogger(__name__)

rate_limit_lock = threading.Lock()

def create_archive(url: str) -> str | None:
    while True:
        try:
            rate_limit_lock.acquire()
            rate_limit_lock.release()
            archive_url = requests.get(f"https://web.archive.org/save/{url}", timeout=600).url
            logger.info(f"Created new archive link for {url}")
            return archive_url
        except requests.RequestException as error:
            if error.errno == 111:
                logger.info(f"Rate-limited while creating new archive link for {url}. Waiting.")
                rate_limit_lock.acquire()
                time.sleep(300)
                rate_limit_lock.release()
            else:
                logger.error(f"Failed to create a new archive link for {url}: {error}")
                return
            
def get_archive(url: str) -> str | None:
    try:
        archive = requests.get(f"https://archive.org/wayback/available?url={url}")
        snapshots = archive.json()["archived_snapshots"]
        closest = snapshots.get("closest")
        if closest and closest["available"] is True:
            archive_url = closest["url"]
            logger.info(f"Found existing archive link for {url}")
            return archive_url
        else:
            return
    except requests.RequestException:
        logger.error(f"Failed to search for archived copy of broken link to {url}")
        return


def check_citations(page: Path) -> None:
    """Checks that every footnote on a given page has a working primary link and an archive link.

    - If a footnote has an archive link already, does nothing.
    - If a footnote has no archive link but has a functional primary link, creates a new archive
    snapshot and adds a link to it.
    - If a footnote has no archive link and the primary link is broken, attempts to add a link to
    an existing archive.
    - If a footnote has no archive link, the primary link is broken, and there is no archive of the
    page, logs a warning.

    :param Path page: a Path object pointing to the page that needs processing.
    :rtype: None
    """

    # Read markdown, strip frontmatter, convert to html for parsing.
    contents = page.read_text()
    contents = re.sub(r"(?s)^---\n.*?\n---\n", "", contents, count=1)
    contents = markdown.markdown(contents, extensions=["fenced_code", "footnotes"])

    # Loop over every footnote.
    doc = bs4.BeautifulSoup(contents, features="html.parser")
    footnotes = doc.find("div", class_="footnote")
    if not footnotes:
        logger.debug(f"No footnotes found in {page.name}")
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
        if archive_link_present is True:
            continue

        logger.debug(f"No archive link found in citation {url}. Attempting fix.")

        # Check if the link is broken. If not, create a new archive.
        try:
            ok = requests.get(url).ok
        except requests.RequestException:
            ok = False

        #if ok:
        #    archive_url = create_archive(url)
        #    if archive_url is None:
        #        continue

        archive_url = get_archive(url)
        if archive_url is None:
            if ok:
                logger.info(f"No archived copy of {url} is available.")
            else:
                logger.warning(f"Footnote in {page.name} contains broken link to {url}. No archived copy is available.")
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
