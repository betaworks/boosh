from boosh.ssh import Instance


def test_cache_dump():
    src_instance = Instance(
        id='i-10ca9425',
        profile_name='testing',
        region='us-west-1',
        private_ip_address='127.0.0.1',
        public_ip_address='10.0.0.1',
        vpc_id='vpc-bbe848de',
        subnet_id='subnet-b5bc10ec',
    )
    cache_line = ('i-10ca9425 {"private_ip_address":"127.0.0.1",'
                  '"profile_name":"testing",'
                  '"public_ip_address":"10.0.0.1",'
                  '"region":"us-west-1",'
                  '"subnet_id":"subnet-b5bc10ec",'
                  '"vpc_id":"vpc-bbe848de"}')

    assert src_instance.as_cache_line() == cache_line


def test_cache_load():
    src_instance = Instance(
        id='i-10ca9425',
        profile_name='testing',
        region='us-west-1',
        private_ip_address='127.0.0.1',
        public_ip_address='10.0.0.1',
        vpc_id='vpc-bbe848de',
        subnet_id='subnet-b5bc10ec',
    )
    cache_line = ('i-10ca9425 {"private_ip_address":"127.0.0.1",'
                  '"profile_name":"testing",'
                  '"public_ip_address":"10.0.0.1",'
                  '"region":"us-west-1",'
                  '"subnet_id":"subnet-b5bc10ec",'
                  '"vpc_id":"vpc-bbe848de"}')

    dst_instance = Instance.from_cache_line(cache_line)
    assert src_instance.__dict__ == dst_instance.__dict__
