from misc import MyException
from node import NodeStatistics, NodeStatus



class Tree(object):

	def __init__(self):
		self.signalNewFile = None
		self.signalBytesDone = None

	### those basic methods should be implemented in derived classes

	def getDepth(self):
		raise MyException('Not implemented.', 3)

	def getPath(self, name=None):
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

	def delete(self, name):
		raise MyException('Not implemented.', 3)

	def commit(self):
		raise MyException('Not implemented.', 3)

	def exists(self, name):
		raise MyException('Not implemented.', 3)

	def getNodeByName(self, name):
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

	def __prettyPrintFunc(self, node, param):
		node.prettyPrint(self.getDepth() * '    ')
		print('')

	def prettyPrint(self, node=None, recurse=True):
		self.preOrderApply(Tree.__prettyPrintFunc, node, None, recurse)

	def __getStatisticsFunc(self, node, param):
		param.update(node)

	def getStatistics(self, node=None, recurse=True):
		stats = NodeStatistics()
		self.preOrderApply(Tree.__getStatisticsFunc, node, stats, recurse)
		return stats

	def __setNodeStatus(self, node, param):
		node.status = param
		self.update(node)

	def setNodeStatus(self, status, node=None, recurse=True):
		self.preOrderApply(Tree.__setNodeStatus, node, status, recurse)

	def copyTo(self, dest):
		for node in self:
			self.calculate(node)
			dest.insert(node)
			if node.isDirectory():
				self.down(node)
				dest.down(dest.getNodeByName(node.name))
				self.copyTo(dest)
				dest.up()
				self.up()

	def copyNodeTo(self, dest, snode):
		# snode must be current node of self!
		dest.calculate(snode)
		dest.insert(snode)
		if snode.isDirectory():
			self.down(snode)
			dest.down(dest.getNodeByName(snode.name))
			self.copyTo(dest)
			dest.up()
			self.up()

	def compare(self, other, result, removeOkNodes=False):
		snames = {}
		for snode in self:
			self.calculate(snode)
			onode = other.getNodeByName(snode.name)
			if (onode is not None) and (snode.isDirectory() == onode.isDirectory()):
				# nodes existing in self and other: already known nodes
				other.calculate(onode)
				rnode = snode
				if snode.isDirectory():
					# recurse
					self.down(snode)
					other.down(onode)
					result.insert(rnode) # just to be able to do a "down"
					result.down(rnode)
					self.compare(other, result, removeOkNodes)
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
					# append other node to rnode
					if not rnode.status == NodeStatus.OK:
						rnode.other = onode
					# add result node if necessary
					if not (removeOkNodes and rnode.status == NodeStatus.OK):
						result.insert(rnode)
			else:
				# nodes existing in self but not in other: missing nodes
				self.copyNodeTo(result, snode)
				result.setNodeStatus(NodeStatus.Missing, snode)
			# buffer that info for later determining new nodes
			snames[snode.name] = snode.isDirectory()
		# nodes existing in other but not in self: new nodes
		for onode in other:
			if onode.name in snames:
				if snames[onode.name] == onode.isDirectory():
					continue
			other.calculate(onode)
			other.copyNodeTo(result, onode)
			result.setNodeStatus(NodeStatus.New, onode)



