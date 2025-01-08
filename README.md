# Wikibot
Wikibot is an automated tool used to improve [Framewiki](https://framewiki.net), the unofficial Framework wiki. It completes chores such as archiving citation links, locating broken links, and populating the description field.

Wikibot does not generate content or use any form of AI. All content on Framewiki is human-written; Wikibot only updates formatting and fixes links. All changes made by Wikibot require human validation before they are published.

## Development
Wikibot includes a devcontainer.json[^1] file preconfigured with the development environment.[^2] The Visual Studio Code Devcontainer Extension or GitHub Codespaces are recommended.

If you wish to set up your own development environment, Wikibot uses [Poetry](https://python-poetry.org/docs/) for dependency management and requires Python 3.13.

Wikibot is maintained by Framewiki. The [Framewiki Code of Conduct](https://framewiki.net/framewiki:code-of-conduct) applies to all contributors.

## Usage
- Requires actions/checkout

## TODO
- [x] Find all Markdown files
- [ ] Link Checking and Archiving
    - [x] If a link has an archive link, ignore it.
    - [x] If a link has no archive link and still exists, add an archive link.
    - [ ] If a link has no archive link and does not exist, post a warning about it to the talk section.
- [ ] Populate description field based on first sentence.
