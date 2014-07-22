boosh
=====

Betaworks Shell -> bwsh -> BOOSH!

I know, it's bad.

Installation
------------
```
pip install -e git+https://github.com/betaworks/boosh.git#egg=boosh
```

benv
====
benv (improved name TBD) will load up AWS credentials stored in the `~/.aws/config` file

Usage
-----

### Load AWS credentialks into the environment
```
$ benv betahack
```

### Remove AWS credentials from the environment
```
$ benv clear
```

### Run one command with AWS credentials in the environment
```
$ benv betahack packer build
```
