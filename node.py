import copy
from misc import sizeToString, MyException



class NodeStatus:

	Undefined = 0
	Unknown = 1
	OK = 2
	New = 3
	Missing = 4
	Warn = 5
	Error = 6

	NumStatuses = 7

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

	@staticmethod
	def updateStatus(oldstatus, status):
		if oldstatus == NodeStatus.Undefined:
			return status
		elif oldstatus == status:
			return oldstatus
		else:
			return NodeStatus.Unknown



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

	def __copy__(self):
		result = NodeInfo()
		result.size = self.size
		result.ctime = self.ctime
		result.atime = self.atime
		result.mtime = self.mtime
		result.checksum = self.checksum
		return result

	def __deepcopy__(self, memo):
		result = NodeInfo()
		result.size = copy.deepcopy(self.size, memo)
		result.ctime = copy.deepcopy(self.ctime, memo)
		result.atime = copy.deepcopy(self.atime, memo)
		result.mtime = copy.deepcopy(self.mtime, memo)
		result.checksum = copy.deepcopy(self.checksum, memo)
		return result

	def getSizeString(self, abbreviate=True):
		if self.size is None:
			return self.NoneString
		else:
			if abbreviate:
				return sizeToString(self.size)
			else:
				return '{0:,}'.format(self.size)

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

	def getChecksumString(self, abbreviate=True):
		if self.checksum is None:
			return self.NoneString
		else:
			return self.checksum.getString(abbreviate)

	def prettyPrint(self, prefix=''):
		print('{0:s}size                {1:s}'.format(prefix, self.getSizeString()))
		print('{0:s}creation time       {1:s}'.format(prefix, self.getCTimeString()))
		print('{0:s}access time         {1:s}'.format(prefix, self.getATimeString()))
		print('{0:s}modification time   {1:s}'.format(prefix, self.getMTimeString()))
		print('{0:s}checksum            {1:s}'.format(prefix, self.getChecksumString()))



class Node(object):

	def __init__(self, name=None):
		# unique (at least at dir level) node identifier in database and filesystem
		self.nodeid = None
		self.name = name
		# node information
		self.info = None
		# node status
		self.status = NodeStatus.Undefined

		self.NoneString = ''

	def __str__(self):
		return '(' + \
			'status="' + self.getStatusString() + '", ' + \
			'nodeid="' + self.getNodeIDString() + '", ' + \
			'name="' + self.getNameString() + '", ' + \
			'info="' + self.getInfoString() + '", ' + \
			')'

	def __copy__(self):
		result = Node()
		result.status = self.status
		result.nodeid = self.nodeid
		result.name = self.name
		result.info = self.info
		return result

	def __deepcopy__(self, memo):
		result = Node()
		result.status = copy.deepcopy(self.status, memo)
		result.nodeid = copy.deepcopy(self.nodeid, memo)
		result.name = copy.deepcopy(self.name, memo)
		result.info = copy.deepcopy(self.info, memo)
		return result

	def __eq__(self, other):
		# does not check equality of node info (!), see getNid()
		return self.getNid() == other.getNid()

	def __ne__(self, other):
		# does not check equality of node info (!), see getNid()
		return not self.__eq__(other)

	def getNid(self):
		# --------------------------------------
		# A note about the 'Node Identifier' (NID)
		# --------------------------------------
		# The NID identifies a node unambiguously among all children of the
		# same node in the tree. Looking at the filesystem, the name itself
		# would suffice, there is no way of creating a directory and a file
		# with the same name in the same directory (at least not for the
		# OSes known to me and supported by this application). The problem
		# occurres when using diff trees between the database containing
		# a directory 'foo' (old status) and the filesystem containing a
		# file 'foo' (new status). The diff tree would contain two entries
		# with directory 'foo' of status 'Missing' and of file 'foo' of
		# state 'New', therefore two nodes with the same name. This is the
		# reason to use the Nid as identifier containing a isdir flag and
		# the name. Node comparison is based on this method, too.
		return Node.constructNid(self.name, self.isDirectory())

	@staticmethod
	def constructNid(name, isdir):
		return '{0:b}{1:s}'.format(not isdir, name)

	@staticmethod
	def nid2Name(nid):
		return nid[1:]

	@staticmethod
	def nid2IsDirectory(nid):
		return nid[0] == '0'

	def isDirectory(self):
		return self.info is None

	def getIsDirString(self):
		return '{0:b}'.format(self.isDirectory())

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

	def getNameString(self):
		if self.name is None:
			return self.NoneString
		else:
			return self.name

	def getInfoString(self):
		if self.info is None:
			return self.NoneString
		else:
			return str(self.info)

	def prettyPrint(self, prefix=''):
		print('{0:s}status              {1:s}'.format(prefix, self.getStatusString()))
		print('{0:s}nodeid              {1:s}'.format(prefix, self.getNodeIDString()))
		print('{0:s}name                {1:s}'.format(prefix, self.getNameString()))
		print('{0:s}isdir               {1:s}'.format(prefix, self.getIsDirString()))
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
