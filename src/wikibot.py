import logging
import os
import sys
from pathlib import Path

import citations


logger = logging.getLogger(__name__)


def process_page(page: Path) -> bool:
    logger.info(f"Processing {page.name}")
    return citations.check_citations(page)


def main() -> None:
    handlers = []
    if os.environ.get("PRODUCTION"):
        pr_handler = logging.FileHandler("/github/workspace/pr.txt")
        pr_handler.setLevel(logging.WARNING)
        pr_handler.setFormatter(logging.Formatter("- %(message)s"))
        handlers.append(pr_handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(logging.Formatter("%(name)s | %(levelname)s: %(message)s"))
    handlers.append(stdout_handler)

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)

    # Get all markdown files from workspace.
    if os.environ.get("PRODUCTION"):
        workspace = "/github/workspace"
        logger.debug("Using production workspace")
    else:
        workspace = "./test_wiki"
        logger.debug("Using development workspace")

    repo = Path(workspace)
    pages = list(repo.glob("**/*.md"))

    # Apply each check to every page.
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #    executor.map(process_page, pages)
    for page in pages:
        process_page(page)


if __name__ == "__main__":
    main()
