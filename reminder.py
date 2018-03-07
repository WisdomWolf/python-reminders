import re
import pendulum
import logging
from dateparser import parse as dateparse
from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import yaml
from watchers import HTTPWatcher, MQTTWatcher

class Reminder(object):

    watcher_type_map = {'http': HTTPWatcher, 'mqtt': MQTTWatcher}

    def __init__(self, condition, daemon=None, watcher=None, alerter=None):
        self._logger = logging.getLogger(__name__)
        self._daemon = daemon
        self.jobs = []
        if watcher:
            watcher['reminder'] = self
            self.watcher = self.watcher_type_map.get(watcher.get('type'))(**watcher)
            jobs = self.watcher.schedules
            for job in jobs:
                job['func'] = self.check
                self.jobs.append(job)
        if alerter:
            # Will need logic similar to above
            self.alerter = alerter
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


class ReminderDaemon(object):

    def __init__(self, blocking=True, timezone='UTC', config_path='.', *args, **kwargs):
        self.scheduler = BlockingScheduler(timezone=timezone) if blocking else BackgroundScheduler(timezone=timezone)
        self.reminders = []
        self.timezone = timezone
        self._observer = Observer()
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self._watchdog_handler = PatternMatchingEventHandler('*.yaml;*.yml')
        self._watchdog_handler.on_created = self.on_created
        self._watchdog_handler.on_modified = self.on_created
        self._watchdog_handler.on_deleted = self.on_deleted
        self._observer.schedule(self._watchdog_handler, self.config_path, recursive=True)
        self.configs = {}

    def start(self):
        self.scheduler.start()
        self._observer.start()

    def update(self, reminder):
        if reminder not in self.reminders:
            for job in reminder.jobs:
                job_id = self.scheduler.add_job(**job)
                reminder.job_ids.append(job_id)
            self.reminders.append(reminder)
        else:
            self.remove_reminder(reminder)
            self.update(reminder)

    def remove_reminder(self, reminder):
        for job_id in reminder.job_ids:
            self.scheduler.remove_job(job_id.id)
            self.reminders.remove(reminder)

    def on_created(self, event):
        self.logger.debug('creation event received for {}'.format(event.src_path))
        if not event.is_directory:
            path = event.src_path.strip(self.config_path).strip('/')
            with open(event.src_path) as f:
                config = yaml.safe_load(f.read())
            self.configs[path] = config
        else:
            self.logger.debug('skipping event because it is directory')

    def on_deleted(self, event):
        if event.src_path in self.configs:
            del self.configs[event.src_path]
