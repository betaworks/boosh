import pytest

import boosh

from six import StringIO
from six.moves import configparser

from boosh.exceptions import MissingOptionError


def test_config():
    parser = configparser.RawConfigParser()
    parser.add_section('gateway foo')
    parser.set('gateway foo', 'hostname', "foo.example.org")
    parser.set('gateway foo', 'user', "jsmith")

    parser.add_section('gateway bar')
    parser.set('gateway bar', 'hostname', "bar.example.org")
    parser.set('gateway bar', 'user', "alice")

    parser.add_section('profile foo')
    parser.set('profile foo', 'regions', "us-west-1, us-east-1")

    parser.add_section('profile bar')
    parser.set('profile bar', 'regions', "us-west-2, sa-east-1")

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)

    config = boosh.Config(buf)
    assert len(config.profiles) == 2
    assert len(config.gateways) == 2


def test_config_boolean():
    parser = configparser.RawConfigParser()

    parser.add_section('gateway testing_true')
    parser.set('gateway testing_true', 'hostname', "foo.example.org")
    parser.set('gateway testing_true', 'use_netcat', "true")

    parser.add_section('gateway testing_false')
    parser.set('gateway testing_false', 'hostname', "foo.example.org")
    parser.set('gateway testing_false', 'use_netcat', "false")

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)
    config = boosh.Config(buf)

    assert config.gateways['testing_true'].use_netcat == True
    assert config.gateways['testing_false'].use_netcat == False


def test_config_string():
    parser = configparser.RawConfigParser()

    parser.add_section('gateway testing')
    parser.set('gateway testing', 'hostname', "foo.example.org")

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)
    config = boosh.Config(buf)

    assert config.gateways['testing'].hostname == "foo.example.org"


def test_config_multistring():
    parser = configparser.RawConfigParser()

    parser.add_section('profile testing')
    parser.set('profile testing', 'regions', "us-west-1, us-east-1")

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)
    config = boosh.Config(buf)

    profile = config.profiles['testing']
    assert profile.regions == ['us-west-1', 'us-east-1']


def test_config_missing_multistring():
    parser = configparser.RawConfigParser()

    parser.add_section('profile testing')

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)
    with pytest.raises(MissingOptionError):
        boosh.Config(buf)


def test_config_missing_string():
    parser = configparser.RawConfigParser()

    parser.add_section('gateway testing')

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)
    with pytest.raises(MissingOptionError):
        boosh.Config(buf)

def test_config_missing_multistring():
    parser = configparser.RawConfigParser()

    parser.add_section('profile testing')

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)
    with pytest.raises(MissingOptionError):
        boosh.Config(buf)


def test_bad_section_names():
    parser = configparser.RawConfigParser()
    parser.add_section(' profile')
    parser.add_section('profile ')
    parser.add_section('testing section')
    parser.add_section(' ')

    buf = StringIO()
    parser.write(buf)
    buf.seek(0)

    config = boosh.Config(buf)
    assert len(config.profiles) == 0
    assert len(config.gateways) == 0
    assert len(config.groups) == 0
