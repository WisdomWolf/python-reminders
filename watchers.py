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
        
        
class MQTTWatcher(Watcher):

    def __init__(self, hostname, port=1883, tls=False, topic_kwargs=None, username=None, password=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.topic_kwargs = topic_kwargs
        self._client = paho.Client()
        self.status = None
        for topic in topic_kwargs:
            self._client.message_add_callback(topic, listener_callback)
        
    def listener_callback(client, userdata, msg):
        # This will be called by configured topics
        try:
            self.status = msg.payload if isinstance(msg.payload, str) else msg.payload.decode('utf8')
        except UnicodeDecodeError:
            self.status = 'ERR'
            
    def update(self):
        return self.status