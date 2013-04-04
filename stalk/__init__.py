#!/usr/bin/python

from fuse import FUSE
import logging
import re

lg = logging.getLogger(__name__)

def mount(opt, cfg, mnt): 
    vol_name = _get_volume(cfg)
    if opt.read_only:
        from stalk.ro import Stalk
        FUSE(Stalk(cfg, vol_name), mnt, ro=True, allow_other=opt.allow_other,
            foreground=opt.fore_ground)
    else:
        from stalk.rw.launch import launch
        launch(opt, cfg, vol_name, mnt)

def _get_volume(cf):
    if cf.has_option('global', 'volume-name'):
        vol = cf.get('global', 'volume-name')
        vol_pat = re.compile('^[-\w=]{1,32}$')
        if vol_pat.match(vol):
            return vol
        else:
            lg.error(
                "bad device '%s'. regex is '^[-\w=]{1,32}$'" %
                    vol.encode("ascii","ignore"))
