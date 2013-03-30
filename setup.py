#!/usr/bin/python -t

from distutils.core import setup

version = '0.65'

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
    scripts = [ 'bin/stem', 'bin/mount_stalk_linux' ],
    packages = ['stalk', 'stalk.rw' ],
    data_files = [('/sbin',['bin/mount.fuse.Stalk']),
       ('/usr/share/doc/' + fullname, ['docs/README.md']),
        ('/usr/share/man/man1/', ['docs/stem.1.gz']),
        ('/etc/stalk/examples', ['config/examples/internal_yum',
        'config/examples/ssh-known-hosts.read-only'])],
    description = 'rsync + fuse',
    long_description = 'fuse + rsync + plugin',
    classifiers = classifiers,
)
