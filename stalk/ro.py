#!/usr/bin/python

from errno import ENOENT
from stat import S_IFDIR
from subprocess import call
from fuse import FuseOSError, Operations, LoggingMixIn
from shutil import rmtree

import logging
import sys
import time
import os
import re
import tempfile
import urllib
import urlparse

lg = logging.getLogger(__name__)

LOCK_ROOT = '/tmp/' 
LOCK_PREP = '.stalk'
MIN_CACHE_TIME = 60

origin_bad_pat = re.compile('.*[/*]$')

class Stalk(LoggingMixIn, Operations):


    def __init__(self, cf):
        self._attr = {}
        self._config = cf
        
        ''' determine cache dir from config'''
        self._cache_per_file = {}
        if cf.has_option('global', 'cachedir'):
            self._tempcache = False
            cachedir = cf.get('global', 'cachedir')
            if os.path.ismount(cachedir):
                lg.critical('something is mounted on %s' % cachedir)
                sys.exit(5)
            if not os.path.isdir(cachedir):
                lg.critical("'%s' is not a directory" % cachedir)
                sys.exit(6)
            if not os.path.isabs(cachedir):
                lg.critical("'%s' is not absolute" % cachedir)
                sys.exit(7)

            if os.path.isdir(cachedir):
                try:
                    lock_dir = os.path.join(LOCK_ROOT, LOCK_PREP +
                        os.path.realpath(cachedir).replace(os.sep, '_'))
                    lg.info("making lock dir '%s'", lock_dir)
                    os.makedirs(lock_dir)
                    self._lock_dir = lock_dir
                except:
                    lg.critical("failed to create lock folder '%s'" % lock_dir)
                    raise
            else:
                lg.critical("cachedir '%s' does not exist" % cachedir)
                sys.exit(17)
        else:
            self._tempcache = True
            cachedir = tempfile.mkdtemp()

        cf.remove_section('global')

        ''' determine origins from config'''
        self._origin = {}
        self._rsync = {}
        for s in cf.sections():
            if not cf.has_option(s, 'name'):
                lg.critical("file name not specified in section '%s'" % s)
                sys.exit(13)
            name = cf.get(s, 'name')
            if os.path.dirname(name) != '':
                lg.critical("filename '%s' contains directory parts" % name)
                sys.exit(14)
            if name in self._origin: 
                lg.critical("'%s' is in at least two sections")
                sys.exit(15)
            if not cf.has_option(s, 'origin'):
                lg.critical("no origin specified in section'%s'", s)
                sys.exit(11)

            if cf.has_option(s, 'cachetime'):
                try:
                    self._cache_per_file[name] = cf.getint(s, 'cachetime')
                except:
                    lg.critical("Invalid cachetime %s for file '%s'" %
                        (cf.get(s, 'cachetime'), name))
                    raise
            origin = cf.get(s, 'origin')
            self._origin[name] = origin
            splitted = urlparse.urlsplit(origin)
            if splitted.scheme and splitted.netloc:
                continue
            self._rsync[name] = 1
            if origin_bad_pat.match(origin):
                lg.critical("origin '%s' must be a single file" % origin)
                sys.exit(10)

        if not self._origin: 
            lg.critical("no files to mount")
            sys.exit(12)

        now = time.time()

        self._recent = {}
        cdir_st = os.lstat(cachedir)
        self._cdir = cachedir + '/'
        self._attr['/'] = dict(st_mode=(S_IFDIR | 0555), st_ctime=now,
            st_mtime=now, st_atime=now, st_nlink=2, st_size=cdir_st.st_size)
        file_st = os.lstat('/etc/passwd')
        self._default_file_mode = dict(st_mode=file_st.st_mode, st_ctime=now,
            st_mtime=now, st_atime=now, st_nlink=1, st_size=1)

    def __del__(self):
        try:
            rmtree(self._lock_dir)
        except:
            lg.error("error removing lock dir '%s'" % self._lock_dir)
        if self._tempcache:
            lg.info("deleting temp cache '%s'" % self._cdir)
            rmtree(self._cdir)

    def getattr(self, path, fh=None):
        if '/' == path:
            return self._attr['/']
        bname = os.path.basename(path)
        if not bname in self._origin:
            raise FuseOSError(ENOENT)
        if path in self._attr:
            return self._attr[path]
        path = self._cdir + path
        if os.path.exists(path):
            st = os.lstat(path)
            return dict((k, getattr(st, k)) for k in ('st_atime',
                'st_gid', 'st_mode', 'st_mtime', 'st_size',
                'st_uid', 'st_nlink'))
        return self._default_file_mode

    def _download(self, name, _now):
        origin = self._origin[name]
        if name in self._rsync:
            lg.info("calling rsync")
            rv = call(['rsync', '-a', origin, self._cdir])
            lg.info("rsync exit code is %d" % rv)
            self._recent[name] = _now
        else:
            lg.info("using urllib to download file")
            try:
                urllib.urlretrieve(origin, os.path.join(self._cdir, name))
            except Exception, e:
                lg.error("failed to download file %s" % name)
                lg.error(e)
                return
            self._recent[name] = _now
            lg.info("file downloaded")

    def _get_real_attr(self, path, fh=None):
        if '/' == path:
            return self._attr['/']
        bname = os.path.basename(path)
        if not bname in self._origin:
            raise FuseOSError(ENOENT)
        now = time.time()
        if bname in self._recent:
            recent = self._recent[bname]
            if bname in self._cache_per_file:
                cachetime = self._cache_per_file[bname]
            else:
                cachetime = MIN_CACHE_TIME
            delta = now - recent
            lg.info("delta is %d cachetime is %d" % (delta, cachetime))
            if delta > cachetime:
                self._download(bname, now)
        else:
            self._download(bname, now)
            lg.info("'%s' synced for the first time" % bname.encode("ascii","ignore") )
        st = os.lstat(self._cdir + path)
        self._attr[path] = dict((key, getattr(st, key)) for key in ('st_atime',
            'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid', 'st_nlink'))
        return self._attr[path]

    def read(self, path, size, offset, fh=None):
        self._attr[path] = self._get_real_attr(path)
        f = open(self._cdir + path, 'r')
        f.seek(offset, 0)
        buff = f.read(size)
        f.close()
        return buff

    def readdir(self, path, fh=None):
        return ['.', '..'] + [ name.encode('utf-8') for name in self._origin ]
