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

		# buffering of the contents of a directory might speedup some
		# operations and allows sorting of the entries
		self.__useBuffer = True

		self.gotoRoot()

	def __str__(self):
		result = '('
		result += 'FilesystemTree: '
		result += 'depth=\'' + str(self.getDepth()) + '\''
		result += ', path=\'' + self.getPath() + '\''
		return result + ')'

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentNameStack) - 1

	def getPath(self, filename=None):
		path = reduce(lambda x, y: os.path.join(x, y), self.__parentNameStack)
		if filename is None:
			return path
		else:
			return os.path.join(path, filename)

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
		if self.__useBuffer:
			self.readCurrentDir()

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		self.__parentNameStack.pop()
		if self.__useBuffer:
			self.readCurrentDir()

	def down(self, node):
		if not node.isDirectory():
			raise MyException('\'down\' on file \'' + node.name + '\' is not possible.', 3)
		self.__parentNameStack.append(node.name)
		if self.__useBuffer:
			self.readCurrentDir()

	def insert(self, node):
		pass

	def update(self, node):
		pass

	def delete(self, nid):
		if not self.exists(nid):
			raise MyException('Node does not exist for deletion.', 1)
		fullpath = self.getFullPath(Node.nid2Name(nid))
		if os.path.isdir(fullpath):
			os.rmdir(fullpath)
		else:
			os.remove(fullpath)
		# remove node from buffer
		if self.__useBuffer:
			del self.__buffer[nid]

	def commit(self):
		pass

	def exists(self, nid):
		if self.__useBuffer:
			return nid in self.__buffer
		else:
			fullpath = self.getFullPath(Node.nid2Name(nid))
			return os.path.exists(fullpath) and os.path.isdir(fullpath) == Node.nid2IsDirectory(nid)

	def getNodeByNid(self, nid):
		if not self.exists(nid):
			return None
		else:
			if self.__useBuffer:
				return self.__buffer[nid]
			else:
				return self.__fetch(Node.nid2Name(nid))

	def __iter__(self):
		if self.__useBuffer:
			for nid in sorted(self.__buffer.keys()):
				yield self.__buffer[nid]
		else:
			for name in os.listdir(self.getFullPath()):
				node = self.__fetch(name)
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
			#print('### expensive calculation for node \'' + self.getPath(node.name) + '\' ...')
			node.info.checksum.calculateForFile(fullpath, self.signalBytesDone)
			# determine file timestamps AFTER calculating the checksum, otherwise opening
			# the file might change the access time (OS dependent)
			# this conversion from unix time stamp to local date/time might fail after year 2038...
			node.info.ctime = datetime.datetime.fromtimestamp(os.path.getctime(fullpath))
			node.info.atime = datetime.datetime.fromtimestamp(os.path.getatime(fullpath))
			node.info.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))

	### the following methods are not implementations of base class methods

	def readCurrentDir(self):
		self.__buffer = {}
		for name in os.listdir(self.getFullPath()):
			node = self.__fetch(name)
			if node is not None:
				self.__buffer[node.getNid()] = node

	def getFullPath(self, name=''):
		return os.path.join(self.__rootDir, self.getPath(), name)

	def __fetch(self, name):
		fullpath = self.getFullPath(name)
		# check blacklist
		if fullpath == self.__metaDir:
			return None
		# fetch node information
		node = Node(name)
		if not os.path.isdir(fullpath):
			node.info = NodeInfo()
			node.info.size = os.path.getsize(fullpath)
		return node
