import fnmatch
import os
import re



def generateExcludeRegex(excludes):
	# spit exclude definitions into separate lists
	# regarding files, absolute dirs and relative dirs
	excludeSplits = [ [], [], [] ]
	for e in excludes:
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
	excludeRegex = []
	for esplit in excludeSplits:
		if esplit != []:
			regex = [ fnmatch.translate(e) for e in esplit ]
			excludeRegex.append(re.compile(r'|'.join(regex)))
		else:
			excludeRegex.append(None)
	# return regular expressions
	return excludeRegex



def isExcluded(excludeRegex, rootDir, currentDir, name):
	localName = os.path.join(currentDir, name)
	# dependent on files, absolute dirs and relative dirs
	# check the paths with the regular expression
	if (os.path.isdir(os.path.join(rootDir, currentDir, name))):
		if excludeRegex[1] is not None and excludeRegex[1].match(localName):
			return True
		if excludeRegex[2] is not None and excludeRegex[2].match(name):
			return True
	else:
		if excludeRegex[0] is not None and excludeRegex[0].match(name):
			return True
	return False



def doWalk(excludeRegex, rootDir, currentDir):
	fullCurrentPath = os.path.join(rootDir, currentDir)
	for name in os.listdir(fullCurrentPath):
		if isExcluded(excludeRegex, rootDir, currentDir, name):
			continue
		fullName = os.path.join(fullCurrentPath, name)
		localName = os.path.join(currentDir, name)
		if (os.path.isdir(fullName)):
			print('>' + localName)
			doWalk(excludeRegex, rootDir, localName)
		else:
			print(localName)



rootDir = 'D:\\Projects\\treeseal-example'
excludeRegex = generateExcludeRegex([ '*.txt', 'gh*.doc', '\\a', 'b\\' ])
doWalk(excludeRegex, rootDir, '')