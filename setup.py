from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ["-v", "-epy"]
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import tox
        tox.cmdline(self.test_args)

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
    tests_require=['tox'],
    cmdclass={"test": Tox},
    author="Paul Handly",
    author_email="ph@betaworks.com",
)
