import datetime
import os
import platform

from tree import Tree
from misc import MyException, Checksum
from node import NodeInfo, Node



class FilesystemTree(Tree):

	def __init__(self, path):
		super(FilesystemTree, self).__init__()
		self.__rootDir = path
		self.__metaDir = os.path.join(self.__rootDir, '.dtint')
		self.gotoRoot()

	### implementation of base class methods, please keep order

	def getDepth(self):
		return self.__currentDepth

	def getPath(self):
		return self.__currentPath

	def reset(self):
		if not os.path.exists(self.__metaDir):
			# create directory
			os.mkdir(self.__metaDir)
			# if on windows platform, hide directory
			if platform.system() == 'Windows':
				os.system('attrib +h "' + self.__metaDir + '"')
		self.gotoRoot()

	def gotoRoot(self):
		self.__currentPath = ''
		self.__currentDepth = 0

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node not allowed.', 3)
		self.__currentPath = os.path.split(self.__currentPath)[0]
		self.__currentDepth -= 1

	def down(self, node):
		if not node.isDirectory():
			raise MyException('\'down\' on file not allowed.', 3)
		self.__currentPath = os.path.join(self.__currentPath, node.name)
		self.__currentDepth += 1

	def insert(self, node):
		# a node contains the metadata necessary to create the file,
		# but instead of the file content just its checksum...
		print('FilesystemTree.insert(\'' + os.path.join(self.getPath(), node.name) + '\') is not implemented.')

	def update(self, node):
		# a node contains the metadata necessary to update the file,
		# but instead of the file content just its checksum...
		print('FilesystemTree.update(\'' + os.path.join(self.getPath(), node.name) + '\') is not implemented.')

	def delete(self, node):
		fullpath = os.path.join(self.__rootDir, node.path)
		if node.isDirectory():
			os.rmdir(fullpath)
		else:
			os.remove(fullpath)

	def commit(self):
		pass

	def fetch(self, node):
		fullpath = os.path.join(self.__rootDir, node.path)
		if not os.path.isdir(fullpath):
			node.info = NodeInfo()
			node.info.size = os.path.getsize(fullpath)
		if self.calculateUponFetch:
			self.calculate(node)
		if not os.path.isdir(fullpath):
			# determine date AFTER calculating the checksum, otherwise opening
			# the file might change the access time (OS dependent)
			# this conversion from unix time stamp to local date/time might fail after year 2038...
			node.info.ctime = datetime.datetime.fromtimestamp(os.path.getctime(fullpath))
			node.info.atime = datetime.datetime.fromtimestamp(os.path.getatime(fullpath))
			node.info.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))

	def calculate(self, node):
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, node.info.size)
			fullpath = os.path.join(self.__rootDir, node.path)
			node.info.checksum = Checksum()
			node.info.checksum.calculateForFile(fullpath, self.signalBytesDone)

	def getNodeByName(self, name):
		path = os.path.join(self.__currentPath, name)
		node = Node()
		node.name = name
		node.path = path
		self.fetch(node)
		return node

	def __iter__(self):
		for name in os.listdir(os.path.join(self.__rootDir, self.__currentPath)):
			path = os.path.join(self.__currentPath, name)
			if self.__isBlacklisted(path):
				continue
			node = Node()
			node.name = name
			node.path = path
			self.fetch(node)
			yield node

	### the following methods are not implementations of base class methods

	def __isBlacklisted(self, path):
		fullpath = os.path.join(self.__rootDir, path)
		# skip the metadir, we do not want to add that to the database
		if fullpath == self.__metaDir:
			return True
		return False
