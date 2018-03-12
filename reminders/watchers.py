import logging
from json import JSONDecodeError
import requests
import jmespath


class Watcher(object):
    """Base Watcher object for resource monitoring"""

    def __init__(self, reminder, schedules, *args, **kwargs):
        """
        Create Watcher object.

        :param Reminder reminder: Reminder instance to associate watcher with.
        :param dict schedules:
            Initial job schedules for watcher to use.
            *Possibly going to be removed from base class*
        """
        self._logger = logging.getLogger(__name__)
        self.reminder = reminder
        self.schedules = schedules

    def update(self):
        """
        **REQUIRED**
        Return status from monitored resource. Up to concrete class to determine implementation.
        """
        raise NotImplementedError('update() not yet implemented')


class HTTPWatcher(Watcher):
    """Watcher object for monitoring HTTP(S) REST Resource."""

    def __init__(self, request_kwargs, json_expression, *args, **kwargs):
        """
        Create HTTPWatcher object.

        :param dict request_kwargs:
            Dictionary containing keyword arguments to be passed to requests.get()
        :param str json_expression:
            JMESPath expression to be used to retrieve status from results JSON object.
        note: 
            Assumes response is JSON.  May require separate classes for JSON/XML/Others in future.
        """
        super().__init__(*args, **kwargs)
        self.request_kwargs = request_kwargs
        self.json_expression = json_expression

    def update(self):
        """Return resource status for Reminder to evaluate."""
        response = requests.get(**self.request_kwargs)
        try:
            result = jmespath.search(self.json_expression, response.json())
        except JSONDecodeError:
            self._logger.error('Unable to decode JSON from {}'.format(response))
            result = None
        return result


class MQTTWatcher(Watcher):
    """Watcher object for monitoring MQTT Resource."""

    def __init__(self, hostname, port=1883, tls=False, topic_kwargs=None, username=None, password=None, *args, **kwargs):
        """
        Create MQTTWatcher object.

        :param str hostname: url for MQTT client to connect to.
        :param int port: port to be used for MQTT connection.
        :param bool tls: Use SSL/TLS for secure connection.
        :param dict topic_kwargs:
            Dictionary containing:
              * topic to monitor
              * condition to start Alerter
              * condition to cancel Alerter
        :param str username: Username for MQTT client authentication.
        :param str password: Password for MQTT client authentication.
        """
        super().__init__(*args, **kwargs)
        self.topic_kwargs = topic_kwargs
        self._client = paho.Client()
        self.status = None
        for topic in topic_kwargs:
            self._client.message_add_callback(topic, listener_callback)

    def listener_callback(client, userdata, msg):
        """
        Callback to set status when msg received on monitored topic.

        :param client: Required by callback signature.
        :param userdata: Required by callback signature.
        :param msg: Message received on topic that generated this callback.
        """
        # This will be called by configured topics
        try:
            self.status = msg.payload if isinstance(msg.payload, str) else msg.payload.decode('utf8')
        except UnicodeDecodeError:
            self.status = 'ERR'

    def update(self):
        """Return status for Reminder evaluation."""
        return self.status
