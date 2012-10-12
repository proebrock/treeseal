from misc import MyException
from node import NodeStatistics, NodeStatus



class Tree(object):

	def __init__(self):
		self.signalNewFile = None
		self.signalBytesDone = None

	### those basic methods should be implemented in derived classes

	def getDepth(self):
		raise MyException('Not implemented.', 3)

	def getPath(self, filename=None):
		raise MyException('Not implemented.', 3)

	def reset():
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

	def delete(self, nid):
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

	### generic methods using basic methods

	def isRoot(self):
		return self.getDepth() == 0

	def registerHandlers(self, signalNewFile, signalBytesDone):
		self.signalNewFile = signalNewFile
		self.signalBytesDone = signalBytesDone

	def unRegisterHandlers(self):
		self.signalNewFile = None
		self.signalBytesDone = None

	def __preOrderApply(self, func, param=None, recurse=True):
		for node in self:
			func(self, node, param)
			if recurse and node.isDirectory():
				self.down(node)
				self.__preOrderApply(func, param, recurse)
				self.up()

	def preOrderApply(self, func, node=None, param=None, recurse=True):
		if node is None:
			self.__preOrderApply(func, param, recurse)
		else:
			func(self, node, param)
			if recurse and node.isDirectory():
				self.down(node)
				self.__preOrderApply(func, param, recurse)
				self.up()

	def __postOrderApply(self, func, param=None, recurse=True):
		for node in self:
			if recurse and node.isDirectory():
				self.down(node)
				self.__preOrderApply(func, param, recurse)
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

	def __prettyPrintFunc(self, node, param):
		node.prettyPrint(self.getDepth() * '    ')
		print('')

	def prettyPrint(self, node=None, recurse=True):
		self.preOrderApply(Tree.__prettyPrintFunc, node, None, recurse)

	def __getNodeStatisticsFunc(self, node, param):
		param.update(node)

	def getNodeStatistics(self, node=None, recurse=True):
		stats = NodeStatistics()
		self.preOrderApply(Tree.__getNodeStatisticsFunc, node, stats, recurse)
		return stats

	def __setNodeStatusFunc(self, node, param):
		node.status = param
		self.update(node)

	def setNodeStatus(self, status, node=None, recurse=True):
		self.preOrderApply(Tree.__setNodeStatusFunc, node, status, recurse)

	def __deleteNodeFunc(self, node, param):
		self.delete(node.getNid())

	def deleteNode(self, node=None, recurse=True):
		self.postOrderApply(Tree.__deleteNodeFunc, node, None, recurse)

	def copyTo(self, dest):
		for node in self:
			self.calculate(node)
			dest.insert(node)
			if node.isDirectory():
				self.down(node)
				dest.down(dest.getNodeByNid(node.getNid()))
				self.copyTo(dest)
				dest.up()
				self.up()

	def copyNodeTo(self, dest, snode):
		# snode must be current node of self!
		dest.calculate(snode)
		dest.insert(snode)
		if snode.isDirectory():
			self.down(snode)
			dest.down(dest.getNodeByNid(snode.getNid()))
			self.copyTo(dest)
			dest.up()
			self.up()

	def syncTo(self, dest):
		snames = {}
		for snode in self:
			dnode = dest.getNodeByNid(snode.getNid())
			if dnode is not None:
				# nodes existing in source and destination: update
				dest.update(snode)
				if snode.isDirectory():
					# recurse
					self.down(snode)
					dest.down(dnode)
					self.syncTo(dest)
					dest.up()
					self.up()
			else:
				# nodes existing in self but not in dest: copy
				self.copyNodeTo(dest, snode)
			snames[snode.name] = snode.isDirectory()
		for dnode in dest:
			if dnode.name in snames:
				if snames[dnode.name] == dnode.isDirectory():
					continue
			# nodes existing in dest but not in self: delete
			dest.deleteNode(dnode)

	def syncNodeTo(self, dest, snode):
		dnode = dest.getNodeByNid(snode.getNid())
		if dnode is not None:
				dest.update(snode)
				if snode.isDirectory():
					# recurse
					self.down(snode)
					dest.down(dnode)
					self.syncTo(dest)
					dest.up()
					self.up()
		else:
			self.copyNodeTo(dest, snode)

	def compare(self, other, result, removeOkNodes=False):
		snames = {}
		totalstatus = NodeStatus.Undefined
		for snode in self:
			self.calculate(snode)
			onode = other.getNodeByNid(snode.getNid())
			if onode is not None:
				# nodes existing in self and other: already known nodes
				other.calculate(onode)
				rnode = snode
				result.insert(rnode)
				if snode.isDirectory():
					# tree descent
					self.down(snode)
					other.down(onode)
					result.down(rnode)
					# recurse
					rnode.status = self.compare(other, result, removeOkNodes)
					# tree ascent
					result.up()
					other.up()
					self.up()
				else:
					# compare snode and onode and set status
					if snode.info == onode.info:
						if snode.info.checksum == onode.info.checksum:
							rnode.status = NodeStatus.OK
						else:
							rnode.status = NodeStatus.Error
					else:
						rnode.status = NodeStatus.Warn
				# process status of child node
				if removeOkNodes and rnode.status == NodeStatus.OK:
					result.delete(rnode.getNid())
				else:
					totalstatus = NodeStatus.updateStatus(totalstatus, rnode.status)
					result.update(rnode)
			else:
				# nodes existing in self but not in other: new nodes
				self.copyNodeTo(result, snode)
				result.setNodeStatus(NodeStatus.New, snode)
				totalstatus = NodeStatus.updateStatus(totalstatus, NodeStatus.New)
			# buffer that info for later determining new nodes
			snames[snode.name] = snode.isDirectory()
		for onode in other:
			if onode.name in snames:
				if snames[onode.name] == onode.isDirectory():
					continue
			# nodes existing in other but not in self: missing nodes
			other.calculate(onode)
			other.copyNodeTo(result, onode)
			result.setNodeStatus(NodeStatus.Missing, onode)
			totalstatus = NodeStatus.updateStatus(totalstatus, NodeStatus.Missing)
		if totalstatus == NodeStatus.Undefined:
			return NodeStatus.OK
		else:
			return totalstatus



