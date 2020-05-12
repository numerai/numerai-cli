from setuptools import setup

# read the contents of the README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='numerai-cli',
      version='0.1.22',
      description='A library for helping to deploy a Numer.ai compute node',
      url='https://github.com/numerai/numerai-cli',
      author='Numer.ai',
      author_email='contact@numer.ai',
      license='MIT',
      packages=['numerai_compute'],
      include_package_data=True,
      long_description=long_description,
      long_description_content_type='text/markdown',
      install_requires=[
          "click>=7",
          "boto3",
          "numerapi>=2.2.4",
          "colorama",
          "requests",
      ],
      entry_points={
          'console_scripts': ['numerai=numerai_compute.cli:main'],
      })
