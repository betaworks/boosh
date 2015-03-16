import ConfigParser


class ConfigBase(object):
    defaults = {}
    bool_keys = ()
    multistring_keys = ()
    string_keys = ()

    def __init__(self, name, section, parser):
        self.name = name

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


class ConfigGroup(ConfigBase):
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
    multistring_keys = (
        'regions',
    )


class ConfigGateway(ConfigBase):
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


class BooshConfig(object):
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
            kind, name = section.split(' ')

            if kind in self.config_class_map:
                config_dict = getattr(self, kind + 's')
                config_class = self.config_class_map[kind]
                config_dict[name] = config_class(name, section, self._parser)
