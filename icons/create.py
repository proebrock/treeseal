#!/usr/bin/env python



import os
import sys
from wx.tools import img2py



icondir = 'set01'
outfile = 'icons.py'
firstparam = '-F -i -n'
otherparam = '-a -F -n'



first = True
for entry in os.listdir(icondir):
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
	variablename = 'icon_' + name 
	cmdline = param + ' ' + variablename + ' ' + path + ' ' + outfile
	args = cmdline.split()
	img2py.main(args)
	
