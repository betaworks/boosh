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
    assert(len(config.groups) == 0)
