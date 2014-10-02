import ConfigParser
import botocore.session
import click
import json
import os
import subprocess
import sys

CACHE_FILE = '~/.cache/boosh/hosts'
BOOSH_CONFIG = '~/.aws/boosh'


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
        kwargs = {
            'id': data['InstanceId'],
            'public_ip_address': data['PublicIpAddress'],
            'private_ip_address': data['PrivateIpAddress'],
            'profile_name': profile_name,
            'region': region,
        }
        if 'VpcId' in data:
            kwargs['subnet_id'] = data['SubnetId']
            kwargs['vpc_id'] = data['VpcId']

        return cls(**kwargs)

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


class Gateway(object):
    def __init__(self, name, hostname, port=22, user=None, use_netcat=False,
                 netcat_path='/usr/bin/nc', identity_file=None,
                 ssh_options=None):

        self.name = name
        self.hostname = hostname
        self.port = port
        self.user = user
        self.use_netcat = use_netcat
        self.netcat_path = netcat_path
        self.identity_file = identity_file
        self.ssh_options = ssh_options

    @classmethod
    def from_config_section(cls, name, parser):
        section = 'gateway ' + name
        keys = (
            'port',
            'user',
            'netcat_path',
            'identity_file',
            'ssh_options',
        )
        kwargs = {k: v for (k, v) in parser.items(section) if k in keys}

        if 'use_netcat' in parser.items(section):
            kwargs['use_netcat'] = parser.getboolean(section, 'use_netcat')

        kwargs['name'] = name
        kwargs['hostname'] = parser.get(section, 'hostname')

        return cls(**kwargs)

    def as_ssh_command(self, instance):
        ssh_options, ssh_command = [], []

        # Set extra options first
        if self.ssh_options:
            ssh_options.extend(self.ssh_options.split(' '))

        ssh_options.append("-p%d" % self.port)

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

    def __repr__(self):
        return "Gateway('%s', ...)" % self.name


def find_instance(instance_id, region):
    profiles_session = botocore.session.get_session()

    for profile in profiles_session.available_profiles:
        if profile in ['_path']:
            continue

        # Re-using the same session doesn't work
        session = botocore.session.get_session()
        session.profile = profile
        if region:
            profile_region = region
        else:
            profile_region = session.get_config_variable('region')

        if not profile_region:
            continue

        ec2 = session.get_service('ec2')
        operation = ec2.get_operation('DescribeInstances')
        endpoint = ec2.get_endpoint(profile_region)
        resp, data = operation.call(
            endpoint,
            instance_ids=[instance_id],
        )

        if resp.status_code == 200:
            for reservation in data['Reservations']:
                for instance_data in reservation['Instances']:
                    return Instance.from_instance_data(instance_data, profile,
                                                       profile_region)
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


def check_group_match(instance, group, config):
    section = 'group ' + group
    # Check profile
    try:
        group_profile = config.get(section, 'profile')
        if group_profile != instance.profile_name:
            return False
    except ConfigParser.NoOptionError:
        pass

    # Check region
    try:
        group_region = config.get(section, 'region')
        if group_region != instance.region:
            return False
    except ConfigParser.NoOptionError:
        pass

    # Check if EC2 "Classic" mode
    try:
        group_classic = config.getboolean(section, 'ec2_classic')
        if group_classic != instance.is_classic:
            return False
    except ConfigParser.NoOptionError:
        pass

    # Check VPC
    try:
        group_vpc_id = config.get(section, 'vpc_id')
        if group_vpc_id != instance.vpc_id:
            return False
    except ConfigParser.NoOptionError:
        pass

    # Check VPC Subnet
    try:
        group_subnet_id = config.get(section, 'subnet_id', None)
        if group_subnet_id != instance.subnet_id:
            return False
    except ConfigParser.NoOptionError:
        pass

    return True


def find_gateway(instance):
    """Find an appropriate gateway."""

    config = ConfigParser.SafeConfigParser()
    config.read(os.path.expanduser(BOOSH_CONFIG))

    group_names, gateway_names = [], []
    for section in config.sections():
        kind, name = section.split(' ', 1)
        if kind == 'group':
            group_names.append(name)
        elif kind == 'gateway':
            gateway_names.append(name)
        else:
            continue

    for name in group_names:
        result = check_group_match(instance, name, config)
        if result:
            break
    else:
        if instance.profile_name in gateway_names:
            return Gateway.from_config_section(instance.profile_name, config)

        return None

    gateway_name = config.get('group ' + name, 'gateway')
    return Gateway.from_config_section(gateway_name, config)


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


@click.command()
@click.argument('hostname')
@click.argument('port', default="22", required=False)
@click.option('--region', required=False)
def main(hostname, port, region):
    cache_file = os.environ.get('BOOSH_HOSTS_FILE', CACHE_FILE)

    cache_miss = False
    result = cache_lookup(hostname, cache_file)

    if not result:
        cache_miss = True
        result = find_instance(hostname, region)

    if result:
        instance = result
    else:
        print >> sys.stderr, "No instance found."
        sys.exit(1)

    if cache_miss:
        cache_append(instance.as_cache_line(), cache_file)

    gateway = find_gateway(instance)
    if gateway:
        # Connect through gateway
        ssh_proc = gateway.as_ssh_command(instance)
        ssh_proc.communicate()
    elif instance.public_ip_address:
        # Connect "directly" via netcat
        ssh_proc = subprocess.Popen(
            ('/usr/bin/nc', instance.public_ip_address, port),
            stdin=sys.stdin,
            stdout=sys.stdout,
        )
        ssh_proc.communicate()
    else:
        print >> sys.stderr, "No public IP available."
        sys.exit(1)

if __name__ == '__main__':
    main()
