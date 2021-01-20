from setuptools import setup
from os import path
from glob import glob

# read the contents of the README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

<<<<<<< HEAD
setup(name='numerai-cli',
      version='0.2.4',
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
=======
setup(
    name='numerai-cli',
    version='0.2.4',
    description='A library for helping to deploy a Numer.ai compute node',
    url='https://github.com/numerai/numerai-cli',
    author='Numer.ai',
    author_email='contact@numer.ai',
    license='MIT',
    packages=['cli'],
    # package_data={'': ['cli/examples', 'cli/terraform']},
    include_package_data=True,
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.6.0',
    install_requires=[
        "click>=7",
        "boto3",
        "numerapi>=2.4.0",
        "colorama",
        "requests",
    ],
    entry_points={
        'console_scripts': ['numerai=cli.__main__'],
    }
)
>>>>>>> restructure cli for multi-app setup and more descriptive commands/modules, rename setup to create (avoid clash with python setup.py), tested and fixed app setup/config/creation
