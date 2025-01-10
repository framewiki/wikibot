import concurrent
import concurrent.futures
import logging
import os
from pathlib import Path

import citations

logger = logging.getLogger(__name__)


def process_page(page: Path) -> bool:
    logger.info(f"Processing {page.name}")
    return citations.check_citations(page)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

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
