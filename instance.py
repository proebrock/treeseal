#!/usr/bin/env python
# -*- coding: utf-8 -*-

from misc import MyException
from node import Node, NodeStatus



class Instance(object):

	def __init__(self, config, view, old, new):
		self.__config = config
		self.__view = view
		self.__old = old
		self.__new = new

	def __str__(self):
		result = '('
		result += '<view> depth={0:d} path=\'{1:s}\'' \
			.format(self.__view.getDepth(), self.__view.getPath())
		if self.__old is not None:
			result += ', <old> depth={0:d} path=\'{1:s}\'' \
				.format(self.__old.getDepth(), self.__old.getPath())
		if self.__new is not None:
			result += ', <new> depth={0:d} path=\'{1:s}\'' \
				.format(self.__new.getDepth(), self.__new.getPath())
		return result + ')'

	def isRoot(self):
		return self.__view.isRoot()

	def getDepth(self):
		return self.__view.getDepth()

	def getPath(self):
		return self.__view.getPath()

	def getNodeStatistics(self):
		return self.__view.getNodeStatistics()

	def up(self):
		# ascent in old tree
		if self.__old is not None:
			if self.__old.getDepth() == self.__view.getDepth():
				self.__old.up()
		# ascent in new tree
		if self.__new is not None:
			if self.__new.getDepth() == self.__view.getDepth():
				self.__new.up()
		# ascent in view tree, update status of parent directory we are returning from in view tree
		status = self.__view.getTotalNodeStatus()
		name = self.__view.up()
		nid = Node.constructNid(name, True)
		node = self.__view.getNodeByNid(nid)
		if node is None:
			raise Exception('Tree inconsistency; that should never happen.', 3)
		if not (node.status == NodeStatus.Missing or node.status == NodeStatus.New):
			node.status = status
			self.__view.update(node)

	def down(self, node):
		# descent in view tree
		self.__view.down(node)
		# descent in old tree if possible
		if self.__old is not None:
			n = self.__old.getNodeByNid(node.getNid())
			if n is not None:
				self.__old.down(n)
		# descent in new tree if possible
		if self.__new is not None:
			n = self.__new.getNodeByNid(node.getNid())
			if n is not None:
				self.__new.down(n)

	def getNodeByNid(self, nid):
		return self.__view.getNodeByNid(nid)

	def __iter__(self):
		for node in self.__view:
			yield node

	def getPathsByChecksum(self, csumstr):
		return self.__old.globalGetPathsByChecksum(csumstr), \
			self.__new.globalGetPathsByChecksum(csumstr)

	def __fixFunc(self, node, updateOld=False):
		# recurse
		if node.isDirectory():
			self.down(node)
			for n in self:
				self.__fixFunc(n, updateOld)
			self.up()
		# post-order: fixing of node, just for all statuses that need fixing
		if node.status == NodeStatus.New:
			if updateOld:
				self.__old.insert(node)
			node.status = NodeStatus.Ok
			self.__view.update(node)
		elif node.status == NodeStatus.Missing:
			if updateOld:
				self.__old.delete(node.getNid())
			self.__view.delete(node.getNid())
		elif node.status == NodeStatus.FileWarning or node.status == NodeStatus.FileError:
			if updateOld:
				self.__old.update(node)
			node.status = NodeStatus.Ok
			self.__view.update(node)

	def fix(self, nids, updateOld=False):
		for nid in nids:
			vnode = self.__view.getNodeByNid(nid)
			if vnode is None:
				raise Exception('Tree inconsistency; that should never happen.', 3)
			self.__fixFunc(vnode, updateOld)
		if updateOld:
			self.__old.commit()
		self.__view.commit()
