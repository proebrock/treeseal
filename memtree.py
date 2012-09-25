import os

from misc import MyException
from node import Node
from tree import Tree



class MemoryTree(Tree):

	def __init__(self):
		super(MemoryTree, self).__init__()
		self.reset()

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentNodeStack) - 1

	def getPath(self):
		path = ''
		for n in self.__parentNodeStack:
			path = os.path.join(path, n.name)
		return path

	def reset(self):
		rootnode = Node()
		rootnode.name = ''
		rootnode.children = {}
		self.__parentNodeStack = [ rootnode ]

	def gotoRoot(self):
		self.__parentNodeStack = [ self.__parentNodeStack[0] ]

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node not allowed.', 3)
		self.__parentNodeStack.pop()

	def down(self, node):
		if not node.isDirectory():
			raise MyException('\'down\' on file not allowed.', 3)
		self.__parentNodeStack.append(node)

	def insert(self, node):
		if node.isDirectory():
			node.children = {}
		self.__parentNodeStack[-1].children[node.name] = node

	def update(self, node):
		self.__parentNodeStack[-1].children[node.name] = node

	def delete(self, node):
		del self.__parentNodeStack[-1].children[node.name]

	def commit(self):
		pass

	def getNodeByName(self, name):
		return self.__parentNodeStack[-1].children[name]

	def __iter__(self):
		for name in self.__parentNodeStack[-1].children.keys():
			yield self.__parentNodeStack[-1].children[name]

	### the following methods are not implementations of base class methods
