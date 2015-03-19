boosh
=====
An SSH ProxyCommand script to help you reach your Amazon EC2 instances by ID. Boosh supports multiple AWS accounts, SSH gateways (bastion hosts), VPC subnets, and multiple EC2 regions.

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
Boosh assumes your AWS credentials are set up for use with the AWS SDKs. If they're not, or you're unsure, the easiest way to get started is by setting up the excellent [AWS CLI](https://aws.amazon.com/cli/).
 0. Install AWS CLI with `pip` or your package manager of choice:

    ```
    $ pip install awscli
    ```
 0. Configure AWS CLI with the interactive prompts. If you're working with multiple accounts, use the optional `--profile=<name>` flag to give this set of credentials a name:

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
 0. You're done! AWS CLI is working, and now we can make use of these credentials in Boosh - once SSH is configured.

### SSH Configuration ###
 0. Once AWS Credentials have been configured, we need to tell SSH to run boosh when trying to reach an EC2 instance by ID. Add the following stanza to your `~/.ssh/config` file, replacing `YOUR-SSH-USERNAME` with the username you typically use on your EC2 instances:
 
    ```
    Host i-*
        User YOUR-SSH-USERNAME
        ProxyCommand boosh_proxy %h %p
    ```
 0. You're all set! If your EC2 instances are reachable directly over SSH, no further configuration is required. Otherwise, you'll need to set up a gateway - see the Advanced Configuration section below.

## Advanced Setup ##
Coming soon!

## Troubleshooting ##
If you have any trouble, check the cache file (`~/.cache/boosh/hosts`) to see
what boosh thinks it knows about the EC2 instance in question. Adding `-vvvv`
to SSH is also a handy trick.
