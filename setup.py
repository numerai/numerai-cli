from setuptools import setup
from os import path

# read the contents of the README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='numerai-cli',
    version='0.3.2.dev08',
    description='A library for deploying Numer.ai Prediction Nodes.',
    url='https://github.com/numerai/numerai-cli',
    author='Numer.ai',
    author_email='contact@numer.ai',
    license='MIT',
    packages=['numerai'],
    include_package_data=True,
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.6.0',
    install_requires=[
        "click>=7",
        "boto3",
        "numerapi>=2.4.5",
        "colorama",
        "requests",
    ],
    entry_points={
        'console_scripts': ['numerai=numerai:main'],
    }
)