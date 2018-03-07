import re
import pendulum
from dateparser import parse as dateparse

class Reminder(object):

    def __init__(self, condition, daemon=None, watcher_config=None, alerter_config=None):
        self._logger = logging.getLogger(__name__)
        self._daemon = daemon
        self.watcher = None # Need to create and associate watcher from config
        self.alerter = None # Need to create and associate alerter from config
        self.condition = condition
        
    def test_condition(self):
        results = {}
        condition = self.condition.replace('$status', self.watcher.update())
        prefix, comparator, postfix = re.split(r'\s([<>(<=)(>=)(==)(!=)])\s', condition)
        prefix = "pendulum.instance(dateparse('{}'))".format(prefix) if dateparse(prefix, settings={'STRICT_PARSING': True}) else "'{}'".format(prefix) if (isinstance(prefix, str) and not prefix.isnumeric()) else prefix
        postfix = "pendulum.instance(dateparse('{}'))".format(postfix) if dateparse(postfix, settings={'STRICT_PARSING': True}) else "'{}'".format(postfix) if (isinstance(postfix, str) and not postfix.isnumeric()) else postfix
        expression = "results['content'] = {} {} {}".format(prefix, comparator, postfix)
        exec(expression)
        return results['content']

    def check(self):
        if self.test_condition() and self.alerter:
            self.alerter.alert()
        
    def activate(self):
        raise NotImplementedError("activate() hasn't been implemented yet")
        
    def deactivate(self):
        raise NotImplementedError("deactivate() hasn't been implemented yet")
