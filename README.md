boosh
=====

Betaworks Shell -> bwsh -> BOOSH!

I know, it's bad.

### Installation ###
```
pip install git+ssh://git@github.com/betaworks/boosh.git#egg=boosh
```

## boosh ##
SSH directly to EC2 instances identified only by their instance ID -- across
multiple accounts!

### Setup ###
 1. Ensure you have AWSCLI configured happily in `~/.aws/config`.  Verify with 
    `aws --profile=<profile_name> ec2 describe-instances`:

    ```ini
    [default]
    
    [profile betahack]
    region = us-east-1
    aws_access_key_id = AKIAGARBLEGARBLE
    aws_secret_access_key = nKNRrTRFrcJOuh5KUtJHFaHEZNGgym0h
    
    [profile ...]
    ```
 2. Create an SSH config stanza to invoke boosh when the hostname looks like an
    EC2 instance ID:

    ```
    ...
    Host i-*
        ProxyCommand boosh_proxy %h %p
    ```
 3. You should be good to go:

    ```bash
    $ ssh i-dec56b07
    ```

If you have any trouble, check the cache file (`~/.cache/boosh/hosts`) to see
what boosh thinks it knows about the EC2 instance in question.  Adding `-vvvv`
to SSH is also a handy trick.
