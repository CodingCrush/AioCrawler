import logging
import sys


def has_level_handler(logger):
    """Check if there is a handler in the logging chain that will handle the
    given logger's :meth:`effective level <~logging.Logger.getEffectiveLevel>`.
    """
    level = logger.getEffectiveLevel()
    current = logger

    while current:
        if any(handler.level <= level for handler in current.handlers):
            return True
        if not current.propagate:
            break
        current = current.parent

    return False


default_handler = logging.StreamHandler(sys.stdout)
default_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))


def create_logger(instance):
    """Get the AioCrawl's instance logger and configure it.
    When the instance.debug is enabled, set the logger level to
    logging.DEBUG` if it is not set.
    """
    logger = logging.getLogger(instance.__class__.__name__)

    if instance.debug and logger.level == logging.NOTSET:
        logger.setLevel(logging.DEBUG)

    if not has_level_handler(logger):
        logger.addHandler(default_handler)

    return logger
