from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from apscheduler.schedulers.base import STATE_STOPPED, STATE_PAUSED, STATE_RUNNING
import logging

class Reminder(object):

    def __init__(self, units, interval, check_function):
        self.logger = logging.getLogger(__name__)
        self._units = units
        self._interval = int(interval)
        self._check_function = check_function
        self._job_args = (check_function, 'interval')
        self._job_kwargs = {self._units: self._interval}
        self.scheduler = BackgroundScheduler()
        #self.scheduler = BlockingScheduler()
        self.scheduler.add_job(*self._job_args, **self._job_kwargs)
        self.active = False
        self.logger.info('Reminder created with repeat rate of {} {}.'.format(self._interval, self._units))

    def activate(self):
        self.active = True
        if not any(self.scheduler.get_jobs()):
            self.scheduler.add_job(*self._job_args, **self._job_kwargs)
        if self.scheduler.state == STATE_STOPPED:
            self.scheduler.start()
            self.logger.info('reminder activated')
        if self.scheduler.state == STATE_PAUSED:
            self.scheduler.resume()
            self.logger.info('reminder resumed')

    def cancel(self):
        if self.active:
            self.active = False
            self.scheduler.pause()
            self.scheduler.remove_all_jobs()
            self.logger.info('reminder canceled')

    def modify(self, units=None, interval=None, check_function=None):
        units = units or self._units
        interval = interval or self._interval
        check_function = check_function or self._check_function
        if self.scheduler.state == STATE_RUNNING:
            logger.warning("It's a bad idea to alter Reminder while it's running.")
        self._job_args = (check_function, 'interval')
        self._job_kwargs = {units: interval}
