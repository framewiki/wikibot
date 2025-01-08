import os
from pathlib import Path

import citations


def main() -> None:
    # Get all markdown files from workspace.
    if os.environ.get("PRODUCTION"):
        workspace = "/github/workspace"
    else:
        workspace = "./test_wiki"
        
    repo = Path(workspace)
    pages = list(repo.glob("**/*.md"))
    
    for page in pages:
        citations.check_citations(page)


if __name__ == "__main__":
    main()
