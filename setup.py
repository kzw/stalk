#!/usr/bin/python -t

from distutils.core import setup

version = '0.70'

classifiers = [
    "Topic :: Filesystem",
    "Programming Language :: Python",
]

_name = 'stalk'
fullname = _name + '-' + version

setup(
    name = _name,
    version = version,
    url = 'http://githubs.com/kzw',
    author = 'K Z Win',
    author_email = 'kzw@happyw.info',
    license = 'GPL',
    scripts = [ 'bin/stem', 'bin/mount_stalk' ],
    packages = ['stalk', 'stalk.rw' ],
    data_files = [('/sbin',['bin/mount.fuse.Stalk']),
       ('/usr/share/doc/' + fullname, ['README.md']),
        ('/usr/share/man/man1/', ['docs/stem.1.gz']),
        ('/etc/stalk/examples', ['config/examples/internal_yum',
        'config/examples/ssh-known-hosts.read-only'])],
    long_description = 'fuse + rsync + urllib + plugin',
    classifiers = classifiers,
)
