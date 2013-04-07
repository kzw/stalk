#!/usr/bin/python -t

from __future__ import with_statement
from errno import EACCES
from threading import Lock
from Queue import Empty
from fuse import FuseOSError, Operations, LoggingMixIn

import os
import time
import logging
import re

dir_pat = re.compile('.*/$')
timeout_pat = re.compile('^\d+$')
lg = logging.getLogger(__name__)
WORK_PROC_TIME = 10
MIN_PING_REPORT = 2

class Stalk(LoggingMixIn, Operations):


    def __init__(self, r, q, q1, vol):
        self._device = r
        if vol:
            self.__class__.__name__ = vol
        self._queue = q
        self._ping_queue = q1
        lg.debug("creating fuse object")
        self.rwlock = Lock()
        self._last_ping = time.time()

    def _rsync(self, rv):
        lg.debug("Calling rsync now")
        ping_count = 0
        try:
            while self._ping_queue.get(False):
                ping_count += 1
        except Empty:
            pass
        self._queue.put(1)
        now = time.time()
        if 0 == ping_count:
            delta = now - self._last_ping 
            if delta > WORK_PROC_TIME:
                lg.warn("child process is blocked or dead")
                self._last_ping = now 
        else:
            delta = now - self._last_ping 
            self._last_ping = now
            if delta > MIN_PING_REPORT:
                lg.info("ping count = %d" % ping_count)
        return rv


    def __call__(self, op, path, *args):
        return super(Stalk, self).__call__(op, self._device + path, *args)

    def access(self, path, mode):
        if not os.access(path, mode):
            raise FuseOSError(EACCES)

    chmod = os.chmod
    chown = os.chown

    def create(self, path, mode):
        return os.open(path, os.O_WRONLY | os.O_CREAT, mode)

    def flush(self, path, fh):
        return self._rsync(os.fsync(fh))

    def fsync(self, path, datasync, fh):
        return self._rsync(os.fsync(fh))

    def getattr(self, path, fh=None):
        st = os.lstat(path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
            'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    getxattr = None

    def link(self, target, src):
        return self._rsync(os.link(self._device + src, target))

    listxattr = None
    mknod = os.mknod
    open = os.open

    def mkdir(self, path, mode):
        return self._rsync(os.mkdir(path, mode))

    def rmdir(self, path):
        return self._rsync(os.rmdir(path))

    def read(self, path, size, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.read(fh, size)

    def readdir(self, path, fh):
        return ['.', '..'] + os.listdir(path)

    readlink = os.readlink

    def release(self, path, fh):
        return self._rsync(os.close(fh))

    def rename(self, old, new):
        return self._rsync(os.rename(old, self._device + new))

    def statfs(self, path):
        stv = os.statvfs(path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def symlink(self, target, src):
        return self._rsync(os.symlink(src, target))

    def truncate(self, path, length, fh=None):
        with open(path, 'r+') as f:
            self._rsync(f.truncate(length))

    def unlink(self, path):
        return self._rsync(os.unlink(path))

    utimens = os.utime

    def write(self, path, data, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return self._rsync(os.write(fh, data))
