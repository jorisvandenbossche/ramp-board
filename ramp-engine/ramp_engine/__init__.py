from .dispatcher import Dispatcher
from .local import CondaEnvWorker
from .aws import AWSWorker

from ._version import __version__

available_workers = {'conda': CondaEnvWorker,
                     'aws': AWSWorker}

__all__ = [
    'AWSWorker',
    'CondaEnvWorker',
    'Dispatcher',
    'available_workers',
    '__version__'
]
