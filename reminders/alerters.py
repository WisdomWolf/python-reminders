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
        self.reminder = reminder
        self.message = message
        self.repeat_interval = repeat_interval
        self.repeat_interval['trigger'] = 'interval'
        self.repeat_interval['func'] = self.alert
        self.max_repeat = max_repeat
        self.current_repeats = 0
        self.alert_on_activate = alert_on_activate
        self.jobs = []
        self.active = False

    def alert(self):
        """Send alert"""
        self.logger.debug('emitting alert')
        if self.current_repeats < self.max_repeat:
            self.current_repeats += 1
        else:
            self.logger.debug('deactivating alerts due to max_repeat')
            self.deactivate()

    def activate(self):
        """Activate alerts"""
        self.active = True
        self.logger.debug('alert activated')
        if self.alert_on_activate:
            self.alert()
        # TODO Make job scheduling better handled without jumping through multiple classes
        job = self.reminder._daemon.scheduler.add_job(**self.repeat_interval)
        self.logger.debug('alert job added to scheduler')
        self.jobs.append(job)
        self.reminder.job_ids.append(job.id)

    def deactivate(self):
        """Deactivate all existing alerts."""
        self.active = False
        self.logger.debug('alert deactivated')
        self.current_repeats = 0
        # TODO Handle job addition/removal better
        for job in self.jobs:
            self.reminder._daemon.scheduler.remove_job(job.id)
            self.reminder.job_ids.remove(job.id)
        self.logger.debug('all alert jobs removed from scheduler')


class LogAlerter(Alerter):
    """Alerter for outputting to logger"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def alert(self):
        """Emit alert to log"""
        super().alert()
        if self.active:
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
        super().alert()
        if self.active:
            self.logger.debug('posting HTTPAlert: {}'.format(self.request_kwargs))
            requests.post(**self.request_kwargs)
