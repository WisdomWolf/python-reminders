import logging
import requests
import json

class Alerter(object):
    """Base Alert object to handle reminder notifications."""

    def __init__(self, reminder, message, notifiers=None, repeat_interval={}, max_repeat=0,
                 alert_on_activate=True, *args, **kwargs):
        """
        Create Alerter object.

        :param Reminder reminder: Reminder instance to associate this alert with.
        :param str message:
            Message to be sent by notifier(s).
            note: This was added as part of POC. Likely to be removed in future.
        :param notifiers: ¯\_(ツ)_/¯
        :param dict repeat_args:
            Arguments to set repeat interval
        :param int max_repeat: number of times alert should repeat.
        :param bool alert_on_activate:
            When ``True`` alert will be emitted as soon as activated rather than
            waiting for first scheduled job to trigger.
        """
        self.logger = logging.getLogger(__name__)
        self.message = message
        self.repeat_interval = repeat_interval
        self.max_repeat = 0
        self.current_repeats = 0
        self.alert_on_activate = alert_on_activate
        self.active = False

    def alert(self):
        raise NotImplementedError('Alert not yet implemented')

    def activate(self):
        self.active = True
        if self.alert_on_activate:
            self.alert()

    def deactivate(self):
        self.active = False
        self.current_repeats = 0


class LogAlerter(Alerter):
    """Alerter for outputting to logger"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def alert(self):
        """Emit alert to log"""
        self.logger.warn(self.message)


class HTTPAlerter(Alerter):
    """Alerts via POST to HTTP REST interface"""

    def __init__(self, request_kwargs, json_params=True, *args, **kwargs):
        """
        Create HTTPAlerter object
        
        :param dict request_kwargs:
            Dictionary containing keyword arguments to be passed to requests.post()
        :param bool json_params:
            Indicates if request_kwargs['data'] should be transmitted as JSON string.
        """
        super().__init__(*args, **kwargs)
        if json_params and request_kwargs.get('data'):
            request_kwargs['data'] = json.dumps(request_kwargs['data'])
        self.request_kwargs = request_kwargs

    def alert(self):
        """Emit Alert"""
        self.logger.debug('posting HTTPAlert: {}'.format(self.request_kwargs))
        requests.post(**self.request_kwargs)
