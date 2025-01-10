import concurrent
import concurrent.futures
import logging
import os
from pathlib import Path

import citations

logger = logging.getLogger(__name__)


def process_page(page:Path) -> bool:
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
        results = list(executor.map(process_page, pages))

    # Set GitHub Action output.
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output is None:
        github_output = ""
    os.environ["GITHUB_OUTPUT"] = github_output + f"files_changed={any(results)}"


if __name__ == "__main__":
    main()
