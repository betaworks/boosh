boosh
=====
An SSH ProxyCommand script to help you reach your Amazon EC2 instances by ID.
Boosh supports multiple AWS accounts, SSH gateways (a.k.a. [bastion
hosts](https://en.wikipedia.org/wiki/Bastion_host)), VPC subnets, and multiple
EC2 regions.
## Example Usage ##
```
$ ssh i-0e28ece1
[INFO] boosh: connecting through gateway 'example-west'...
Last login: Thu Feb 12 21:44:35 2015 from 128.177.165.170
jsmith@west-0e28ece1:~$
```
It's that easy!
## Installation ##
```
$ pip install git+ssh://git@github.com/betaworks/boosh.git#egg=boosh
```
## Simple Setup ##
### AWS Credentials ###
Boosh assumes your AWS credentials are set up for use with the AWS SDKs. If
they're not, or you're unsure, the easiest way to get started is by setting up
the excellent [AWS CLI](https://aws.amazon.com/cli/).
 0. Install AWS CLI with `pip` or your package manager of choice:

    ```
    $ pip install awscli
    ```
 0. Configure AWS CLI with the interactive prompts. If you're working with
 multiple accounts, use the optional `--profile=<name>` flag to give this set
 of credentials a name:

    ```
    $ aws configure --profile=example
    AWS Access Key ID [None]: AKIAGARBLEGARBLE
    AWS Secret Access Key [None]: nKNRrTRFrcJOuh5KUtJHFaHEZNGgym0h
    Default region name [None]: us-east-1
    Default output format [None]: 
    $ 
    ```
 0. Test out AWS CLI by listing your access permissions:

   ```
   $ aws --profile=example iam get-user
   {
        "User": {
            "UserName": "jsmith",
            "PasswordLastUsed": "2014-11-18T19:11:09Z",
            "CreateDate": "2014-01-28T16:08:19Z",
            "UserId": "AKIAGARBLEGARBLE",
            "Path": "/",
            "Arn": "arn:aws:iam::64111877890:user/jsmith"
        }
    }
    ```
 0. You're done! AWS CLI is working, and now we can make use of these
 credentials in Boosh - once SSH is configured.

### SSH Configuration ###
 0. Once AWS Credentials have been configured, we need to tell SSH to run boosh
 when trying to reach an EC2 instance by ID. Add the following stanza to your
 `~/.ssh/config` file, replacing `YOUR-SSH-USERNAME` with the username you
 typically use on your EC2 instances:
 
    ```
    Host i-*
        User YOUR-SSH-USERNAME
        ProxyCommand boosh_proxy %h %p
    ```
 0. You're all set! If your EC2 instances are reachable directly over SSH, no
 further configuration is required. Otherwise, you'll need to set up a gateway
 - see the Advanced Configuration section below.

## Advanced Setup ##
If you need to make use of gateways, multiple regions for a given credential
profile, or use specific gateways for sub-sets of EC2 hosts, you'll need to
create a Boosh configuration file.

By default, Boosh will look for a config file in `~/.aws/boosh`, and may be
populated with one or more of the following configurables:

### Gateways ###
SSH Gateways allow you to relay an SSH connection through an intermediary
server, which is tremendously helpful when the EC2 node you're trying to reach
isn't exposing a publicly-accessible SSH server. If the name of a gateway
matches the name of an AWS credential profile, it will be used for all EC2
instances reachable under that profile.

A sample gateway configuration:
```ini
[gateway example]
hostname = bastion.ec2.example.org
```

#### Gateway Parameters ###
 - *hostname* (required) hostname or IP to connect to
 - *port* (default: `22`) SSH port of the gateway host
 - *user* (default: local username) SSH user on the gateway host
 - *use_netcat* (boolean, default: `false`) When false, uses the `-W`
   behavior added in OpenSSH 5.4. If the gateway host is running an earlier
   release of OpenSSH, set this to true and netcat will be used instead.
 - *netcat_path* (default: `/usr/bin/nc`) Only used when `use_netcat=true`,
   defines the path to the netcat binary on the gateway host
 - *identity_file* Defines the path to an SSH private key file
 - *ssh_options* additional command-line options to be added to the outer
   (gateway) connection

### Profiles ####
AWS Credential profiles may be configured with a default region, but sometimes
you want to use the same credentials in multiple regions. Boosh allows you
to specify a list of regions for a profile.

A sample profile configuration:
```ini
[profile example]
regions = us-east-1, us-west-1
```

#### Profile Parameters ####
- *regions* (required) a comma-separated list of EC2 regions to search through,
  instead of the region specified in `~/.aws/config`

### Groups ###
In complex AWS environments, a single gateway won't be enough to reach all EC2
instances in an account. Groups allow you to specify matching conditions for
instances, and map them to a configured Gateway. The first group that matches
an instance will be used, so they should be ordered from most-specific to
least-specific.

A sample group and gateway configuration:
```ini
# Use one gateway for a specific VPC, and another for everything else
[gateway example-vpc]
hostname = bastion.vpc.example.org

[gateway example-classic]
hostname = bastion.example.org

[group example-vpc]
profile = example
gateway = example-vpc
vpc_id = vpc-bbe848de

[group example-classic]
profile = example
gateway = example-classic
```

#### Group Parameters ###
 - *gateway* (required) the name of a gateway configuration
 - *profile* name of the credential profile to use
 - *ec2_classic* (boolean) match instances in EC2 classic networking
 - *region* match instances in a specific region
 - *subnet_id* match instances in a specific subnet
 - *vpc_id* match instances in a specific VPC

### Environment Variables ###
There are several environment variables you may set to control runtime
behavior:

 - *BOOSH_DEBUG* When set, increases stderr logging verbosity. Defaults to unset.
 - *BOOSH_HOSTS_FILE* Where to store cached EC2 instance data. Defaults to
   `~/.cache/boosh/hosts`
 - *BOOSH_CONFIG* config file location. Defaults to `~/.aws/boosh`

## Troubleshooting ##
If you have any trouble, check the cache file (`~/.cache/boosh/hosts`) to see
what boosh thinks it knows about the EC2 instance in question. Adding `-vvvv`
to SSH is also a handy trick.

Setting the `BOOSH_DEBUG` environment variable will display debug logging
output:

```
$ BOOSH_DEBUG=1 ssh i-0e28ece1
[DEBUG] boosh: connecting to region 'us-east-1' with AWS profile 'example-global'...
[DEBUG] boosh: connecting to region 'us-west-2' with AWS profile 'example-global'...
[INFO] boosh: connecting through gateway 'example-global'...
(remote-0e28ece1 ~)$
```

Adding `-v` or `-vvv` to your SSH command will increase the verbosity of the
"outer" (non-gateway) SSH connection, and is helpful when troubleshooting
authentication errors.
