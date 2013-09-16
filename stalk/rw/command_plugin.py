#!/usr/bin/python -t

from stalk.rw.base_plugin import BasePlugin
import subprocess
import logging
import os

class NoCommandError(Exception):
    pass

class CommandNotFoundError(Exception):
    pass

lg = logging.getLogger(__name__)


class StalkPlugin(BasePlugin):


    def __init__(self, cf):
        dic = dict(cf.items('plugin'))
        try:
            command = dic['command']
        except KeyError:
            raise NoCommandError("no command. check your config")
        if 0 != subprocess.call(['which', command]):
            raise CommandNotFoundError("No such command in path")
        lg.info("found command in path using 'which' command")
        # this restores the original python behavior
        del os.environ['PATH']

        del dic['command']
        del dic['name']
        self._command = [ command ] + [ v for v in dic.itervalues() ]

    def run(self, root=None):
        rv = subprocess.call(self._command + [ root ])
        if rv != 0:
           lg.info("command exit code = %d" % rv)
        else:
           lg.info("command exit code = 0")
