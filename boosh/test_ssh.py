import ConfigParser
import StringIO

from boosh.ssh import BooshConfig


def test_config():
    parser = ConfigParser.RawConfigParser()
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

    buf = StringIO.StringIO()
    parser.write(buf)
    buf.seek(0)

    config = BooshConfig(buf)
    assert(len(config.profiles) == 2)
    assert(len(config.gateways) == 2)


def test_config_boolean():
    parser = ConfigParser.RawConfigParser()

    parser.add_section('gateway testing_true')
    parser.set('gateway testing_true', 'hostname', "foo.example.org")
    parser.set('gateway testing_true', 'use_netcat', "true")

    parser.add_section('gateway testing_false')
    parser.set('gateway testing_false', 'hostname', "foo.example.org")
    parser.set('gateway testing_false', 'use_netcat', "false")

    buf = StringIO.StringIO()
    parser.write(buf)
    buf.seek(0)
    config = BooshConfig(buf)

    assert(config.gateways['testing_true'].use_netcat == True)
    assert(config.gateways['testing_false'].use_netcat == False)


def test_config_string():
    parser = ConfigParser.RawConfigParser()

    parser.add_section('gateway testing')
    parser.set('gateway testing', 'hostname', "foo.example.org")

    buf = StringIO.StringIO()
    parser.write(buf)
    buf.seek(0)
    config = BooshConfig(buf)

    assert(config.gateways['testing'].hostname == "foo.example.org")


def test_config_multistring():
    parser = ConfigParser.RawConfigParser()

    parser.add_section('profile testing')
    parser.set('profile testing', 'regions', "us-west-1, us-east-1")

    buf = StringIO.StringIO()
    parser.write(buf)
    buf.seek(0)
    config = BooshConfig(buf)

    profile = config.profiles['testing']
    assert(profile.regions == ['us-west-1', 'us-east-1'])
