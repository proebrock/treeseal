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

	def close(self):
		if self.__view is not None and self.__view.isOpen:
			self.__view.close()
		if self.__old is not None and self.__old.isOpen:
			self.__old.close()
		if self.__new is not None and self.__new.isOpen:
			self.__new.close()

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
			if self.__old.sameDepth(self.__view):
				self.__old.up()
		# ascent in new tree
		if self.__new is not None:
			if self.__new.sameDepth(self.__view):
				self.__new.up()
		# ascent in view tree, update status of parent directory we are returning from in view tree
		status = self.__view.getTotalNodeStatus()
		name = self.__view.up()
		nid = Node.constructNid(name, True)
		node = self.__view.getNodeByNid(nid)
		if node is None:
			raise MyException('Tree inconsistency; that should never happen.', 3)
		if not (node.status == NodeStatus.Missing or node.status == NodeStatus.New):
			node.status = status
			self.__view.update(node)

	def down(self, node):
		# descent in old tree if possible
		if self.__old is not None:
			if self.__old.sameDepth(self.__view) and self.__old.exists(node.getNid()):
				self.__old.down(node)
		# descent in new tree if possible
		if self.__new is not None:
			if self.__new.sameDepth(self.__view) and self.__new.exists(node.getNid()):
				self.__new.down(node)
		# descent in view tree
		self.__view.down(node)

	def getNodeByNid(self, nid):
		return self.__view.getNodeByNid(nid)

	def __iter__(self):
		for node in self.__view:
			yield node

	def isQueryByChecksumPossible(self):
		return not (self.__old is None or self.__new is None)

	def getPathsByChecksum(self, csumstr):
		if self.isQueryByChecksumPossible:
			return [ \
				self.__old.globalGetPathsByChecksum(csumstr),
				self.__new.globalGetPathsByChecksum(csumstr)
				]
		else:
			return [ None, None ]

	def hasRiskOfLoss(self, node):
		if node.isDirectory():
			raise MyException('Cannot determine risk of loss for directories.', 3)
		if node.status == NodeStatus.Missing:
			csum = node.info.checksum
		elif node.status == NodeStatus.FileWarning or node.status == NodeStatus.FileError:
			csum = node.otherinfo.checksum
		else:
			return False
		return not self.__new.globalChecksumExists(csum.getString())

	def ignore(self, nids):
		for nid in nids:
			vnode = self.__view.getNodeByNid(nid)
			if vnode is None:
				raise MyException('Tree inconsistency; that should never happen.', 3)
			self.__view.deleteNode(vnode)
		self.__view.commit()

	def __patch(self, node, safeOnly):
		exists = 1
		if node.isDirectory():
			# before descent: create if necessary
			if node.status == NodeStatus.New:
				self.__new.copyTo(self.__old, node, False)
				exists = 0
			# tree descend
			self.down(node)
			numexists = 0
			for n in self:
				numexists += self.__patch(n, safeOnly)
			self.up()
			# after descent: delete if necessary (status missing and empty)
			if node.status == NodeStatus.Ok:
				exists = 0
			elif not safeOnly or (numexists == 0):
				if node.status == NodeStatus.Missing:
					self.__old.delete(node)
					exists = 0
		else:
			if node.status == NodeStatus.New:
				self.__new.copyTo(self.__old, node, False)
				exists = 0
			elif not safeOnly or not self.hasRiskOfLoss(node):
				if node.status == NodeStatus.FileWarning or node.status == NodeStatus.FileError:
					self.__old.update(node)
					exists = 0
				elif node.status == NodeStatus.Missing:
					self.__old.delete(node)
					exists = 0
		if exists == 0:
			self.__view.delete(node)
		return exists

	def patch(self, nids, safeOnly=False):
		for nid in nids:
			vnode = self.__view.getNodeByNid(nid)
			if vnode is None:
				raise MyException('Tree inconsistency; that should never happen.', 3)
			self.__patch(vnode, safeOnly)
		self.__old.commit()
		self.__view.commit()

	def __delete(self, node):
		# recurse
		if node.isDirectory():
			self.down(node)
			for n in self:
				self.__delete(n)
			self.up()
		 # post-order: deletion of node
		self.__view.delete(node)
		if self.__old.sameDepth(self.__view) and self.__old.exists(node.getNid()):
			self.__old.delete(node)
		if self.__new.sameDepth(self.__view) and self.__new.exists(node.getNid()):
			self.__new.delete(node)

	def delete(self, nids):
		for nid in nids:
			# delete in view tree
			vnode = self.__view.getNodeByNid(nid)
			if vnode is None:
				raise MyException('Tree inconsistency; that should never happen.', 3)
			self.__delete(vnode)
		self.__old.commit()
		self.__new.commit()
		self.__view.commit()
