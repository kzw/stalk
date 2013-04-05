#!/usr/bin/python -t

from Queue import Empty
import sys
import os
import re
import logging
import subprocess
import time
import stalk.rw.null_plugin as plugin

lg = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 30

def work(_q, _r, _remote_trgts, _plg=None):
    ''' This method is called when it's time to do rsync '''
    ''' TODO: make this one process per target '''
    try:
        while _q.get(False): continue
    except:
        pass
    if _plg is not None:
        lg.info("running plugin")
        _plg.run(_r)
    # rsync --timeout option
    for target in _remote_trgts:
        lg.info("calling rsync for target '%s'", target)
        rv = subprocess.call(['rsync', '-aH', '--delete', _r, target])
        if 0 != rv:
            lg.error("failed to rsync for target '%s'. exit code %d" %
		(target.encode('ascii', 'ignore'), rv))
        else:
            lg.info("rsync exit code 0 for '%s'" %
                target.encode('ascii', 'ignore'))

def _get_plugin(_c):
    ''' Load an optional plugin '''
    if _c.has_section('plugin'):
        plug = _c.get('plugin', 'name').encode('ascii')
        plug_pat = re.compile('^\w+$')
        if not plug_pat.match(plug):
            lg.error("invalid plugin name %s" % plug)
            return
        try:
            exec('import stalk.rw.' + plug + ' as plugin')
        except ImportError:
            lg.error("failed to import plugin '%s'" % plug)
            return
        except Exception, e:
            lg.error("error importing plugin '%s'" % plug)
            lg.error(e)
            return
        lg.info("imported %s plugin" % plug)
        plug_obj = None
        try:
            plug_obj = plugin.StalkPlugin(_c)
        except Exception, e:
            # is it better to die here ??
            lg.error("failed to create plugin object: %s" % e)
        return plug_obj

def _get_targets(_c, rt, mn):
    ''' Parse targets from config '''
    _targets = []
    if _c.has_section('target'):
        _targets = [ _c.get('target', o) 
            for o in _c.options('target') ]
    if not _targets:
        lg.info("target not supplied")
    # The following loop, sanity check the case of targets on local machine
    # and append missing '/'
    ans = []
    for t in _targets:
        if os.path.isdir(t) and (os.path.samefile(t, rt)
            or os.path.samefile(t, mn)):
            lg.error("'%s' is the same as either root or mount", t)
            sys.exit(8)
        if not t.endswith('/'):
            t += '/'
        ans.append(t)
    return ans

def _get_timeout(_c):
    if _c.has_option('global', 'timeout'):
        try: 
            t_out = _c.getint('global', 'timeout')
        except:
            lg.critical("Invalid timeout specification")
            sys.exit(9)
        lg.info("timeout set to '%d'" % t_out)
    else:
        t_out = DEFAULT_TIMEOUT
        lg.info("timeout set to default '%d'" % t_out)
    return t_out
 
def rsync_process(_work_q, _ping_q, cf, root, mnt):
    targets = _get_targets(cf, root, mnt)
    timeout = _get_timeout(cf)
    plugin_obj = _get_plugin(cf)
    if plugin_obj is None and not targets:
        lg.critical("No plugin nor targets supplied.  Nothing to do")
        sys.exit(20)
    work(_work_q, root, targets, plugin_obj)
    quiet = True 
    last_sync = time.asctime()
    while True:
        ''' TODO: handle full queue case '''
        _ping_q.put(1)
        try:
            _work_q.get(True, timeout)
            quiet = False
        except Empty:
            if quiet:
                continue
            quiet = True
            lg.info('doing work. last worked at %s' % last_sync)
            work(_work_q, root, targets, plugin_obj)
            last_sync = time.asctime()
