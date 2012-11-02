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

	def globalGetPathsByChecksum(self, checksumString):
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

	def getTotalNodeStatus(self):
		totalstatus = NodeStatus.Undefined
		for node in self:
			if totalstatus == NodeStatus.Undefined:
				totalstatus = node.status
			elif not totalstatus == node.status:
				totalstatus = NodeStatus.Unknown
		if totalstatus == NodeStatus.Undefined:
			return NodeStatus.OK
		else:
			return totalstatus

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

	def compare(self, other, result, removeOkNodes=False):
		snames = {}
		for snode in self:
			self.calculate(snode)
			onode = other.getNodeByNid(snode.getNid())
			if onode is not None:
				# nodes existing in self and other: already known nodes
				other.calculate(onode)
				rnode = snode
				rnode.dbkey = onode.dbkey
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
					if snode.info.checksum == onode.info.checksum:
						# this program is about checksums, if the checksum is valid, the status is OK
						rnode.status = NodeStatus.OK
					else:
						# otherwise we check if someone has willingly (?) changed the file,
						# if that is not the case, we have a serious error
						if snode.info.mtime == onode.info.mtime:
							rnode.status = NodeStatus.Error
						else:
							rnode.status = NodeStatus.Warn
					# always keep the other node info (even for OK nodes)
					rnode.otherinfo = onode.info
				# process status of child node
				if removeOkNodes and rnode.status == NodeStatus.OK:
					result.delete(rnode.getNid())
				else:
					result.update(rnode)
			else:
				# nodes existing in self but not in other: new nodes
				self.copyNodeTo(result, snode)
				result.setNodeStatus(NodeStatus.New, snode)
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
		return result.getTotalNodeStatus()



