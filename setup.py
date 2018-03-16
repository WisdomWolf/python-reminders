from setuptools import setup
import reminders

setup(name='python-reminders',
      version=reminders.__version__,
      py_modules=['reminders'],
      author='@wisdomwolf',
      author_email='wisdomwolf@gmail.com',
      install_requires=[
          'APScheduler>=3.5.1',
          'requests>=2.3.0'
      ],
)
