from setuptools import setup, find_packages


setup(
    name='boosh',
    version='0.0.1',
    packages=find_packages(),

    install_requires=[
        'click',
        'botocore==0.57.0',
    ],

    entry_points={
        'console_scripts': [
            'benv_creds = boosh.benv:main',
        ],
    },
    scripts=[
        'benv.sh',
    ],

    author="Paul Handly",
    author_email="ph@betaworks.com",
)
