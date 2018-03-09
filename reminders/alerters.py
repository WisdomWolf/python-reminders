import logging

class Alerter(object):
    """Base Alert object to handle reminder notifications."""

    def __init__(self, reminder, message, notifiers=None, repeat_args=None, *args, **kwargs):
        """
        Create Alerter object.

        :param Reminder reminder: Reminder instance to associate this alert with.
        :param str message:
            Message to be sent by notifier(s).
            note: This was added as part of POC. Likely to be removed in future.
        :param notifiers: ¯\_(ツ)_/¯
        :param dict repeat_args:
            Arguments to set repeat interval and max number of repeats.
            note: Might make more sense to seperate out into individual arguments.
        """
        self.logger = logging.getLogger(__name__)
        self.message = message
        
    def alert(self):
        raise NotImplementedError('Alert not yet implemented')

    def activate(self):
        raise NotImplementedError('activate() not yet implemented')

    def deactivate(self):
        raise NotImplementedError('deactivate() not yet implemented')

class LogAlerter(Alerter):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def alert(self):
        self.logger.warn(self.message)