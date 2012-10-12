import os

from misc import MyException
from node import Node
from tree import Tree



class MemoryTreeNode():

	def __init__(self, node):
		self.node = node
		if node.isDirectory():
			self.children = {}



class MemoryTree(Tree):

	def __init__(self):
		super(MemoryTree, self).__init__()
		self.reset()

	def __str__(self):
		result = '('
		result += 'MemoryTree: '
		result += 'depth=\'' + str(self.getDepth()) + '\''
		result += ', path=\'' + self.getPath() + '\''
		return result + ')'

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentMTNStack) - 1

	def getPath(self, filename=None):
		path = ''
		for n in self.__parentMTNStack:
			path = os.path.join(path, n.node.name)
		if filename is None:
			return path
		else:
			return os.path.join(path, filename)

	def reset(self):
		self.__parentMTNStack = [ MemoryTreeNode(Node('')) ]

	def gotoRoot(self):
		self.__parentMTNStack = [ self.__parentMTNStack[0] ]

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		self.__parentMTNStack.pop()

	def down(self, node):
		if node.getNid() not in self.__parentMTNStack[-1].children:
			raise MyException('No node \'' + node.name + '\' in current dir.', 3)
		mtn = self.__parentMTNStack[-1].children[node.getNid()]
		if not mtn.node.isDirectory():
			raise MyException('\'down\' on file \'' + node.name + '\' is not possible.', 3)
		self.__parentMTNStack.append(mtn)

	def insert(self, node):
		self.__parentMTNStack[-1].children[node.getNid()] = MemoryTreeNode(node)

	def update(self, node):
		self.__parentMTNStack[-1].children[node.getNid()].node = node

	def delete(self, nid):
		if not self.exists(nid):
			raise MyException('Node does not exist for deletion.', 1)
		del self.__parentMTNStack[-1].children[nid]

	def commit(self):
		pass

	def exists(self, nid):
		return nid in self.__parentMTNStack[-1].children

	def getNodeByNid(self, nid):
		if not self.exists(nid):
			return None
		return self.__parentMTNStack[-1].children[nid].node

	def __iter__(self):
		for nid in self.__parentMTNStack[-1].children.keys():
			yield self.__parentMTNStack[-1].children[nid].node

	def calculate(self, node):
		# nothing to do, just signal that the job is done if necessary
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), node.info.size)
			if self.signalBytesDone is not None:
				self.signalBytesDone(node.info.size)

	### the following methods are not implementations of base class methods