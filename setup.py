import os
from setuptools import find_packages, setup
from codecs import open
import sys


# Get the long description from the README file
with open(os.path.join(os.path.dirname(
        os.path.realpath(__file__)), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

install_requires = [
    'aiohttp',
    'aiofiles',
    'async_timeout',
    'httptools',
    "lxml",
    "pyquery",
    'uvloop',
    'click',
    'ujson',
    'user_agent',
    'aioredis==1.0.0b2',
    'umsgpack'
]

if sys.platform.startswith("win"):
    install_requires.remove("uvloop")


setup(
    name="aiocrawler",
    version="0.0.2",

    description="Async crawler framework based on asyncio",
    long_description=long_description,

    author="CodingCrush",
    author_email="codingcrush@163.com",

    url='https://github.com/CodingCrush/aiocrawler',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='scrapy crawler asyncio uvloop',
    install_requires=install_requires,
    license='MIT',
    packages=find_packages(exclude=['docs', 'examples', 'tests']),
    include_package_data=True,
)
