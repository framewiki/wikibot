import concurrent
import concurrent.futures
import logging
import os
from pathlib import Path
import sys

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
        pr_handler.setFormatter(
            logging.Formatter("- %(levelname)s: %(message)s")
        )
        handlers.append(pr_handler)   

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s | %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    handlers.append(stdout_handler)

    logging.basicConfig(level=logging.INFO, handlers=handlers)

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
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(process_page, pages)


if __name__ == "__main__":
    main()
