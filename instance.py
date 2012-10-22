from sets import Set
from node import NodeStatus



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
		if self.__old is not None:
			if self.__old.getDepth() == self.__view.getDepth():
				self.__old.up()
		if self.__new is not None:
			if self.__new.getDepth() == self.__view.getDepth():
				self.__new.up()
		self.__view.up()

	def down(self, node):
		self.__view.down(node)
		if self.__old is not None:
			n = self.__old.getNodeByNid(node.getNid())
			if n is not None:
				self.__old.down(n)
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
		return Set([]), Set([]) # TODO

	def ignore(self, nids):
		for nid in nids:
			vnode = self.__view.getNodeByNid(nid)
			if vnode is None:
				raise Exception('Tree inconsistency; that should never happen.', 3)
			nnode = self.__new.getNodeByNid(nid)
			if nnode is None or self.__config.removeOkNodes:
				self.__view.deleteNode(vnode)
			else:
				self.__new.syncNodeTo(self.__view, nnode)
				self.__view.setNodeStatus(NodeStatus.OK, vnode)
		self.__view.commit()

	def fix(self, nids):
		pass