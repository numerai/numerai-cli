from setuptools import setup

setup(name='numerai-cli',
      version='0.1',
      description='A library for helping to deploy a Numer.ai compute node',
      url='https://github.com/numerai/numerai-compute-cli',
      author='Numer.ai',
      author_email='contact@numer.ai',
      license='MIT',
      packages=['numerai_compute'],
      include_package_data=True,  # TODO add Manifest.in
      install_requires=[
          "click>=7",
          "boto3",
      ],
      entry_points={
          'console_scripts': ['numerai=numerai_compute.cli:main'],
      })
