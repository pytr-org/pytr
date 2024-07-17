from pathlib import Path
from setuptools import setup
import os

def find_locale_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

locale_files = find_locale_files('locale')

def readme():
    this_directory = Path(__file__).parent.resolve()
    with open(this_directory / 'README.md', encoding='utf-8') as f:
        return f.read()


setup(
    name='pytr',
    version='0.2.1',
    description='Use TradeRepublic in terminal',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://gitlab.com/pytr-org/pytr/',
    author='marzzzello',
    author_email='853485-marzzzello@users.noreply.gitlab.com',
    license='MIT',
    packages=['pytr'],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'pytr = pytr.main:main',
        ],
    },
    package_data={
        '': locale_files,  # Include locale files
    },
    install_requires=[
        'certifi',
        'coloredlogs',
        'ecdsa',
        'packaging',
        'pathvalidate',
        'pygments',
        'requests_futures',
        'shtab',
        'websockets>=10.1',
    ],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        'Programming Language :: Python :: 3 :: Only',
        "Operating System :: OS Independent",
        'Development Status :: 3 - Alpha',
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    zip_safe=False,
)
