import os
from misc import sizeToString, MyException



class NodeStatus:

	Undefined = 0
	Unknown = 1
	OK = 2
	New = 3
	Missing = 4
	Warn = 5
	Error = 6

	NumStatuses = 6

	@staticmethod
	def toString(status):
		if status == NodeStatus.Undefined:
			return "Undefined"
		elif status == NodeStatus.Unknown:
			return 'Unknown'
		elif status == NodeStatus.OK:
			return 'OK'
		elif status == NodeStatus.New:
			return 'New'
		elif status == NodeStatus.Missing:
			return 'Missing'
		elif status == NodeStatus.Warn:
			return 'Warning'
		elif status == NodeStatus.Error:
			return 'Error'
		else:
			raise MyException('Not existing node status {0:d}'.format(status), 3)



class NodeInfo(object):

	def __init__(self):
		self.size = None
		self.ctime = None
		self.atime = None
		self.mtime = None
		self.checksum = None

		self.NoneString = ''

	def __str__(self):
		return '(' + \
			'size="' + self.getSizeString() + '", ' + \
			'ctime="' + self.getCTimeString() + '", ' + \
			'atime="' + self.getATimeString() + '", ' + \
			'mtime="' + self.getMTimeString() + '", ' + \
			'checksum="' + self.getChecksumString() + '"' + \
			')'

	def __eq__(self, other):
		if other is None:
			return False
		else:
			return self.size == other.size and \
			self.ctime == other.ctime and \
			self.atime == other.atime and \
			self.mtime == other.mtime

	def __ne__(self, other):
		return not self.__eq__(other)

	def getSizeString(self):
		if self.size is None:
			return self.NoneString
		else:
			return sizeToString(self.size)

	def getCTimeString(self):
		if self.ctime is None:
			return self.NoneString
		else:
			return self.ctime.strftime('%Y-%m-%d %H:%M:%S')

	def getATimeString(self):
		if self.atime is None:
			return self.NoneString
		else:
			return self.atime.strftime('%Y-%m-%d %H:%M:%S')

	def getMTimeString(self):
		if self.mtime is None:
			return self.NoneString
		else:
			return self.mtime.strftime('%Y-%m-%d %H:%M:%S')

	def getChecksumString(self):
		if self.checksum is None:
			return self.NoneString
		else:
			return self.checksum.getString(True)

	def prettyPrint(self, prefix=''):
		print('{0:s}size                {1:s}'.format(prefix, self.getSizeString()))
		print('{0:s}creation time       {1:s}'.format(prefix, self.getCTimeString()))
		print('{0:s}access time         {1:s}'.format(prefix, self.getATimeString()))
		print('{0:s}modification time   {1:s}'.format(prefix, self.getMTimeString()))
		print('{0:s}checksum            {1:s}'.format(prefix, self.getChecksumString()))



class Node(object):

	def __init__(self):
		self.status = NodeStatus.Undefined
		self.pythonid = id(self)
		self.nodeid = None
		self.parentid = None
		self.name = None
		self.path = None

		self.info = None
		self.children = None

		self.NoneString = ''

	def __str__(self):
		return '(' + \
			'status="' + self.getStatusString() + '", ' + \
			'nodeid="' + self.getNodeIDString() + '", ' + \
			'parentid="' + self.getParentIDString() + '", ' + \
			'name="' + self.getNameString() + '", ' + \
			'path="' + self.getPathString() + '", ' + \
			'info="' + self.getInfoString() + '", ' + \
			')'

	def chainWithParent(self, parent):
		if not parent.path is None:
			self.path = os.path.join(parent.path, self.name)
		if not parent.nodeid is None:
			self.parentid = parent.nodeid

	def isDirectory(self):
		return self.info is None

	def getStatusString(self):
		if self.status is None:
			return self.NoneString
		else:
			return NodeStatus.toString(self.status)

	def getNodeIDString(self):
		if self.nodeid is None:
			return self.NoneString
		else:
			return '{0:d}'.format(self.nodeid)

	def getParentIDString(self):
		if self.parentid is None:
			return self.NoneString
		else:
			return '{0:d}'.format(self.parentid)

	def getNameString(self):
		if self.name is None:
			return self.NoneString
		else:
			return self.name

	def getUniqueKey(self):
		return '{0:b}{1:s}'.format(not self.isDirectory(), self.name)

	def getPathString(self):
		if self.path is None:
			return self.NoneString
		else:
			return self.path

	def getInfoString(self):
		if self.info is None:
			return self.NoneString
		else:
			return str(self.info)

	def prettyPrint(self, prefix=''):
		print('{0:s}status              {1:s}'.format(prefix, self.getStatusString()))
		print('{0:s}nodeid              {1:s}'.format(prefix, self.getNodeIDString()))
		print('{0:s}parentid            {1:s}'.format(prefix, self.getParentIDString()))
		print('{0:s}name                {1:s}'.format(prefix, self.getNameString()))
		print('{0:s}path                {1:s}'.format(prefix, self.getPathString()))
		if self.info is not None:
			self.info.prettyPrint(prefix)



