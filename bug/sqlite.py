#!/usr/bin/python
import sqlite3
sqlite3.connect('a').cursor().execute('''create table s (a int)''')
