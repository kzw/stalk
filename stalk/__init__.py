#!/usr/bin/python

from fuse import FUSE

def mount(opt, cfg, mnt): 
    if opt.read_only:
        from stalk.ro import Stalk
        FUSE(Stalk(cfg), mnt, allow_other=opt.allow_other, foreground=opt.fore_ground)
    else:
        from stalk.rw.launch import launch
        launch(opt, cfg, mnt)
