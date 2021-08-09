from os import path
from setuptools import setup


def readme():
    this_directory = path.abspath(path.dirname(__file__))
    with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        return f.read()


setup(
    name='pytr',
    version='0.0.3',
    description='Use TradeRepublic in terminal',
    long_description=readme(),
    long_description_content_type='text/markdown',
    url='https://gitlab.com/marzzzello/pytr/',
    author='marzzzello',
    author_email='853485-marzzzello@users.noreply.gitlab.com',
    license='MIT',
    packages=['pytr'],
    python_requires='>=3.5',
    entry_points={
        'console_scripts': [
            'pytr = pytr.main:main',
        ],
    },
    #  scripts=['traderep'],
    # install_requires=['py_tr'],
    install_requires=['coloredlogs', 'ecdsa', 'pygments', 'requests_futures', 'shtab', 'websockets'],
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
