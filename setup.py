from setuptools import setup

setup(name='python-reminders',
      version='0.1',
      py_modules=['reminders'],
      author='@wisdomwolf',
      author_email='wisdomwolf@gmail.com',
      install_requires=[
          'APScheduler>=3.5.1',
          'requests>=2.3.0'
      ],
)
