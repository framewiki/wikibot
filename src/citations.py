import logging
import os
import re
import threading
import time
import urllib.parse
from pathlib import Path

import bs4
import markdown
import requests

from exceptions import CitationCaptureException


logger = logging.getLogger(__name__)

host_denylist = []
host_denylist_lock = threading.Lock()


def create_archive(url: str) -> str:
    """Captures a new archive of the provided URL on the Archive.org Wayback Machine and returns
    the URL to it.

    Uses the Save Page Now API, documented at
    https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA

    :param str url: The URL of the page to archive.
    :rtype: str
    :return: An archive.org URL to a newly-captured archive.
    :raises: exceptions.CitationCaptureException
    """
    parsed_url = urllib.parse.urlparse(url)
    host = parsed_url.hostname
    if host in host_denylist:
        raise CitationCaptureException(f"{host} is denylisted.")

    headers = {
        "Accept": "application/json",
        "authorization": f"LOW {os.getenv("ARCHIVE_ACCESS_KEY")}:{os.getenv("ARCHIVE_SECRET_KEY")}",
    }
    data = {"url": url, "skip_first_archive": 1}

    # Tell Archive.org to queue a crawl and get the Job ID of it.
    logger.debug(f"Attempting to queue Wayback Machine capture of {url}.")
    try:
        req = requests.post("https://web.archive.org/save", data=data, headers=headers)
        response = req.json()
    except requests.RequestException as error:
        raise CitationCaptureException(f"Encountered an error while creating capture job: {error}")

    logger.debug(f"Capture Request Response: {response}")

    job_id = response.get("job_id")
    if job_id is None:
        if response.get("status") == "error":
            error_code = response.get("status_ext")
            if error_code == "error:too-many-daily-captures-host":
                logger.debug(f"Adding {host} to denylist for this run.")
                host_denylist_lock.acquire()
                if host not in host_denylist:
                    host_denylist.append(host)
                host_denylist_lock.release()
                raise CitationCaptureException(
                    f"The Wayback Machine has created too many captures of {host} today. Added to denylist for this run."
                )
            elif error_code == "error:user-session-limit":
                logger.info(
                    f"Rate limited while attempting to create archive of {url} because there are too many active capture sessions. Retrying in 5 seconds."
                )
                time.sleep(5)
                return create_archive(url)
            else:
                raise CitationCaptureException(
                    f"Wayback Machine reported {error_code} with the following message: {response.get("message")}"
                )
        else:
            raise CitationCaptureException(f"Bad response from Wayback Machine: {response}")

    # Check the job status until completed.
    status = "pending"
    while status == "pending":
        time.sleep(5)
        logger.debug(f"Checking status of capture job {job_id} for url {url}")
        try:
            req = requests.get(f"https://web.archive.org/save/status/{job_id}", headers=headers)
        except requests.RequestException as error:
            raise CitationCaptureException(
                f"Encountered an error while checking job status: {error}"
            )

        response = req.json()
        logger.debug(f"Status Check Response {response}")
        status = response["status"]

    if status == "success":
        logger.info(f"Successfuly captured archive of {url}")
        return f"https://web.archive.org/web/{response["timestamp"]}/{url}"
    elif status == "error":
        raise CitationCaptureException(f"Wayback Machine reported {response["exception"]}")


def find_archive(url: str) -> str | None:
    """Locates the most recent archive of the provided URL from the Wayback Machine.

    If the rate limit kicks in, retries infinitely (until the recursion limit) after the suggested
    amount of time (or every 10 seconds if no Retry-After header is provided.)

    :param str url: The URL of the page to archive.
    :rtype: str | None
    :return: None if an archive could not be located. Otherwise, an archive.org URL.
    """
    try:
        req = requests.get(f"https://archive.org/wayback/available?url={url}")
        if req.ok:
            snapshots = req.json()["archived_snapshots"]
            closest = snapshots.get("closest")
            if closest and closest["available"] is True:
                archive_url = closest["url"]
                logger.info(f"Found existing archive link for {url}")
                return archive_url
            else:
                return
        # If the API rate limits, wait for the suggested amount of time.
        elif req.status_code == 429:
            wait_time = req.headers.get("Retry-After")
            # If no time is suggested, wait for 10 seconds.
            if wait_time is None:
                wait_time = 10
            logger.info(
                f"Rate limited while attempting to locate archive for {url}. Waiting for {wait_time} seconds."
            )
            time.sleep(wait_time)
            return find_archive(url)
        else:
            logger.error(
                f"Failed to search for archived copy of {url}: Request returned HTTP status code {req.status_code}"
            )
    except requests.RequestException as error:
        logger.error(f"Failed to search for archived copy of {url}: {error}")
        return


