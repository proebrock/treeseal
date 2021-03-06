#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from misc import MyException, sizeToString



class NodeStatus:

	# dir and file
	Undefined = 0
	New = 1
	Missing = 2
	Ok = 3
	# file only
	FileWarning = 4
	FileError = 5
	# dir only
	DirContainsNew = 6
	DirContainsMissing = 7
	DirContainsWarning = 8
	DirContainsError = 9
	DirContainsMulti = 10
	# count
	NumStatuses = 11

	@staticmethod
	def toString(status):
		# dir and file
		if status == NodeStatus.Undefined:
			return "Undefined"
		elif status == NodeStatus.New:
			return 'New'
		elif status == NodeStatus.Missing:
			return 'Missing'
		elif status == NodeStatus.Ok:
			return 'Ok'
		# file only
		elif status == NodeStatus.FileWarning:
			return 'FileWarning'
		elif status == NodeStatus.FileError:
			return 'FileError'
		# dir only
		elif status == NodeStatus.DirContainsNew:
			return 'DirContainsNew'
		elif status == NodeStatus.DirContainsMissing:
			return 'DirContainsMissing'
		elif status == NodeStatus.DirContainsWarning:
			return 'DirContainsWarning'
		elif status == NodeStatus.DirContainsError:
			return 'DirContainsError'
		elif status == NodeStatus.DirContainsMulti:
			return 'DirContainsMulti'
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

	def getCTimeString(self, abbreviate=True):
		if self.ctime is None:
			return self.NoneString
		else:
			if abbreviate:
				return self.ctime.strftime('%Y-%m-%d %H:%M:%S')
			else:
				return str(self.ctime)

	def getATimeString(self, abbreviate=True):
		if self.atime is None:
			return self.NoneString
		else:
			if abbreviate:
				return self.atime.strftime('%Y-%m-%d %H:%M:%S')
			else:
				return str(self.atime)

	def getMTimeString(self, abbreviate=True):
		if self.mtime is None:
			return self.NoneString
		else:
			if abbreviate:
				return self.mtime.strftime('%Y-%m-%d %H:%M:%S')
			else:
				return str(self.mtime)

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
		self.dbkey = None
		self.name = name
		# node information
		self.info = None
		self.otherinfo = None
		# node status
		self.status = NodeStatus.Undefined

		self.NoneString = ''

	def __str__(self):
		return '(' + \
			'status="' + self.getStatusString() + '", ' + \
			'dbkey="' + self.getDbKeyString() + '", ' + \
			'name="' + self.getNameString() + '", ' + \
			'info="' + self.getInfoString() + '", ' + \
			')'

	def __copy__(self):
		result = Node()
		result.status = self.status
		result.dbkey = self.dbkey
		result.name = self.name
		result.info = self.info
		return result

	def __deepcopy__(self, memo):
		result = Node()
		result.status = copy.deepcopy(self.status, memo)
		result.dbkey = copy.deepcopy(self.dbkey, memo)
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
		return u'{0:b}{1:s}'.format(not isdir, name)

	@staticmethod
	def nid2Name(nid):
		return nid[1:]

	@staticmethod
	def nid2IsDirectory(nid):
		return nid[0] == '0'

	def isFile(self):
		return self.info is not None

	def isDirectory(self):
		return self.info is None

	def getIsDirString(self):
		if self.isDirectory():
			return 'True'
		else:
			return 'False'

	def getStatusString(self):
		if self.status is None:
			return self.NoneString
		else:
			return NodeStatus.toString(self.status)

	def getDbKeyString(self):
		if self.dbkey is None:
			return self.NoneString
		else:
			return '{0:d}'.format(self.dbkey)

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
		print('{0:s}dbkey               {1:s}'.format(prefix, self.getDbKeyString()))
		print('{0:s}name                {1:s}'.format(prefix, self.getNameString()))
		print('{0:s}isdir               {1:s}'.format(prefix, self.getIsDirString()))
		if self.info is not None:
			self.info.prettyPrint(prefix)

	def graphvizExport(self, filehandle, depth=0, basic=True, parentid=None):
		# prepare export
		vertexid = id(self)
		label = self.name.replace('\\', '\\\\')
		if not basic:
			label += '\\n' + self.getDbKeyString()
			if self.isFile():
				label += '\\n0x' + self.info.getChecksumString(True)
		indent = (depth + 1) * '\t'
		if self.isDirectory():
			if self.status == NodeStatus.DirContainsNew or \
				self.status == NodeStatus.DirContainsMissing or \
				self.status == NodeStatus.DirContainsWarning or \
				self.status == NodeStatus.DirContainsError or \
				self.status == NodeStatus.DirContainsMulti:
				attrs = 'shape=plaintext'
			else:
				attrs = 'shape=box'
		else:
			if self.status == NodeStatus.FileWarning:
				attrs = 'shape=doubleoctagon'
			elif self.status == NodeStatus.FileError:
				attrs = 'shape=tripleoctagon'
			else:
				attrs = 'shape=octagon'
		if self.status == NodeStatus.Undefined:
			attrs += ', style=dotted'
		elif self.status == NodeStatus.New:
			attrs += ', style=bold'
		elif self.status == NodeStatus.Missing:
			attrs += ', style=dashed'
		elif self.status == NodeStatus.Ok:
			attrs += ', style=solid'
		# export node
		filehandle.write(indent + '{0:d} [ {1:s}, label="{2:s}" ];\n' \
			.format(vertexid, attrs, label))
		# connect node with parent
		if parentid is not None:
			filehandle.write(indent + '{0:d} -> {1:d};\n'.format(parentid, vertexid))
		return vertexid



class NodeStatistics:

	def __init__(self):
		self.reset()

	def __str__(self):
		return '{0:d} directories and {1:s} in {2:d} files'.format( \
			self.__dircount, sizeToString(self.__filesize), self.__filecount)

	def reset(self):
		self.__dircount = 0
		self.__filecount = 0
		self.__filesize = 0

	def update(self, node):
		if node.isDirectory():
			self.__dircount += 1
		else:
			self.__filecount += 1
			self.__filesize += node.info.size

	def add(self, other):
		self.__dircount += other.__dircount
		self.__filecount += other.__filecount
		self.__filesize += other.__filesize

	def getNodeCount(self):
		return self.__filecount + self.__dircount

	def getNodeSize(self):
		return self.__filesize
