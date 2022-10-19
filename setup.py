# Very basic and pretty bad setup.py for use with pip
# pip install git+https://github.com/alwinm/fiso.git

from setuptools import setup, find_packages

subs = setuptools.find_packages(where='.')
packages_ = ['fiso']
for sub in subs:
    packages_.append('fiso.' + sub)


setup(name='fiso',
      version='0.0',
      packages=packages_,
      package_dir={"fiso":"./"},
      )