def check_citations(page: Path) -> None:
    """Checks that every footnote on a given page has a working primary link and an archive link.

    - If a footnote has an archive link already, does nothing.
    - If a footnote has no archive link, attempts to add a link to an existing archive.
    - If a footnote has no archive link and no existing archive link is available, but the primary link is functional,
    creates and adds a link to a new archive snapshot.
    - If a footnote has no archive link, the primary link is broken, and there is no archive of the
    page, logs a warning.

    :param Path page: a Path object pointing to the page that needs processing.
    :rtype: None
    """

    # Read markdown, strip frontmatter, convert to html for parsing.
    contents = page.read_text()
    contents = re.sub(r"(?s)^---\n.*?\n---\n", "", contents, count=1)
    contents = markdown.markdown(contents, extensions=["fenced_code", "footnotes"])

    # Get the list of footnotes.
    doc = bs4.BeautifulSoup(contents, features="html.parser")
    footnotes = doc.find("div", class_="footnote")

    # Do nothing if there are no footnotes.
    if not footnotes:
        logger.debug(f"No footnotes found in {page.name}")
        return

    # Loop over footnotes.
    for note in footnotes.find_all("li"):
        links = note.find_all(
            "a", href=lambda href: href and href.startswith(("http://", "https://"))
        )

        # Make sure there is at least one link.
        if len(links) == 0:
            logger.warning(f"Footnote in {page.name} has no links. Skipping.")
            continue

        url = links[0].get("href")
        logger.debug(f"Checking citation {url} in {page.name}")

        # Check if there is an archive link.
        archive_link_present = False
        for link in links:
            link_url = link.get("href")
            if link_url.startswith("https://web.archive.org") or link_url.startswith(
                "http://web.archive.org"
            ):
                archive_link_present = True  # If there is an archive link, the footnote is fine.
                logger.debug(f"Found archive link in citation {url}")
                break
        if archive_link_present is True:
            continue

        logger.debug(f"No archive link found in citation {url}. Attempting fix.")

        # Try to find an existing archive.
        logger.debug(f"Attempting to locate archive of {url}.")
        archive_url = find_archive(url)
        if archive_url is not None:
            logger.debug(f"Found archive link {archive_url} for primary url {url}")

        # Check if the primary link is broken.
        try:
            req = requests.get(url)
            link_ok = req.ok
            if link_ok is False:
                logger.debug(f"Link {url} is broken. Server responded {req.status_code}")
        except requests.RequestException as error:
            link_ok = False
            logger.debug(f"Link {url} is broken. Request raised exception: {error}")

        # If no archive is available and the primary link is not broken, create a new archive.
        if archive_url is None and link_ok is True:
            logger.debug(f"Failed to locate archive of {url}. Attempting to create.")
            try:
                archive_url = create_archive(url)
            except CitationCaptureException as error:
                logger.warning(
                    f"Footnote in {page.name} contains {url}, for which no archive is available and none could be created: {error}"
                )
                continue
        elif link_ok is False:
            logger.warning(
                f"Footnote in {page.name} contains broken link to {url}. No archived copy could be located."
            )
            continue

        # Put archive_url on the page.
        logger.debug(f"Writing archive url {archive_url} to {page.name}")
        with page.open("r") as file:
            lines = file.readlines()
        modified_lines = []
        wrote = False
        for line in lines:
            if line.startswith("[^") and re.search(
                rf"(?<=[\s<\[\(]){re.escape(url)}(?=[\s>\]\)])", line
            ):
                line = f"{line.rstrip()} [Archived]({archive_url}) \n"
                wrote = True
            modified_lines.append(line)
        with page.open("w") as file:
            file.writelines(modified_lines)
        if wrote is False:
            logger.error(f"Failed to write {archive_url} to {page.name} for primary link {url}")
        else:
            logger.debug(f"Wrote {archive_url} to {page.name} for primary link {url}")
