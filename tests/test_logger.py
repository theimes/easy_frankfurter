import logging
import sys
import contextlib


@contextlib.contextmanager
def _isolated_easy_frankfurter_import():
    """
    Purge easy_frankfurter from sys.modules, yield for the test body, then restore
    the original module objects so the rest of the test session isn't affected.

    Without restoration the patching target "easy_frankfurter._base_engine.urlopen"
    ends up pointing at the freshly re-imported module while engine classes
    imported by other test files still hold references to the original module,
    causing mock patches to miss the real call site.
    """
    saved = {k: v for k, v in sys.modules.items() if k.startswith("easy_frankfurter")}
    for key in saved:
        del sys.modules[key]
    try:
        yield
    finally:
        # Remove any newly created easy_frankfurter modules, then put originals back.
        for key in list(sys.modules.keys()):
            if key.startswith("easy_frankfurter"):
                del sys.modules[key]
        sys.modules.update(saved)


def test_import_does_not_configure_root_logger_handlers():
    """Importing easy_frankfurter must not add handlers to the root logger."""
    root = logging.getLogger()
    handlers_before = list(root.handlers)

    with _isolated_easy_frankfurter_import():
        import easy_frankfurter  # noqa: F401
        assert root.handlers == handlers_before, (
            f"Import added handlers to root logger: {root.handlers}"
        )


def test_import_does_not_change_root_logger_level():
    """Importing easy_frankfurter must not change the root logger's level."""
    root = logging.getLogger()
    level_before = root.level

    with _isolated_easy_frankfurter_import():
        import easy_frankfurter  # noqa: F401
        assert root.level == level_before, (
            f"Import changed root logger level from {level_before} to {root.level}"
        )


def test_library_logger_has_null_handler():
    """The easy_frankfurter logger must have a NullHandler so it is silent by default."""
    with _isolated_easy_frankfurter_import():
        import easy_frankfurter  # noqa: F401
        logger = logging.getLogger("easy_frankfurter")
        assert any(isinstance(h, logging.NullHandler) for h in logger.handlers), (
            "easy_frankfurter logger must have a NullHandler"
        )
