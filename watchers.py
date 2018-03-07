import logging
from json import JSONDecodeError


class Watcher(object):

    def __init__(self, schedules, *args, **kwargs):
        self._logger = logging.getLogger(__name__)
        self.schedules = schedules

    def update(self):
        raise NotImplementedError('update() not yet implemented')


class HTTPWatcher(Watcher):

    def __init__(self, request_kwargs, key, *args, **kwargs)
        super().__init__(*args, **kwargs)
        self.request_kwargs = request_kwargs
        self.key = key

    def update(self):
        response = requests.get(**self.request_kwargs)
        try:
            result = response.json().get(self.key)
        except JSONDecodeError:
            self._logger.error('Unable to decode JSON from {}'.format(response))
            result = None
        return result