from setuptools import setup, find_packages

setup(name='fiso',
      version='0.0',
      packages=find_packages(where='..'),
      package_dir={"fiso":"./"},
      )
