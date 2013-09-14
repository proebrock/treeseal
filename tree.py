#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shlex
import subprocess

from misc import MyException
from node import NodeStatistics, NodeStatus



class Tree(object):

	def __init__(self):
		self.signalNewFile = None
		self.signalBytesDone = None

	### those basic methods should be implemented in derived classes

	def open(self):
		raise MyException('Not implemented.', 3)

	def close(self):
		raise MyException('Not implemented.', 3)

	def isOpen(self):
		raise MyException('Not implemented.', 3)

	def clear(self):
		raise MyException('Not implemented.', 3)

	def getDepth(self):
		raise MyException('Not implemented.', 3)

	def getPath(self, filename=None):
		raise MyException('Not implemented.', 3)

	def gotoRoot(self):
		raise MyException('Not implemented.', 3)

	def up(self):
		raise MyException('Not implemented.', 3)

	def down(self, node):
		raise MyException('Not implemented.', 3)

	def insert(self, node):
		raise MyException('Not implemented.', 3)

	def update(self, node):
		raise MyException('Not implemented.', 3)

	def delete(self, node):
		raise MyException('Not implemented.', 3)

	def commit(self):
		raise MyException('Not implemented.', 3)

	def exists(self, nid):
		raise MyException('Not implemented.', 3)

	def getNodeByNid(self, nid):
		raise MyException('Not implemented.', 3)

	def __iter__(self):
		raise MyException('Not implemented.', 3)

	def calculate(self, node):
		raise MyException('Not implemented.', 3)

	def globalChecksumExists(self, checksumString):
		raise MyException('Not implemented.', 3)

	def globalChecksumNumberOfOccurrences(self, checksumString):
		raise MyException('Not implemented.', 3)

	def globalGetPathsByChecksum(self, checksumString):
		raise MyException('Not implemented.', 3)

	### generic methods using basic methods

	def isRoot(self):
		return self.getDepth() == 0

	def sameDepth(self, other):
		return self.getDepth() == other.getDepth()

	def registerHandlers(self, signalNewFile, signalBytesDone):
		self.signalNewFile = signalNewFile
		self.signalBytesDone = signalBytesDone

	def unRegisterHandlers(self):
		self.signalNewFile = None
		self.signalBytesDone = None

	def __preOrderApply(self, func, param=None, ret=None, recurse=True):
		for node in self:
			nret = func(self, node, param, ret)
			if recurse and node.isDirectory():
				self.down(node)
				self.__preOrderApply(func, param, nret, recurse)
				self.up()

	def preOrderApply(self, func, node=None, param=None, recurse=True):
		if node is None:
			nret = self.__preOrderApply(func, param, None, recurse)
		else:
			nret = func(self, node, param, None)
			if recurse and node.isDirectory():
				self.down(node)
				self.__preOrderApply(func, param, nret, recurse)
				self.up()

	def __postOrderApply(self, func, param=None, recurse=True):
		for node in self:
			if recurse and node.isDirectory():
				self.down(node)
				self.__postOrderApply(func, param, recurse)
				self.up()
			func(self, node, param)

	def postOrderApply(self, func, node=None, param=None, recurse=True):
		if node is None:
			self.__postOrderApply(func, param, recurse)
		else:
			if recurse and node.isDirectory():
				self.down(node)
				self.__postOrderApply(func, param, recurse)
				self.up()
			func(self, node, param)

	def __prettyPrintFunc(self, node, param, ret):
		depth = self.getDepth() - param[0]
		node.prettyPrint(depth * '    ')
		print('')
		return None

	def prettyPrint(self, node=None, recurse=True):
		rootdepth = self.getDepth()
		self.preOrderApply(Tree.__prettyPrintFunc, node, rootdepth, recurse)

	def __graphvizExportFunc(self, node, param, ret):
		return node.graphvizExport(param[0], self.getDepth()-param[1], param[2], ret)

	def graphvizExport(self, filename='export', basic=True, node=None, recurse=True):
		# write temporary graphviz dot file
		filehandle = open(filename + '.dot', 'w')
		filehandle.write('digraph "treeseal schema"\n{\n')
		self.preOrderApply(Tree.__graphvizExportFunc, node, \
			[ filehandle, self.getDepth(), basic ], recurse)
		filehandle.write('}\n')
		filehandle.close()
		# process file with graphviz dot
		cmdline = 'dot -Tsvg -o' + filename + '.svg ' + filename + '.dot'
		args = shlex.split(cmdline)
		fnull = open(os.devnull, 'w')
		proc = subprocess.Popen(args, stdin=fnull, stdout=fnull, stderr=fnull)
		fnull.close()
		proc.communicate()
		# clean up and exit
		os.remove(filename + '.dot')

	def __getNodeStatisticsFunc(self, node, param, ret):
		param.update(node)
		return None

	def getNodeStatistics(self, node=None, recurse=True):
		stats = NodeStatistics()
		self.preOrderApply(Tree.__getNodeStatisticsFunc, node, stats, recurse)
		return stats

	def __setNodeStatusFunc(self, node, param, ret):
		node.status = param
		self.update(node)
		return None

	def setNodeStatus(self, status, node=None, recurse=True):
		self.preOrderApply(Tree.__setNodeStatusFunc, node, status, recurse)

	def getTotalNodeStatus(self):
		totalstatus = NodeStatus.Undefined
		isempty = True
		for node in self:
			isempty = False
			if totalstatus == NodeStatus.Undefined:
				if node.status == NodeStatus.Undefined:
					pass
				elif node.status == NodeStatus.New or node.status == NodeStatus.DirContainsNew:
					totalstatus = NodeStatus.DirContainsNew
				elif node.status == NodeStatus.Missing or node.status == NodeStatus.DirContainsMissing:
					totalstatus = NodeStatus.DirContainsMissing
				elif node.status == NodeStatus.Ok:
					totalstatus = NodeStatus.Ok
				elif node.status == NodeStatus.FileWarning or node.status == NodeStatus.DirContainsWarning:
					totalstatus = NodeStatus.DirContainsWarning
				elif node.status == NodeStatus.FileError or node.status == NodeStatus.DirContainsError:
					totalstatus = NodeStatus.DirContainsError
				elif node.status == NodeStatus.DirContainsMulti:
					return NodeStatus.DirContainsMulti
				else:
					raise MyException('Error in state machine.', 3)
			elif totalstatus == NodeStatus.DirContainsNew:
				if not (node.status == NodeStatus.New or node.status == NodeStatus.DirContainsNew):
					return NodeStatus.DirContainsMulti
			elif totalstatus == NodeStatus.DirContainsMissing:
				if not (node.status == NodeStatus.Missing or node.status == NodeStatus.DirContainsMissing):
					return NodeStatus.DirContainsMulti
			elif totalstatus == NodeStatus.Ok:
				if not node.status == NodeStatus.Ok:
					return NodeStatus.DirContainsMulti
			elif totalstatus == NodeStatus.DirContainsWarning:
				if not (node.status == NodeStatus.FileWarning or node.status == NodeStatus.DirContainsWarning):
					return NodeStatus.DirContainsMulti
			elif totalstatus == NodeStatus.DirContainsError:
				if not (node.status == NodeStatus.FileError or node.status == NodeStatus.DirContainsError):
					return NodeStatus.DirContainsMulti
			else:
				raise MyException('Error in state machine.', 3)
		if isempty:
			return NodeStatus.Ok
		else:
			return totalstatus

	def __deleteNodeFunc(self, node, param):
		self.delete(node)

	def deleteNode(self, node=None, recurse=True):
		self.postOrderApply(Tree.__deleteNodeFunc, node, None, recurse)

	def __copyTo(self, dest, node, recurse=True):
		self.calculate(node)
		dest.insert(node)
		if recurse and node.isDirectory():
			self.down(node)
			dest.down(dest.getNodeByNid(node.getNid()))
			for snode in self:
				self.__copyTo(dest, snode, recurse)
			dest.up()
			self.up()

	def copyTo(self, dest, node=None, recurse=True):
		if node is None:
			for snode in self:
				self.__copyTo(dest, snode, recurse)
		else:
			self.__copyTo(dest, node, recurse)

	def diff(self, old, result, removeOkNodes=True):
		for snode in self:
			onode = old.getNodeByNid(snode.getNid())
			if onode is not None:
				self.calculate(snode)
				# nodes existing in self (new) and old: already known nodes
				old.calculate(onode)
				rnode = snode
				rnode.dbkey = onode.dbkey
				result.insert(rnode)
				if snode.isDirectory():
					# tree descent
					self.down(snode)
					old.down(onode)
					result.down(rnode)
					# recurse
					rnode.status = self.diff(old, result, removeOkNodes)
					# tree ascent
					result.up()
					old.up()
					self.up()
				else:
					# compare snode and onode and set status
					if snode.info.checksum == onode.info.checksum:
						# this program is about checksums, if the checksum is valid, the status is OK
						rnode.status = NodeStatus.Ok
					else:
						# otherwise we check if someone has willingly (?) changed the file,
						# if that is not the case, we have a serious error
						if snode.info.mtime == onode.info.mtime:
							rnode.status = NodeStatus.FileError
						else:
							rnode.status = NodeStatus.FileWarning
					# always keep the old node info (even for OK nodes)
					rnode.otherinfo = onode.info
				# process status of child node
				if removeOkNodes and rnode.status == NodeStatus.Ok:
					result.delete(rnode)
				else:
					result.update(rnode)
			else:
				# nodes existing in self (new) but not in old: new nodes
				self.copyTo(result, snode)
				result.setNodeStatus(NodeStatus.New, snode)
		for onode in old:
			if self.exists(onode.getNid()):
				# existing in both: we already took care of this in the first loop
				continue
			else:
				# nodes existing in old but not in self (new): missing nodes
				old.calculate(onode)
				old.copyTo(result, onode)
				result.setNodeStatus(NodeStatus.Missing, onode)
		return result.getTotalNodeStatus()

	def __patch(self, old, node, recurse=True):
		# loop over the nodes in the patch tree
		onode = old.getNodeByNid(node.getNid())
		# dir and file
		if node.status == NodeStatus.Ok:
			return
		elif node.status == NodeStatus.New:
			self.copyTo(old, node, recurse)
		elif node.status == NodeStatus.Missing:
			old.deleteNode(onode, recurse)
		# file only
		elif node.status == NodeStatus.FileWarning or \
			node.status == NodeStatus.FileError:
			old.update(node)
		# dir only
		elif recurse and ( \
			node.status == NodeStatus.DirContainsNew or \
			node.status == NodeStatus.DirContainsMissing or \
			node.status == NodeStatus.DirContainsWarning or \
			node.status == NodeStatus.DirContainsError or \
			node.status == NodeStatus.DirContainsMulti):
			# tree descent
			self.down(node)
			old.down(onode)
			# recurse
			for snode in self:
				self.__patch(old, snode, recurse)
			# tree ascent
			old.up()
			self.up()
		else:
			raise MyException('Cannot apply diff node of status {0:d}'.format(node.status), 3)

	def patch(self, old, node=None, recurse=True):
		if node is None:
			for snode in self:
				self.__patch(old, snode, recurse)
		else:
			self.__patch(old, node, recurse)

