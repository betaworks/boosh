import sys

import botocore.session
import click


@click.command()
@click.option('--profile')
def main(profile):
    """Grab credentials from the AWS config and stick em in the environment."""

    sess = botocore.session.get_session()
    if profile not in sess.available_profiles:
        print >> sys.stderr, "Please select a properly configured profile."
        sys.exit(1)

    sess.profile = profile
    credentials = sess.get_credentials()
    print "AWS_ACCESS_KEY_ID=%s" % credentials.access_key, "AWS_SECRET_ACCESS_KEY=%s" % credentials.secret_key

if __name__ == '__main__':
    main()
