import os
from setuptools import find_packages, setup
from codecs import open
import sys

# Get the long description from the README file
with open(os.path.join(os.getcwd(), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

install_requires = [
    'aiohttp',
    'aiofiles',
    'httptools',
    "lxml",
    'uvloop'
]

if sys.platform.startswith("win"):
    install_requires.remove("uvloop")


setup(
    name="acrawl",
    version="0.0.1",

    description="Async crawler framework based on asyncio",
    long_description=long_description,

    author="CodingCrush",
    author_email="codingcrush@163.com",

    url='https://github.com/CodingCrush/acrawl',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='scrapy crawler asyncio uvloop',
    install_requires=install_requires,
    license='MIT',
    packages=find_packages(exclude=['contrib', 'docs', 'examples', 'tests']),
    include_package_data=True,
)
