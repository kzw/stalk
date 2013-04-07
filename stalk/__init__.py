#!/usr/bin/python

from fuse import FUSE
import logging
import re

lg = logging.getLogger(__name__)

def mount(opt, cfg, mnt): 
    vol_name = opt.name
    if vol_name:
        vol_pat = re.compile('^[-\w=]{1,32}$')
        if not vol_pat.match(vol_name):
            lg.error(
                "bad volume '%s'. regex is '^[-\w=]{1,32}$'" %
                    vol_name.encode("ascii","ignore"))
            vol_name = None
    if opt.read_only:
        from stalk.ro import Stalk
        FUSE(Stalk(cfg, vol_name), mnt, ro=True, allow_other=opt.allow_other,
            foreground=opt.fore_ground)
    else:
        from stalk.rw.launch import launch
        launch(opt, cfg, vol_name, mnt)

