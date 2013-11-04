#!/usr/bin/env python
# -*- coding: utf-8 -*-



import os
import re
import fnmatch



class FileFilter(object):

	def __init__(self, includes=[], excludes=[]):
		self.SetIncludes(includes)
		self.SetExcludes(excludes)

	def __str__(self):
		return '(includes=' + str(self.includes) + '; excludes=' + str(self.excludes) + ')'

	def SetIncludes(self, includes=[]):
		self.includes = includes
		if includes != []:
			regex = [ fnmatch.translate(e) for e in includes ]
			self.includeRegex = re.compile(r'|'.join(regex))
		else:
			self.includeRegex = None

	def SetExcludes(self, excludes=[]):
		# spit exclude definitions into separate lists
		# regarding files, absolute dirs and relative dirs
		self.excludes = excludes
		excludeSplits = [ [], [], [] ]
		for e in self.excludes:
			if e.startswith(os.path.sep):
				if e.endswith(os.path.sep):
					excludeSplits[1].append(e[1:-1])
				else:
					excludeSplits[1].append(e[1:])
			else:
				if e.endswith(os.path.sep):
					excludeSplits[2].append(e[0:-1])
				else:
					excludeSplits[0].append(e)
		# convert each of the list into a single regular expression
		self.excludeRegex = []
		for esplit in excludeSplits:
			if esplit != []:
				regex = [ fnmatch.translate(e) for e in esplit ]
				self.excludeRegex.append(re.compile(r'|'.join(regex)))
			else:
				self.excludeRegex.append(None)

	def FileAccepted(self, rootDir, currentDir, name):
		localName = os.path.join(currentDir, name)
		# dependent on files, absolute dirs and relative dirs
		# check the paths with the regular expression
		if (os.path.isdir(os.path.join(rootDir, currentDir, name))):
			if self.excludeRegex[1] is not None and self.excludeRegex[1].match(localName):
				return False
			if self.excludeRegex[2] is not None and self.excludeRegex[2].match(name):
				return False
		else:
			if self.includeRegex is not None and not self.includeRegex.match(name):
				return False
			if self.excludeRegex[0] is not None and self.excludeRegex[0].match(name):
				return False
		return True



###########################################

def doWalk(ff, rootDir, currentDir):
	fullCurrentPath = os.path.join(rootDir, currentDir)
	for name in sorted(os.listdir(fullCurrentPath)):
		if not ff.FileAccepted(rootDir, currentDir, name):
			continue
		fullName = os.path.join(fullCurrentPath, name)
		localName = os.path.join(currentDir, name)
		if (os.path.isdir(fullName)):
			print('>' + localName)
			doWalk(ff, rootDir, localName)
		else:
			print(localName)



ff = FileFilter()
ff.SetIncludes()
ff.SetIncludes([ '*.txt' ])
ff.SetExcludes([ 'a/', 'asdf.*' ])
#ff.SetExcludes([ '*.txt', 'gh*.doc', '/a', 'b/' ])
#rootDir = 'D:\\Projects\\treeseal-example'
rootDir = '/home/phil/Projects/treeseal-example'
print(ff)
doWalk(ff, rootDir, '')
