from setuptools import setup, find_packages


setup(
    name='boosh',
    version='0.0.2',
    packages=find_packages(),
    install_requires=[
        'botocore',
    ],
    entry_points={
        'console_scripts': [
            'boosh_proxy = boosh.ssh:main',
        ],
    },
    author="Paul Handly",
    author_email="ph@betaworks.com",
)
