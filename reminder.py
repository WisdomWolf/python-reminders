import re
import pendulum
import logging
import logging.config
from dateparser import parse as dateparse
from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import yaml
from watchers import HTTPWatcher, MQTTWatcher
from alerters import LogAlerter
import os
import argparse

class Reminder(object):

    watcher_type_map = {'http': HTTPWatcher, 'mqtt': MQTTWatcher}
    alerter_type_map = {'log': LogAlerter}

    def __init__(self, condition, daemon=None, watcher=None, alerter=None):
        self._logger = logging.getLogger(__name__)
        self._daemon = daemon
        self._logger.setLevel(self._daemon.logger.level)
        self.jobs = []
        self.job_ids = []
        if watcher:
            self._logger.debug('creating watcher from: %s', watcher)
            watcher['reminder'] = self
            self.watcher = self.watcher_type_map.get(watcher.get('type'))(**watcher)
            jobs = self.watcher.schedules
            for job in jobs:
                job['func'] = self.check
                self._logger.debug('added job to jobs: %s', job)
                self.jobs.append(job)
        if alerter:
            self._logger.debug('creating alerter from: %s', alerter)
            alerter['reminder'] = self
            # self.alerter = self.alerter_type_map.get(alerter.get('type'))(**alerter) or LogAlerter(**alerter)
            self.alerter = LogAlerter(**alerter)
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
            self._logger.debug('sending alert')
            self.alerter.alert()
        else:
            self._logger.debug('checked successfully - no alert necessary')

    def activate(self):
        raise NotImplementedError("activate() hasn't been implemented yet")

    def deactivate(self):
        raise NotImplementedError("deactivate() hasn't been implemented yet")


class ReminderDaemon(object):

    def __init__(self, blocking=True, timezone='UTC', config_path='.', logger_level=None, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        if logger_level:
            self.logger.setLevel(logger_level)
        self.logger.debug('initializing daemon')
        self.scheduler = BlockingScheduler(timezone=timezone) if blocking else BackgroundScheduler(timezone=timezone)
        self.reminders = []
        self.configs = {}
        self.timezone = timezone
        self._observer = Observer()
        self.config_path = config_path
        for _, _, files in os.walk(self.config_path):
            for file_ in files:
               filename, extension = os.path.splitext(file_)
               if extension in ['.yaml', '.yml']:
                   self.load_yaml(file_)
        self._watchdog_handler = PatternMatchingEventHandler('*.yaml;*.yml')
        self._watchdog_handler.on_created = self.on_created
        self._watchdog_handler.on_modified = self.on_created
        self._watchdog_handler.on_deleted = self.on_deleted
        self._observer.schedule(self._watchdog_handler, self.config_path)

    def start(self):
        self._observer.start()
        self.scheduler.start()

    def add_reminder(self, reminder_config):
        reminder_config['daemon'] = self
        reminder = Reminder(**reminder_config)
        self.update(reminder)

    def update(self, reminder):
        if reminder not in self.reminders:
            for job in reminder.jobs:
                self.logger.debug('adding job to scheduler: %s', job)
                try:
                    job_id = self.scheduler.add_job(**job)
                    reminder.job_ids.append(job_id)
                except TypeError:
                    logger.error('Unable to add job to scheduler', exc_info=True)
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
            self.load_yaml(path)
        else:
            self.logger.debug('skipping event because it is directory')

    def load_yaml(self, path):
        self.logger.debug('loading yaml config from %s', path)
        path = os.path.join(self.config_path, path)
        with open(path) as f:
            config = yaml.safe_load(f.read())
            reminder_config = config.get('reminder')
            self.logger.debug('loaded reminder_config: %s', reminder_config)
            if reminder_config:
                self.add_reminder(reminder_config)
                self.logger.info('loaded reminder config from %s', path)
                self.configs[os.path.basename(path)] = self.reminders[-1]
        # self.configs[path] = config

    def on_deleted(self, event):
        self.logger.debug('deletion event for %s', event.src_path)
        path = os.path.basename(event.src_path)
        if path in self.configs:
            self.remove_reminder(self.configs[path])
            del self.configs[path]
            self.logger.info('removed config for %s', path)
        else:
            self.logger.debug('No action taken for deletion event because it doesn\'t appear to exist in configs: %s', self.configs)
