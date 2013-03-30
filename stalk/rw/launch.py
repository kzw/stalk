#!/usr/bin/python

import logging
import os
import sys
import stalk.rw.work
from multiprocessing import Process, Queue
from fuse import FUSE
from stalk.rw import Stalk


lg = logging.getLogger(__name__)

def launch(opt, cf, mn):
    r = get_root(cf, mn)
    work_q = Queue() 
    ping_q = Queue()
    p = Process(target=stalk.rw.work.rsync_process,
                args=(work_q, ping_q, cf, r, mn))
    p.daemon = True
    p.start()
    FUSE(Stalk(r, work_q, ping_q, mn), mn, allow_other=opt.allow_other,
                 foreground=opt.fore_ground)

def get_root(cf, mountpoint):
    if cf.has_option('global', 'root'):
        try:
            _root = os.path.realpath(cf.get('global', 'root'))
        except:
            raise
    else:
        lg.critical("config file does not specify 'root'")
        sys.exit(1)
    if not os.path.isabs(_root):
        lg.critical("root path '%s' is not absolute" % _root)
        sys.exit(2)
    if os.path.samefile(_root, mountpoint):
        lg.critical("root path '%s' and mountpoint '%s' are the same" %
                        (_root, mountpoint))
        sys.exit(9)
    lg.info("root path is '%s'" % _root)
    if not _root.endswith('/'):
        _root += '/' 
    return _root 
