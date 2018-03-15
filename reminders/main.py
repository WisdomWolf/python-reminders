from .reminders import Reminder, ReminderDaemon
import logging
import logging.config
import os
import yaml
import argparse

def setup_logging(
        default_path='./config/logging_config.yaml',
        default_level=logging.INFO,
        env_key='LOG_CFG'
):
    """Setup logging configuration
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="Enable debug logging",
                        action='store_true')
    args = parser.parse_args()
    logger_level = logging.DEBUG if args.debug else logging.INFO
    reminder_daemon = ReminderDaemon(timezone='US/Eastern', config_path='./config/reminders', logger_level=logger_level)
    if args.debug:
        reminder_daemon.logger.setLevel(logging.DEBUG)
    for _, _, files in os.walk(reminder_daemon.config_path):
        for file_ in files:
           filename, extension = os.path.splitext(file_)
           if extension in ['.yaml', '.yml']:
               reminder_daemon.load_yaml(file_)
    reminder_daemon.start()

if __name__ == '__main__':
    main()