class NodeStatistics:

	def __init__(self):
		self.reset()

	def __str__(self):
		result = '( '
		for i in range(NodeStatus.NumStatuses):
			result += '{0:s}=({1:d}/{2:s}) '.format( \
				NodeStatus.toString(i), \
				self.__filecount[i], sizeToString(self.__filesize[i]))
		result += ')'
		return result

	def reset(self):
		self.__filecount = [ 0 for i in range(NodeStatus.NumStatuses) ]
		self.__filesize = [ 0 for i in range(NodeStatus.NumStatuses) ]
		self.__dircount = 0

	def update(self, node):
		if node.isDirectory():
			self.__dircount += 1
		else:
			self.__filecount[node.status] += 1
			self.__filesize[node.status] += node.info.size

	def getNodeCount(self):
		return sum(self.__filecount) + self.__dircount

	def getNodeSize(self):
		return sum(self.__filesize)



class NodeContainer(object):

	def __init__(self):
		pass

	def __preOrderApply(self, nodes, func, param, depth):
		for node in nodes:
			func(self, node, param, depth)
			if not node.children is None:
				node.children.__preOrderApply(node.children, func, param, depth + 1)

	def preOrderApply(self, func, param):
		self.__preOrderApply(self, func, param, 0)

	def __postOrderApply(self, nodes, func, param, depth):
		for node in nodes:
			if not node.children is None:
				node.children.__postOrderApply(node.children, func, param, depth + 1)
			func(self, node, param, depth)

	def postOrderApply(self, func, param):
		self.__postOrderApply(self, func, param, 0)

	def __setStatusFunc(self, node, param, depth):
		node.status = param

	def setStatus(self, status):
		self.preOrderApply(NodeContainer.__setStatusFunc, status)

	def __prettyPrintFunc(self, node, param, depth):
		node.prettyPrint(depth * '    ')
		print('')

	def prettyPrint(self):
		self.preOrderApply(NodeContainer.__prettyPrintFunc, None)

	def __getStatisticsFunc(self, node, param, depth):
		param.update(node)

	def getStatistics(self):
		stats = NodeStatistics()
		self.preOrderApply(NodeContainer.__getStatisticsFunc, stats)
		return stats

	def __insertFunc(self, node, param, depth):
		dest = param
		dest.insertNode(node)

	def insert(self, dest):
		self.preOrderApply(NodeContainer.__insertFunc, dest)
		dest.commit()



class NodeList(NodeContainer, list):

	def __init__(self):
		super(NodeList, self).__init__()



class NodeDict(NodeContainer):

	def __init__(self):
		super(NodeDict, self).__init__()
		self.__dictByUniqueID = {}
		self.__dictByPythonID = {}

	def __iter__(self):
		for key in sorted(self.__dictByUniqueID.keys()):
			yield self.__dictByUniqueID[key]

	def __getitem__(self, key):
		return self.__dictByUniqueID.values().__getitem__(key)

	def __len__(self):
		return len(self.__dictByUniqueID)

	def append(self, node):
		self.__dictByUniqueID[node.getUniqueKey()] = node
		self.__dictByPythonID[node.pythonid] = node

	def clear(self):
		self.__dictByUniqueID.clear()
		self.__dictByPythonID.clear()

	def mergeAndUpdate(self, other):
		self.__dictByUniqueID.update(other.__dictByUniqueID)
		self.__dictByPythonID.update(other.__dictByPythonID)

	def getByUniqueID(self, uniqueid):
		if uniqueid not in self.__dictByUniqueID:
			return None
		return self.__dictByUniqueID[uniqueid]

	def getByPythonID(self, pythonid):
		return self.__dictByPythonID[pythonid]

	def __delNodeFunc(self, node, param, depth):
		del self.__dictByUniqueID[node.getUniqueKey()]
		del self.__dictByPythonID[node.pythonid]

	def delByUniqueID(self, uniqueid):
		node = self.getByUniqueID(uniqueid)
		if not node.children is None:
			node.children.postOrderApply(NodeDict.__delNodeFunc, None)
		self.__delNodeFunc(node, None, 0)

	def delByPythonID(self, pythonid):
		node = self.getByPythonID(pythonid)
		if not node.children is None:
			node.children.postOrderApply(NodeDict.__delNodeFunc, None)
		self.__delNodeFunc(node, None, 0)


