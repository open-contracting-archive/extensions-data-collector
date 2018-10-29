class OCDSExtensionsDataCollectorError(Exception):
    """Base class for exceptions from within this package"""


class CommandError(OCDSExtensionsDataCollectorError):
    """Errors from within this package's CLI"""
