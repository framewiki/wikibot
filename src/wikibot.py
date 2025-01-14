import concurrent.futures
import logging
import os
import sys
import traceback
from pathlib import Path

import citations


logger = logging.getLogger(__name__)


def process_page(page: Path) -> None:
    logger.info(f"Processing {page.name}")
    citations.check_citations(page)
    logger.info(f"Finished processing {page.name}")


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
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = {executor.submit(process_page, page): page for page in pages}
        # Get and log any exceptions with their tracebacks instead of ignoring them.
        for thread in concurrent.futures.as_completed(results):
            exception = thread.exception()
            if exception:
                tb = traceback.format_exception(exception)
                tb_string = ""
                for line in tb:
                    tb_string += line
                logger.error(f"\n```\n{tb_string}\n```")


if __name__ == "__main__":
    main()
