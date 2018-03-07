import re
import pendulum
from dateparser import parse as dateparse

class Reminder(object):

    def __init__(self, daemon, watcher, alerter, condition):
        self._logger = logging.getLogger(__name__)
        self._daemon = daemon
        self.watcher = watcher
        self.alerter = alerter
        self.condition = condition
        
    def check(self):
        results = {}
        condition = self.condition.replace('$status', self.watcher.update())
        prefix, comparator, postfix = re.split(r'\s([<>(<=)(>=)(==)(!=)])\s', condition)
        prefix = "pendulum.instance(dateparse('{}'))".format(prefix) or prefix
        postfix = "pendulum.instance(dateparse('{}'))".format(postfix) or postfix
        expression = "results['content'] = {} {} {}".format(prefix, comparator, postfix)
        exec(expression)
        return results['content']
        
    def activate(self):
        pass
        
    def deactivate(self):
        pass