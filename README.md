# stalk  = fuse + rsync + urllib + plugins

*stalk* is a Python application that combines
[FUSE](http://fuse.sourceforge.net/) with user defined trigger actions for file
system operations. It supports two modes: read-only/pull mode and
read-write/push mode. The file-system is suitable for syncing across network
for files not changing very frequently but you want the changes made available
to the end-user quickly.  It may not be suitable if you expect frequent changes
and the data to sync is very large but it should work well as a part of an
automation system where you want to simplify the life of your end users.

## read-only/pull mode

*Problem A:* have a small number of files in remote locations that you need
most up to date read access.

- solution 1: set up network file servers on remote locations and mount folders
  on local machines. 
- solution 2: use cron  to periodically sync remote files to local machines
- alternative solution: use *stalk* in read-only mode.  A file is fetched
  using rsync or urllib when there is a read request on it.
 
Things to note:

1. multiple files/multiple remote locations per mount point.
2. only 1 level of files in a mount folder in the read-only mode

## read-write/push mode + plugin

*Problem B:* have a local folder that you want to mirror to remote locations.
There is not a lot of write operations in the local folder but whenever some
write operations take place, sync should happen quickly.

- solution 1: set up a network file server on the local machine and have the
  remote machines mount a folder from the server
- solution 2: use cron to periodically sync the local folder to remote
  machines.
- alternative solution with *stalk* in read-write/push mode: no network traffic
  until some write operations take place in the folder.  When a write operation such
as deleting a file, appending to a file or creating a file takes place, the
folder is synced to remote locations using `rsyc -aH --delete` command.

The definition for `a lot of write operations` will vary with the usage and
the available bandwidth.


*Problem C:* After writing to a folder on the local machine, you always run
a very specific shell command with the folder as the final argument.

>Use *stalk* in read-write mode with the supplied ``command_plugin``;
writing to the folder will automatically trigger the command.

*Problem D:* You always do some other specific task after writing to a local
folder.

>Write a python plugin that does this very specific task; writing to the folder
will automatically trigger the plugin.

*Problem E:*  Problem B + Problem C

>see the example below in the next section for rsync + shell command

## usage

The behavior of a mounted folder is driven by the config file.  In a typical
installation, a few example config files will be installed under
`/etc/stalk/examples`. Here is the content of a config file for mounting a
read-only folder which contains a lone file `ssh-known-hosts`.

		[global]
		cachedir: /etc/ssh/cache/
		log: /var/log/stalk-ssh
		[DEFAULT]
		cachetime: 600
		[file1]
		name: ssh_known_hosts
		origin: https://ssh-known-hosts-server.example.com/ssh_known_hosts

In the read-only mode, `global` and `DEFAULT` sections are optional.  In the
`global` section, the option `cachedir` specifies a cache-folder for the files
to persist after umounting.  Logging to syslog `USER` facility happens if
`/dev/log` on the system exists.  It will also log to the path given by the
`log` option in	`global` section.  The `cachetime` option specifies the time in
second a file will be cached before another rsync call is made.

The config file must contain one or more section describing how the remote
files are to be mounted.  The name of a section does not matter and each
section must contain `name` and `origin` options.  `name` option specifies the
name of the local file and `origin` specifies the remote location.  They will
be supplied to the rsync command as 

		rsync <origin> <cachedir>/<name>
if `origin` cannot be parsed as a url.  Otherwise, `origin` will be downloaded as

		urllib.urlretrieve(<origin>, <cachedir>/<name>)
Optionally a file section may contain `cachetime` option which will override
any value specified `DEFAULT` section.  If no `cachetime` is found for a file,
it is equivalent to a hardcoded minimum `cachetime` of 60 s.  This value should
be below the minimum time period you expect the remote file to change
regularly.  In other words, if the file on the remote server changes every hour,
the cachetime should be below 3600. It should also be well above the time it
takes to download or rsync the remote file; this obviously depends on the
network and the size of the file.     Assuming the config file is located at
`/etc/stalk/ssh.cf`, the command to mount is

		stem -r -c /etc/stalk/ssh.cf -a /etc/ssh/kh

In this example, `-a` flag lets other users access to the mount point, `-r`
specifies the read-only option, `-c` specifies the config file and the
`ssh-known-hosts` file will appear in the folder `/etc/ssh/kh`.  You can umount
any `fuse` mounted folder with a regular `umount` command.   In a typical
*open-ssh* installation, `ssh` command consults `/etc/ssh/ssh-knowns-hosts`
after `~/.ssh/known-hosts`; so one can provide such a system wide default
known-hosts file with a symlink:

		cd /etc/ssh ; ln -sf kh/ssh-known-hosts

An external mount helper for `linux` is also provided and the following is
equivalent to `stem` command above

		$ sudo mount /etc/ssh/kh

assuming you have the following line in `/etc/fstab`

		Stalk /etc/ssh/kh fuse.Stalk config=/etc/stalk/ssh.cf,allow_other,ro,noauto 1 2 

The following options in `/etc/fstab` option column are understood by *stalk*:
`ro`, `verbose`, `debug`, `config=<path>`, `allow_other`.  If `config` path is
omitted the default is `/etc/stalk.cf`.  Other options are equivalent to `-r`,
`-v`, `-d`, `-a` flags to `stem` command.  You can also put the standard `user` option in
`/etc/fstab` to allow non-root user to do the mounting but also see the section
for *FUSE* security.  If `noauto` is omitted, you should also have `_netdev`
option to prevent the system from mounting before network is available.

Below is an example config file for mounting in the read-write mode.  At the heart
of read-write mode is a file system mounted in a loopback mode with root and
mount folders.  The root folder is where the files live permanently.  The files
appear under mount-point only when it is mounted.  To get the benefits of
`stalk` all write operations should take place in the mounted folder.  The
`global` section has a required option `root` which specifies the path to this
folder.  If `timeout` is specified, the filesystem waits this many seconds
before it starts to do `rsync` or do a trigger action.  If `timeout` is
omitted, the default value 100s is used.  `log` option has the same meaning as
in the read-only mode above.

Either `plugin` or `target` may be absent in a config file but not both.  In
the example, both are present.  The `plugin` action takes place just before the
`rsync` action.

In the `plugin` section, `name` is the name of the plugin to be loaded.  Other
options in the section depend on the specific plugin being loaded.   In this
example, `command_plugin` requires `command` and switches to be supplied to the
`command`. In the example there is a single switch `-q` supplied to the
command; the exact key `o:` for the switch `-q` is not important except that
it should be different from keys for other switches.
In `target` section, you specify the remote locations to sync the `root`
folder.

		[global]
		timeout: 10
		root: /home/me/.internal_yum
		log: /home/me/fuse/logs/internal_yum

		[plugin]
		name: command_plugin
		command: createrepo
		o: -q

		[target]
		us-west-2: host1:/var/lib/nginx/yum
		us-east-1: hostb.example.org:/var/www/yum

The following line in `/etc/fstab`

		Stalk /home/me/internal_yum fuse.Stalk user,noauto 0 0
will let a regular user `me` mount it with the command

		mount ~/internal_yum
assuming the default config file `/etc/stalk.cf`  Any write operations in the
folder `internal_yum` will kick-off 

		createrepo -q ~/.internal_yum
and

		rsync -aH --delete ~/.internal_yum <target>
for each target. 

## security control in FUSE

The underlying FUSE system has security controls that can confuse the first
time user.  For example, let say a user has a non-fuse folder and its contents with
permission that allows other users read access.  If the user mounts a fuse
folder with the same mounted permission, other users (not even root) may not
have any read access unless it is mounted with `allow_other` option for root
and `user_allow_other` option for non-root.  To allow `user_allow_other`,
`/etc/fuse.conf` must also adjusted.

## plugin specification

In case the `command_plugin` supplied does not suit your need, a custom plugin
can be written as a python class module and installed under
`/path/to/site-packages/stalk/rw` folder.  One can consult the module
`command_plugin.py` in the same folder as an example.  It needs `run()` method
which will call with `root` folder path as its lone argument.  The plugin
should inherit from `BasePlugin` class in `stalk.rw.base_plugin` module;
although it currently does not check this inheritance.

## compatibility

python version 2.6 or higher is required to use *stalk*; it has been tested in
linux with python versions 2.6 and 2.7 and Mac OS X with python 2.7.

## installation

### Centos 6 variant systems (including EC2 with AWS supplied images)

            $ sudo yum install http://repo.vrane.com/yum/c6/yum-repo.rpm
            $ sudo yum install stalk
This yum repo for Centos 6 also contains the necessary open-source python
library *fusepy* and `yum install` should install that rpm too.  For other rpm
based system, run `make` command in the `docs` folder and get a binary rpm with
the following command.

            $ ./setup.py bdist_rpm  --requires fusepy

### Debian systems

Enter the following for Ubuntu 12 in `/etc/apt/sources.list`

			deb http://repo.vrane.com/apt/ u12/
Then

			$ sudo apt-get update
			$ sudo apt-get install stalk
will install the necessary packages.  For other debian systems, the following
command will build a deb file (after running a `make` command in the `docs`
folder)

            $ ./setup.py bdist_deb
You will need `python-stdeb` package.

### tarballs

			http://repo.vrane.com/downloads/

### git

github repo contains the latest code.

			https://github.com/kzw/stalk


## credits

*stalk* relies on [fusepy](https://github.com/terencehonles/fusepy) python
module.  In fact, read-only mode is derived from `memory.py` example and
read-write mode is based on `loopback.py` example.

## bugs

`sqlite3_open` in *sqlite3* C library does not work in read-write mode due to
lack of `fcntl` support by the FUSE system.  An example python script that will
produce this error is provided in `bug/` folder.  **TODO:** see if this script
breaks other types of fuse mounted folders.

`getxattr` is not supported and selinux will not work.

In read-only/push mode, do not set cachetime to 0 or to the number of seconds lower than
time it takes to sync the file otherwise multiple syncs of the file
will take place with one request for its contents.  This mode is unsuitable for a
file whose size is expected to change by orders of magnitude.

## TODO

See if the external mount helper for BSD is the same.
