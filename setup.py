from setuptools import setup, find_packages

subs = setuptools.find_packages(where='.')
subs.append('')

setup(name='fiso',
      version='0.0',
      packages=['fiso' + sub for sub in subs],
      package_dir={"fiso":"./"},
      )
