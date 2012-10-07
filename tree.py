from misc import MyException
from node import NodeStatistics, NodeStatus



class Tree(object):

	def __init__(self):
		self.signalNewFile = None
		self.signalBytesDone = None
		self.doCalculate = True

	### those basic methods should be implemented in derived classes

	def getDepth(self):
		raise MyException('Not implemented.', 3)

	def getPath(self):
		raise MyException('Not implemented.', 3)

	def reset():
		raise MyException('Not implemented.', 3)

	def gotoRoot(self):
		raise MyException('Not implemented.', 3)

	def up(self):
		raise MyException('Not implemented.', 3)

	def down(self, name):
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

	### generic methods using basic methods

	def isRoot(self):
		return self.getDepth() == 0

	def preOrderApply(self, func, param=None, recurse=True):
		for node in self:
			func(self, node, param)
			if recurse and node.isDirectory():
				self.down(node.name)
				self.preOrderApply(func, param, recurse)
				self.up()

	def postOrderApply(self, func, param=None, recurse=True):
		for node in self:
			if recurse and node.isDirectory():
				self.down(node.name)
				self.postOrderApply(func, param, recurse)
				self.up()
			func(self, node, param)

	def __prettyPrintFunc(self, node, param):
		node.prettyPrint(self.getDepth() * '    ')
		print('')

	def prettyPrint(self, recurse=True):
		self.preOrderApply(Tree.__prettyPrintFunc, None, recurse)

	def __getStatisticsFunc(self, node, param):
		stats = param
		stats.update(node)

	def getStatistics(self, recurse=True):
		stats = NodeStatistics()
		self.preOrderApply(Tree.__getStatisticsFunc, stats, recurse)
		return stats

	def __copyTo(self, dest):
		for node in self:
			dest.insert(node)
			if node.isDirectory():
				self.down(node.name)
				dest.down(node.name)
				self.__copyTo(dest)
				dest.up()
				self.up()

	def copyTo(self, dest):
		self.__copyTo(dest)
		dest.commit()

	def compare(self, other, result, removeOkNodes=False):
		for snode in self:
			onode = other.getNodeByName(snode.name)
			if (onode is not None) and (snode.isDirectory() == onode.isDirectory()):
				# nodes existing in selfnodes and othernodes: already known nodes
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
					# add result node if necessary
					if not (removeOkNodes and rnode.status == NodeStatus.OK):
						result.insert(rnode)
			else:
				# nodes existing in selfnodes but not in othernodes: new nodes
				pass
