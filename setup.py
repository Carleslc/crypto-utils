from setuptools import setup, find_packages

with open('README.md', 'r') as readme_f:
  readme = readme_f.read()

setup(
  name='crypto-utils',
  version='0.1',
  description='Blockchain financial utilities',
  long_description=readme,
  author='Carlos Lázaro Costa',
  author_email='lazaro.costa.carles@gmail.com',
  url='https://github.com/Carleslc/crypto-utils',
  license='MIT',
  packages=find_packages(exclude='crypto.scripts'),
  install_requires=['web3', 'bscscan-python', 'python-dotenv'],
  entry_points={
    'console_scripts': [
      'bsc_info = crypto.scripts.bsc_info:main',
    ],
    'gui_scripts': []
  }
)
