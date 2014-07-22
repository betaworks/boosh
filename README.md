boosh
=====

Betaworks Shell -> bwsh -> BOOSH!

I know, it's bad.

Installation
------------
```
pip install git+ssh://git@github.com/betaworks/boosh.git#egg=boosh
```

benv
====
benv (improved name TBD) will load up AWS credentials stored in the `~/.aws/config` file

Setup
-----
 1. Ensure you have AWSCLI configured happily in `~/.aws/config`.  Verify with `aws --profile=<profile_name> ec2 describe-instances`:

    ```ini
    [default]
    
    [profile betahack]
    region = us-east-1
    aws_access_key_id = AKIAGARBLEGARBLE
    aws_secret_access_key = nKNRrTRFrcJOuh5KUtJHFaHEZNGgym0h
    
    [profile ...]
    ```
 2. Add the following to your `.bash_profile`:

    ```
    # Load up the benv shell function
    . /usr/local/bin/benv.sh
    ```

 3. Profit!

Usage
-----

#### Load AWS credentials into the environment
```
$ benv betahack
```

#### Remove AWS credentials from the environment
```
$ benv clear
```

#### Run one command with AWS credentials in the environment
```
$ benv betahack packer build
```
