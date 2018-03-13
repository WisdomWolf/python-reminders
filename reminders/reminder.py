import re
import pendulum
import logging
import logging.config
from dateparser import parse as dateparse
from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import yaml
from .watchers import HTTPWatcher, MQTTWatcher
from .alerters import LogAlerter
import os
from simpleeval import SimpleEval
import importlib

class Reminder(object):
    """
    Base Reminder object to handle watch and notification for a single reminder.
    """
    watcher_type_map = {'http': HTTPWatcher, 'mqtt': MQTTWatcher}
    alerter_type_map = {'log': LogAlerter}

    def __init__(self, condition, daemon=None, watcher=None, alerter=None):
        """
        Create Reminder object.

        :param str condition:
            An expression to indicate that an alert should be sent.
            Should evaluate to True or False only.
        :param ReminderDaemon daemon:
            A ReminderDaemon instance where jobs will be scheduled.
        :param Watcher watcher:
            A Watcher instance to handle resource monitoring.
        :param Alerter alerter:
            An Alerter instance to handle sending notifications for Reminder.
        """
        self._logger = logging.getLogger(__name__)
        self._daemon = daemon
        try:
            self._logger.setLevel(self._daemon.logger.level)
        except AttributeError:
            pass
        self.jobs = []
        self.job_ids = []
        self.condition = condition
        if watcher:
            self._logger.debug('creating watcher from: %s', watcher)
            watcher['reminder'] = self
            WatcherClass = getattr(importlib.import_module('reminders.watchers'), watcher.get('type'))
            self.watcher = WatcherClass(**watcher)
            jobs = self.watcher.schedules
            for job in jobs:
                job['func'] = self.check
                self._logger.debug('added job to jobs: %s', job)
                self.jobs.append(job)
        if alerter:
            self._logger.debug('creating alerter from: %s', alerter)
            alerter['reminder'] = self
            AlerterClass = getattr(importlib.import_module('reminders.alerters'), alerter.get('type'))
            self.alerter = AlerterClass(**alerter)
        self.simple_eval = SimpleEval()
        self.simple_eval.names.update({
            'status': self.status,
            'now': self.now,
        })
        self.simple_eval.functions = {
            'pendulum': pendulum,
            'date': pendulum.instance
        }

    @property
    def now(self):
        """Shortcut for expression evaluation against current time"""
        return pendulum.now()

    @property
    def status(self):
        if self.watcher:
            try:
                d = dateparse(self.watcher.update(), settings={'STRICT_PARSING': True})
                if d:
                    return d
                else:
                    return self.watcher.update()
            except TypeError:
                return None
        else:
            self._logger.error('No watcher associated', exc_info=True)
            return None

    def test_condition(self):
        """
        Evaluates self.expression
        .. deprecated:: 0.2
        """
        results = {}
        condition = self.condition.replace('$status', self.watcher.update())
        prefix, comparator, postfix = re.split(r'\s([<>(<=)(>=)(==)(!=)])\s', condition)
        prefix = "pendulum.instance(dateparse('{}'))".format(prefix) if dateparse(prefix, settings={'STRICT_PARSING': True}) else "'{}'".format(prefix) if (isinstance(prefix, str) and not prefix.isnumeric()) else prefix
        postfix = "pendulum.instance(dateparse('{}'))".format(postfix) if dateparse(postfix, settings={'STRICT_PARSING': True}) else "'{}'".format(postfix) if (isinstance(postfix, str) and not postfix.isnumeric()) else postfix
        expression = "results['content'] = {} {} {}".format(prefix, comparator, postfix)
        exec(expression)
        return results['content']

    def eval(self):
        """
        Evaluate self.expression

        :returns:   True if alert should be started
        :rtype:     bool
        """
        try:
            return self.simple_eval.eval(self.condition)
        except TypeError:
            self._logger.error('Error evaluating expression.', exc_info=True)
            return None

    def check(self):
        """Runs self.test_condition() and sends Alert if True."""
        if self.eval() and self.alerter:
            self._logger.debug('sending alert')
            self.alerter.alert()
        else:
            self._logger.debug('checked successfully - no alert necessary')

    def activate(self):
        """TBD - May be unnecessary at this level."""
        raise NotImplementedError("activate() hasn't been implemented yet")

    def deactivate(self):
        """TBD - May be unnecessary at this level."""
        raise NotImplementedError("deactivate() hasn't been implemented yet")


class ReminderDaemon(object):
    """Parent Daemon to keep track of scheduled jobs and watch for config file changes."""
    def __init__(self, blocking=True, timezone='UTC', config_path='.', logger_level=None, *args, **kwargs):
        """
        Create ReminderDaemon object.

        :param boolean blocking:
            Determines if Scheduler should be BlockingScheduler or BackgroundScheduler.
        :param str timzone: Timezone for the scheduler to use when scheduling jobs.
        :param str config_path: Path to configuration files.
        :param int logger_level: Level to set logger to.
        """
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
        """Start the observer and scheduler associated with daemon."""
        self._observer.start()
        self.scheduler.start()

    def add_reminder(self, reminder_config):
        """
        Create new reminder and add to daemon.

        :param dict reminder_config:
            Dictionary configuration for creating Reminder.
            Typically loaded from YAML file.
        """
        reminder_config['daemon'] = self
        reminder = Reminder(**reminder_config)
        self.update(reminder)

    def update(self, reminder):
        """
        Update Daemon with new Reminder object.
        Operates by either appending new reminder or replacing existing reminder.

        :param Reminder reminder: Reminder to be added or updated.
        """
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
        """
        Remove reminder from Daemon.

        :param Reminder reminder: The Reminder to be removed.
        """
        for job_id in reminder.job_ids:
            self.scheduler.remove_job(job_id.id)
        self.reminders.remove(reminder)

    def on_created(self, event):
        """
        Callback for on_created events to be associated with watchdog EventHandler.

        :param event: Event object representing the file system event.
        :event type: watchdog.events.FileSystemEvent
        """
        self.logger.debug('creation event received for {}'.format(event.src_path))
        if not event.is_directory:
            path = os.path.basename(event.src_path)
            self.load_yaml(path)
        else:
            self.logger.debug('skipping event because it is directory')

    def load_yaml(self, path):
        """
        Read and process yaml config.

        :param str path: The path of yaml config to load.
        """
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
        """
        Callback for on_deleted events to be associated with watchdog EventHandler.

        :param event: Event object representing the file system event.
        :event type: watchdog.events.FileSystemEvent
        """
        self.logger.debug('deletion event for %s', event.src_path)
        path = os.path.basename(event.src_path)
        if path in self.configs:
            self.remove_reminder(self.configs[path])
            del self.configs[path]
            self.logger.info('removed config for %s', path)
        else:
            self.logger.debug('No action taken for deletion event because it doesn\'t appear to exist in configs: %s', self.configs)
