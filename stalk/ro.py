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

lg = logging.getLogger(__name__)

LOCK_ROOT = '/tmp/' 
LOCK_PREP = '.stalk'

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
            origin = cf.get(s, 'origin')     
            if origin_bad_pat.match(origin):
                lg.critical("origin '%s' must be a single file" % origin)
                sys.exit(10)
            self._origin[name] = origin
            if cf.has_option(s, 'cachetime'):
                try:
                    self._cache_per_file[name] = cf.getint(s, 'cachetime')
                except:
                    lg.critical("Invalid cachetime %s for file '%s'" %
                        (cf.get(s, 'cachetime'), name))
                    raise

        if not self._origin: 
            lg.critical("no files to mount")
            sys.exit(12)

        now = time.time()

        self._recent = {}
        cdir_st = os.lstat(cachedir)
        self._cdir = cachedir + '/'
        self._attr['/'] = dict(st_mode=(S_IFDIR | 0555), st_ctime=now,
            st_mtime=now, st_atime=now, st_nlink=2, st_size=cdir_st.st_size)

    def __del__(self):
        try:
            rmtree(self._lock_dir)
        except:
            lg.error("error removing lock dir '%s'" % self._lock_dir)
            pass
        if self._tempcache:
            lg.info("deleting temp cache '%s'" % self._cdir)
            rmtree(self._cdir)

    def getattr(self, path, fh=None):
        if '/' == path: return self._attr['/']
        bname = os.path.basename(path)
        if not bname in self._origin:
            raise FuseOSError(ENOENT)
        now = time.time()
        if bname in self._recent:
            recent = self._recent[bname]
            if bname in self._cache_per_file:
                cachetime = self._cache_per_file[bname]
            else:
                cachetime = 0
        else:
            recent = now
            cachetime = 0
        delta = now - recent
        lg.info("delta is %d cachetime is %d" % (delta, cachetime))
        if delta >= cachetime :
            origin = self._origin[bname]
            lg.info("calling rsync")
            rv = call(['rsync', '-a', origin, self._cdir])
            lg.info("rsync exit code is %d" % rv)
            self._recent[bname] = now
        st = os.lstat(self._cdir + path)
        self._attr[path] = dict((key, getattr(st, key)) for key in ('st_atime',
            'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid', 'st_nlink'))
        return self._attr[path]

    def read(self, path, size, offset, fh=None):
        self._attr[path] = self.getattr(path)
        f = open(self._cdir + path, 'r')
        f.seek(offset, 0)
        buff = f.read(size)
        f.close()
        return buff

    def readdir(self, path, fh=None):
        return ['.', '..'] + [ name.encode('utf-8') for name in self._origin ]
