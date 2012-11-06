#!/usr/bin/env python



import os
import re
from wx.tools import img2py



icondir = 'set01'
outfile = '../icons.py'
firstparam = '-F -i -n'
otherparam = '-a -F -n'



first = True
dirlist = os.listdir(icondir)
dirlist.sort()
for entry in dirlist:
	path = os.path.join(icondir, entry)
	# skip if path
	if os.path.isdir(path):
		continue
	# skip if no icon file
	name, ext = os.path.splitext(entry)
	if not ext == '.ico':
		continue
	# determine parameters
	if first:
		first = False
		param = firstparam
	else:
		param = otherparam
	# run converter
	camelCaseName = re.sub('_([a-z])', lambda p: p.group(1).upper(), name.lower())
	variablename = camelCaseName[0].upper() + camelCaseName[1:]
	cmdline = param + ' ' + variablename + ' ' + path + ' ' + outfile
	args = cmdline.split()
	img2py.main(args)

