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

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentMTNStack) - 1

	def getPath(self):
		path = ''
		for n in self.__parentMTNStack:
			path = os.path.join(path, n.node.name)
		return path

	def reset(self):
		self.__parentMTNStack = [ MemoryTreeNode(Node('')) ]

	def gotoRoot(self):
		self.__parentMTNStack = [ self.__parentMTNStack[0] ]

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		self.__parentMTNStack.pop()

	def down(self, name):
		if name not in self.__parentMTNStack[-1].children:
			raise MyException('No node \'' + name + '\' in current dir.', 3)
		mtn = self.__parentMTNStack[-1].children[name]
		if not mtn.node.isDirectory():
			raise MyException('\'down\' on file \'' + name + '\' is not possible.', 3)
		self.__parentMTNStack.append(mtn)

	def insert(self, node):
		self.__parentMTNStack[-1].children[node.name] = MemoryTreeNode(node)

	def update(self, node):
		self.__parentMTNStack[-1].children[node.name].node = node

	def delete(self, name):
		del self.__parentMTNStack[-1].children[name]

	def commit(self):
		pass

	def getNodeByName(self, name):
		if name in self.__parentMTNStack[-1].children:
			return self.__parentMTNStack[-1].children[name].node
		else:
			return None

	def __iter__(self):
		for name in self.__parentMTNStack[-1].children.keys():
			yield self.__parentMTNStack[-1].children[name].node

	### the following methods are not implementations of base class methods
