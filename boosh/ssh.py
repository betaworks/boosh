import json
import logging
import os
import subprocess
import sys

import botocore.exceptions
import botocore.session

import boosh


DEFAULT_CACHE_FILE = '~/.cache/boosh/hosts'
DEFAULT_BOOSH_CONFIG = '~/.aws/boosh'

logger = logging.getLogger('boosh')


class Instance(object):
    """
    Subset of EC2 instance properties needed for remote connection.
    """
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
        """
        Return an Instance given a raw EC2 DescribeInstances dictionary.
        """
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
    """
    Search through all AWS profiles and regions for an instance.
    """
    profiles_session = botocore.session.get_session()

    for profile in profiles_session.available_profiles:
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

        for region in regions:
            logger.debug("connecting to region '%s' with AWS profile '%s'...",
                         region, profile)
            ec2 = session.create_client('ec2', region)

            try:
                resp = ec2.describe_instances(InstanceIds=[instance_id])
            except botocore.exceptions.NoCredentialsError:
                break
            except botocore.exceptions.ClientError:
                continue

            for reservation in resp['Reservations']:
                for instance_data in reservation['Instances']:
                    return Instance.from_instance_data(instance_data, profile,
                                                       region)

    return None


def cache_lookup(key, cache_file):
    """
    Find a cache line matching the key and return the first match.
    """
    for line in cache_file:
        if line.startswith('#'):
            continue
        elif line.startswith(key):
            return Instance.from_cache_line(line.rstrip())

        continue

    return None


def find_group_match(instance, groups):
    """
    Loop through defined groups and return the first match for the instance.
    """
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
    """
    Find a gateway that matches the instance by name or through grouping.
    """
    group_name = find_group_match(instance, config.groups)
    if group_name:
        gateway_name = config.groups[group_name].gateway
        return config.gateways[gateway_name]

    if instance.profile_name in config.gateways:
        return config.gateways[instance.profile_name]

    return None


def get_gateway_process(instance, port, gateway):
    """
    Create a subprocess to reach an instance through a gateway.
    """
    ssh_options, ssh_command = [], []

    # Set extra options first
    if gateway.ssh_options:
        ssh_options.extend(gateway.ssh_options.split(' '))

    ssh_options.append("-p%s" % gateway.port)

    if gateway.user:
        ssh_options.extend(('-l', gateway.user))

    if gateway.identity_file:
        identity_file_path = os.path.expanduser(gateway.identity_file)
        ssh_options.extend(('-i', identity_file_path, '-oIdentitiesOnly=yes'))

    if gateway.use_netcat:
        ssh_options.extend(('-NT', '-oExitOnForwardFailure',
                            '-oClearAllForwardings'))
    else:
        ssh_options.extend(('-W', '%s:%s' % (instance.private_ip_address,
                                             port)))

    if gateway.use_netcat:
        ssh_command = (gateway.netcat_path, instance.private_ip_address, port)

    ssh_args = ssh_options + [gateway.hostname] + ssh_command

    return subprocess.Popen(['/usr/bin/ssh'] + ssh_args, stdin=sys.stdin,
                            stderr=sys.stderr)


def get_direct_process(instance, port):
    """
    Create a subprocess to reach an instance directly.
    """
    hostname = instance.public_ip_address

    return subprocess.Popen(
        ('/usr/bin/nc', hostname, port),
        stdin=sys.stdin,
        stdout=sys.stdout,
    )


def main():
    # Set up logging for interactive use
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if 'BOOSH_DEBUG' in os.environ:
        logger.setLevel(logging.DEBUG)

    cache_path = os.environ.get('BOOSH_HOSTS_FILE', DEFAULT_CACHE_FILE)
    cache_path = os.path.abspath(os.path.expanduser(cache_path))
    config_path = os.environ.get('BOOSH_CONFIG', DEFAULT_BOOSH_CONFIG)
    config_path = os.path.abspath(os.path.expanduser(config_path))

    hostname = sys.argv[1]
    if len(sys.argv) > 2:
        port = sys.argv[2]
    else:
        port = '22'

    with open(config_path, 'r') as config_file:
        config = boosh.Config(config_file)

    try:
        cache_file = open(cache_path, 'a+')
    except IOError:
        os.makedirs(os.path.dirname(cache_path))
        cache_file = open(cache_path, 'a+')

    # Search the local cache first, then fall back to EC2
    instance = None
    cache_result = cache_lookup(hostname, cache_file)
    if cache_result:
        instance = cache_result
    else:
        find_result = find_instance(hostname, config.profiles)
        if find_result:
            instance = find_result
            cache_file.write(instance.as_cache_line() + '\n')

    cache_file.close()

    if not instance:
        logger.error("no instance found with instance ID %s, exiting.",
                     hostname)
        sys.exit(1)

    gateway = find_gateway(instance, config)
    if gateway:
        logger.info("connecting through gateway '%s'...", gateway.name)
        ssh_proc = get_gateway_process(instance, port, gateway)
        ssh_proc.communicate()
    elif instance.public_ip_address:
        # Connect "directly" via netcat
        logger.info("connecting directly to %s:%s...",
                    instance.public_ip_address, port)
        ssh_proc = get_direct_process(instance, port)
        ssh_proc.communicate()
    else:
        logger.error("neither a public IP nor a gateway was available for "
                     "this host, exiting.")
        sys.exit(1)
