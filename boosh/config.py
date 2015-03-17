import ConfigParser
import logging

from boosh.exceptions import MissingOptionError

logger = logging.getLogger(__name__)


class ConfigBase(object):
    """
    Base class for configurable objects.

    Interesting properties:
     - defaults, a dict of any config keys that have default values
     - bool_keys, a list of keys whose values should be treated as boolean
     - multistring_keys, a list of keys whose values are comma-delimited
       strings
     - string_keys, a list of keys whose values are plain strings
    """
    defaults = {}
    bool_keys = ()
    multistring_keys = ()
    string_keys = ()

    def _read_config_items(self, section, parser):
        for key in self.string_keys:
            self.__dict__[key] = parser.get(section, key, vars=self.defaults)

        for key in self.bool_keys:
            try:
                self.__dict__[key] = parser.getboolean(section, key)
            except ConfigParser.NoOptionError:
                self.__dict__[key] = self.defaults[key]

        for key in self.multistring_keys:
            raw_value = parser.get(section, key, vars=self.defaults)
            self.__dict__[key] = [i.strip() for i in raw_value.split(',')]

    def __init__(self, name, section, parser):
        self.name = name

        try:
            self._read_config_items(section, parser)
        except ConfigParser.NoOptionError, e:
            raise MissingOptionError(e)


class ConfigGroup(ConfigBase):
    """
    Groups bind a subset of instances to a Gateway.
    """
    defaults = {
        'ec2_classic': True,
        'profile': None,
        'region': None,
        'subnet_id': None,
        'vpc_id': None,
    }
    bool_keys = (
        'ec2_classic',
    )
    string_keys = (
        'profile'
        'region',
        'subnet_id',
        'vpc_id',
    )


class ConfigProfile(ConfigBase):
    """
    Profiles define additional attributes for an AWS Credential Profile.
    """
    multistring_keys = (
        'regions',
    )


class ConfigGateway(ConfigBase):
    """
    Gateways define SSH servers through which we may reach instances.
    """
    defaults = {
        'port': '22',
        'user': None,
        'use_netcat': False,
        'netcat_path': '/usr/bin/nc',
        'identity_file': None,
        'ssh_options': None,
    }
    bool_keys = (
        'use_netcat',
    )
    string_keys = (
        'port',
        'hostname',
        'user',
        'netcat_path',
        'identity_file',
        'ssh_options',
    )


class Config(object):
    """
    Reads an ini-style config file to build dicts of configurable objects.
    """
    config_class_map = {
        'gateway': ConfigGateway,
        'profile': ConfigProfile,
        'group': ConfigGroup,
    }

    def __init__(self, config_file):
        self._parser = ConfigParser.SafeConfigParser()
        self._parser.readfp(config_file)

        self.gateways, self.profiles, self.groups = {}, {}, {}
        for section in self._parser.sections():
            try:
                kind, name = section.split(' ')
            except ValueError:
                logger.warning('skipping bad section name "%s"...', section)
                continue

            if (kind in self.config_class_map) and name:
                config_dict = getattr(self, kind + 's')
                config_class = self.config_class_map[kind]
                config_dict[name] = config_class(name, section, self._parser)
            else:
                logger.warning('skipping unknown section type "%s"...', kind)
                continue
