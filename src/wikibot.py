import logging
import os
from pathlib import Path

import citations

logger = logging.getLogger(__name__)


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

    files_changed = False

    # Apply each check to every page.
    for page in pages:
        logger.info(f"Processing {page.name}")
        citations_changed = citations.check_citations(page)

        if citations_changed is True:
            files_changed = True

        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output is None:
            github_output = ""
        os.environ["GITHUB_OUTPUT"] = github_output + f"files_changed={files_changed}"


if __name__ == "__main__":
    main()
