class WikibotException(Exception):
    """Base for all Wikibot exceptions."""

    pass


class CitationException(WikibotException):
    """Base for all exceptions raised by Wikibot's citations module."""

    pass


class CitationCaptureException(CitationException):
    """Raised when Wikibot's citations module fails to capture an archive."""

    pass
