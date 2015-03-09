import ConfigParser
import json
import logging
import os
import subprocess
import sys

import botocore.session

CACHE_FILE = '~/.cache/boosh/hosts'
BOOSH_CONFIG = '~/.aws/boosh'

logger = logging.getLogger('boosh.ssh')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

if 'BOOSH_DEBUG' in os.environ:
    logger.setLevel(logging.DEBUG)


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

    def as_ssh_command(self, instance):
        ssh_options, ssh_command = [], []

        # Set extra options first
        if self.ssh_options:
            ssh_options.extend(self.ssh_options.split(' '))

        ssh_options.append("-p%s" % self.port)

        if self.user:
            ssh_options.extend(('-l', self.user))

        if self.identity_file:
            identity_file_path = os.path.expanduser(self.identity_file)
            ssh_options.extend(('-i', identity_file_path,
                                '-oIdentitiesOnly=yes'))

        if self.use_netcat:
            ssh_options.extend(('-NT', '-oExitOnForwardFailure',
                                '-oClearAllForwardings'))
        else:
            ssh_options.extend(('-W', '%s:%d' % (instance.private_ip_address,
                                                 22)))

        if self.use_netcat:
            ssh_command = (self.netcat_path, instance.private_ip_address,
                           '22')

        ssh_args = ssh_options + [self.hostname] + ssh_command

        p = subprocess.Popen(['/usr/bin/ssh'] + ssh_args, stdin=sys.stdin,
                             stderr=sys.stderr)

        return p


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


class Instance(object):
    """Subset of EC2 instance properties needed for remote connection."""
    def __init__(self, id, profile_name, region, private_ip_address,
                 public_ip_address=None, vpc_id=None, subnet_id=None):

        self.id = id
        self.private_ip_address = private_ip_address
        self.public_ip_address = public_ip_address
        self.profile_name = profile_name
        self.region = region
        self.vpc_id = vpc_id
        self.subnet_id = subnet_id

    @classmethod
    def from_instance_data(cls, data, profile_name, region):
        """Return an Instance given a raw EC2 DescribeInstances dictionary."""

        return cls(
            id=data.get('InstanceId'),
            profile_name=profile_name,
            region=region,
            private_ip_address=data.get('PrivateIpAddress'),
            public_ip_address=data.get('PublicIpAddress', None),
            subnet_id=data.get('SubnetId', None),
            vpc_id=data.get('VpcId', None),
        )

    @classmethod
    def from_cache_line(cls, line):
        id, data_json = line.split(' ', 1)
        data = json.loads(data_json)
        return cls(id=id, **data)

    def as_cache_line(self):
        keys = (
            'private_ip_address',
            'profile_name',
            'public_ip_address',
            'region',
            'subnet_id',
            'vpc_id',
        )
        data = {k: self.__dict__[k] for k in keys if self.__dict__[k]}
        data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return '%s %s' % (self.id, data_json)

    def __repr__(self):
        return "Instance('%s', ...)" % self.id

    @property
    def is_classic(self):
        if self.vpc_id:
            return False
        else:
            return True


def find_instance(instance_id, config_profiles):
    """Search through all AWS profiles and regions for an instance."""

    profiles_session = botocore.session.get_session()

    for profile in profiles_session.available_profiles:
        if profile in ['_path']:
            continue

        # Re-using the same session doesn't work
        session = botocore.session.get_session()
        session.profile = profile

        # Prefer regions listed in the profile
        regions = None
        if profile in config_profiles:
            regions = config_profiles[profile].regions

        if not regions:
            region = session.get_config_variable('region')
            if not region:
                continue
            else:
                regions = [region]

        ec2 = session.get_service('ec2')
        operation = ec2.get_operation('DescribeInstances')
        for region in regions:
            logger.debug("connecting to region '%s' with AWS profile '%s'...",
                         region, profile)
            endpoint = ec2.get_endpoint(region)
            try:
                resp, data = operation.call(
                    endpoint,
                    instance_ids=[instance_id],
                )
            except botocore.exceptions.NoCredentialsError:
                break

            if resp.status_code == 200:
                for reservation in data['Reservations']:
                    for instance_data in reservation['Instances']:
                        return Instance.from_instance_data(instance_data,
                                                           profile, region)
            else:
                continue

    return None


def cache_lookup(hostname, file_path):
    cache_file_path = os.path.abspath(os.path.expanduser(file_path))
    try:
        with open(cache_file_path, 'r') as cf:
            for line in cf:
                if line.startswith('#'):
                    continue
                elif line.startswith(hostname):
                    return Instance.from_cache_line(line.rstrip())

                continue
    except IOError:
        pass

    return None


def find_group_match(instance, groups):
    """Find a group match for the instance."""

    fields_map = {
        'profile': instance.profile_name,
        'region': instance.region,
        'ec2_classic': instance.is_classic,
        'vpc_id': instance.vpc_id,
        'subnet_id': instance.subnet_id,
    }

    for group in groups:
        for field, instance_prop in fields_map.iteritems():
            if field in group:
                if group[field] != instance_prop:
                    break

        else:
            return group

    return False


def find_gateway(instance, config):
    """Find an appropriate gateway."""

    group_name = find_group_match(instance, config.groups)
    if group_name:
        gateway_name = config.groups[group_name].gateway
        return config.gateways[gateway_name]

    if instance.profile_name in config.gateways:
        return config.gateways[instance.profile_name]

    return None


def cache_append(line, file_path):
    cache_file_path = os.path.abspath(os.path.expanduser(file_path))

    def _open_and_write():
        with open(cache_file_path, 'a+') as cf:
            cf.write(line + '\n')

    try:
        _open_and_write()
    except IOError:
        cache_dir = os.path.dirname(cache_file_path)
        os.makedirs(cache_dir)
        _open_and_write()


def main():
    hostname = sys.argv[1]
    if len(sys.argv) > 2:
        port = sys.argv[2]
    else:
        port = '22'

    cache_file = os.environ.get('BOOSH_HOSTS_FILE', CACHE_FILE)

    with open(os.path.expanduser(BOOSH_CONFIG), 'r') as config_file:
        config = BooshConfig(config_file)

    instance = None
    cache_result = cache_lookup(hostname, cache_file)
    if cache_result:
        instance = cache_result
    if not cache_result:
        search_result = find_instance(hostname, config.profiles)
        if search_result:
            instance = search_result
            cache_append(instance.as_cache_line(), cache_file)

    if not instance:
        logger.error("no instance found with instance ID %s, exiting.",
                     hostname)
        sys.exit(1)

    gateway = find_gateway(instance, config)
    if gateway:
        logger.info("connecting through gateway '%s'...", gateway.name)
        ssh_proc = gateway.as_ssh_command(instance)
        ssh_proc.communicate()
    elif instance.public_ip_address:
        # Connect "directly" via netcat
        logger.info("connecting directly to %s:%s...",
                    instance.public_ip_address, port)
        ssh_proc = subprocess.Popen(
            ('/usr/bin/nc', instance.public_ip_address, port),
            stdin=sys.stdin,
            stdout=sys.stdout,
        )
        ssh_proc.communicate()
    else:
        logger.error("neither a public IP nor a gateway was available for "
                     "this host, exiting.")
        sys.exit(1)
