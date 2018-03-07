import logging

class Alerter(object):
    
    def __init__(self, message):
        self.logger = logging.getLogger(__name__)
        self.message = message
        
    def alert(self):
        raise NotImplementedError('Alert not yet implemented')

class LogAlerter(Alerter):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def alert(self):
        self.logger.warn(self.message)
