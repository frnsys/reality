from setuptools import setup, find_packages

setup(
    name='reality',
    version='0.0.1',
    description='news slurper',
    url='https://github.com/frnsys/reality',
    author='Francis Tseng (@frnsys)',
    license='MIT',

    packages=find_packages(),
    install_requires=[
        'feedparser==5.2.1',
        'python-dateutil==2.5.3',
        'tldextract==2.0.1',
        'newspaper3k==0.1.7',
        'spacy==0.101.0'
    ]
)