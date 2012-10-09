import datetime
import os
import platform

from misc import MyException, Checksum
from node import NodeInfo, Node
from tree import Tree



class FilesystemTree(Tree):

	def __init__(self, path):
		super(FilesystemTree, self).__init__()
		self.__rootDir = path
		self.__metaDir = os.path.join(self.__rootDir, '.dtint')
		self.gotoRoot()

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentNameStack) - 1

	def getPath(self, name=None):
		path = reduce(lambda x, y: os.path.join(x, y), self.__parentNameStack)
		if name is None:
			return path
		else:
			return os.path.join(path, name)

	def reset(self):
		if not os.path.exists(self.__metaDir):
			# create directory
			os.mkdir(self.__metaDir)
			# if on windows platform, hide directory
			if platform.system() == 'Windows':
				os.system('attrib +h "' + self.__metaDir + '"')
		self.gotoRoot()

	def gotoRoot(self):
		self.__parentNameStack = [ '' ]

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		self.__parentNameStack.pop()

	def down(self, node):
		if not node.isDirectory():
			raise MyException('\'down\' on file \'' + node.name + '\' is not possible.', 3)
		self.__parentNameStack.append(node.name)

	def insert(self, node):
		pass

	def update(self, node):
		pass

	def delete(self, node):
		fullpath = self.getFullPath(node.name)
		if node.isDirectory():
			os.rmdir(fullpath)
		else:
			os.remove(fullpath)

	def commit(self):
		pass

	def exists(self, name):
		return os.path.exists(self.getFullPath(name))

	def getNodeByName(self, name):
		return self.__fetch(name)

	def __iter__(self):
		for name in os.listdir(self.getFullPath()):
			node = self.getNodeByName(name)
			if node is not None:
				yield node

	def calculate(self, node):
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), node.info.size)
			fullpath = self.getFullPath(node.name)
			# calculate checksum
			node.info.checksum = Checksum()
			node.info.checksum.calculateForFile(fullpath, self.signalBytesDone)
			# determine file timestamps AFTER calculating the checksum, otherwise opening
			# the file might change the access time (OS dependent)
			# this conversion from unix time stamp to local date/time might fail after year 2038...
			node.info.ctime = datetime.datetime.fromtimestamp(os.path.getctime(fullpath))
			node.info.atime = datetime.datetime.fromtimestamp(os.path.getatime(fullpath))
			node.info.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))

	### the following methods are not implementations of base class methods

	def getFullPath(self, name=''):
		return os.path.join(self.__rootDir, self.getPath(), name)

	def __fetch(self, name):
		fullpath = self.getFullPath(name)
		if fullpath == self.__metaDir:
			return None
		if not self.exists(name):
			return None
		node = Node(name)
		if not os.path.isdir(fullpath):
			node.info = NodeInfo()
			node.info.size = os.path.getsize(fullpath)
		return node
