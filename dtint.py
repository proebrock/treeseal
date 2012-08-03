#!/usr/bin/env python

import binascii
import datetime
import hashlib
import os
import sqlite3
import sys
import wx
import wx.lib.mixins.listctrl as listmix

import icons



ProgramName = 'dtint'
ProgramVersion = '3.0'



def sizeToString(size):
	if size < 1000:
		sizestr = '{0:d} '.format(size)
	elif size < 1000**2:
		sizestr = '{0:.1f} K'.format(size/1000)
	elif size < 1000**3:
		sizestr = '{0:.1f} M'.format(size/1000**2)
	elif size < 1000**4:
		sizestr = '{0:.1f} G'.format(size/1000**3)
	elif size < 1000**5:
		sizestr = '{0:.1f} T'.format(size/1000**4)
	elif size < 1000**6:
		sizestr = '{0:.1f} P'.format(size/1000**5)
	else:
		sizestr = '{0:.1f} E'.format(size/1000**6)
	return sizestr + 'B'



class Checksum(object):

	def __init__(self):
		self.__checksum = None # is of type 'buffer'
		self.__checksumbits = 256

	def __str__(self):
		return self.getString()

	def __eq__(self, other):
		if other is None:
			return False
		return self.getString() == other.getString()

	def __ne__(self, other):
		return not self.__eq__(other)

	def setBinary(self, checksum):
		if not len(checksum) == self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = checksum

	def getBinary(self):
		return self.__checksum

	def setString(self, checksum):
		if not len(checksum) == 2*self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = binascii.unhexlify(checksum)

	def getString(self, short=False):
		if self.__checksum is None:
			return '<none>'
		else:
			if short:
				return binascii.hexlify(self.__checksum[0:7]).decode('utf-8') + '...'
			else:
				return binascii.hexlify(self.__checksum).decode('utf-8')

	def calculateForFile(self, path, signalBytesDone=None):
		checksum = hashlib.sha256()
		buffersize = 2**24
		f = open(path,'rb')
		while True:
			data = f.read(buffersize)
			if not data:
				break
			if signalBytesDone is not None:
				signalBytesDone(len(data))
			checksum.update(data)
		f.close()
		self.__checksum = buffer(checksum.digest())

	def saveToFile(self, path):
		f = open(path, 'w')
		f.write(self.getString())
		f.close()

	def isValidUsingSavedFile(self, path):
		f = open(path, 'r')
		csum = f.read()
		f.close()
		return csum == self.getString()



class MyException(Exception):

	def __init__(self, message, level):
		super(MyException, self).__init__(message)
		self.__message = message
		self.__level = level

	def __str__(self):
		return self.__getPrefix() + ': ' + self.__message

	def __getPrefix(self):
		if self.__level == 0:
			return 'Info'
		elif self.__level == 1:
			return 'Warning'
		elif self.__level == 2:
			return 'Error'
		elif self.__level == 3:
			return '### Fatal Error'
		else:
			raise Exception('Unknown log level {0:d}'.format(self.__level))

	def __getIcon(self):
		if self.__level == 0:
			return wx.ICON_INFORMATION
		elif self.__level == 1:
			return wx.ICON_WARNING
		elif self.__level == 2:
			return wx.ICON_ERROR
		elif self.__level == 3:
			return wx.ICON_STOP
		else:
			raise Exception('Unknown log level {0:d}'.format(self.__level))

	def showDialog(self, headerMessage=''):
		wx.MessageBox(self.__getPrefix() + ': ' + self.__message, \
			headerMessage, wx.OK | self.__getIcon())



class UserCancelledException(Exception):
	def __init_(self):
		super(UserCancelledException, self).__init__('UserCancelledException')

	def __str__(self):
		return 'UserCancelledException'



class NodeStatus:

	OK = 0
	New = 1
	Missing = 2
	Warn = 3
	Error = 4



class Node(object):

	def __init__(self):
		self.status = None
		self.pythonid = id(self)
		self.nodeid = None
		self.parentid = None
		self.name = None
		self.path = None
		self.isdir = None
		self.size = None
		self.ctime = None
		self.atime = None
		self.mtime = None
		self.checksum = None

		self.children = None
		self.similar = None

		self.NoneString = ''

	def __str__(self):
		return '(' + \
			'status="' + self.getStatusString() + '", ' + \
			'nodeid="' + self.getNodeIDString() + '", ' + \
			'parentid="' + self.getParentIDString() + '", ' + \
			'name="' + self.getNameString() + '", ' + \
			'path="' + self.getPathString() + '", ' + \
			'isdir="' + self.getIsDirString() + '", ' + \
			'size="' + self.getSizeString() + '", ' + \
			'ctime="' + self.getCTimeString() + '", ' + \
			'atime="' + self.getATimeString() + '", ' + \
			'mtime="' + self.getMTimeString() + '", ' + \
			'checksum="' + self.getChecksumString() + '"' + \
			')'

	def setStatus(self, status):
		self.status = status

	def getStatusString(self):
		if self.status is None:
			return self.NoneString
		elif self.status == NodeStatus.OK:
			return 'OK'
		elif self.status == NodeStatus.New:
			return 'New'
		elif self.status == NodeStatus.Missing:
			return 'Missing'
		elif self.status == NodeStatus.Warn:
			return 'Warning'
		elif self.status == NodeStatus.Error:
			return 'Error'
		else:
			raise Exception('Unknown node status {0:d}'.format(self.status))

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
		return '{0:b}{1:s}'.format(not self.isdir, self.name)

	def getPathString(self):
		if self.path is None:
			return self.NoneString
		else:
			return self.path

	def getIsDirString(self):
		if self.isdir is None:
			return self.NoneString
		else:
			return '{0:b}'.format(self.isdir)

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

	def compareEqualNodesAndSetStatus(self, other):
		if not (self.name == other.name and self.isdir == other.isdir):
			raise Exception('Nodes are not equal.')
		if self.size == other.size and \
			self.ctime == other.ctime and \
			self.atime == other.atime and \
			self.mtime == other.mtime:
			if self.isdir:
				self.status = NodeStatus.OK
			else:
				if self.checksum == other.checksum:
					self.status = NodeStatus.OK
				else:
					self.status = NodeStatus.Error
		else:
			self.status = NodeStatus.Warn

	def prettyPrint(self, prefix=''):
		print('{0:s}status              {1:s}'.format(prefix, self.getStatusString()))
		print('{0:s}nodeid              {1:s}'.format(prefix, self.getNodeIDString()))
		print('{0:s}parentid            {1:s}'.format(prefix, self.getParentIDString()))
		print('{0:s}name                {1:s}'.format(prefix, self.getNameString()))
		print('{0:s}path                {1:s}'.format(prefix, self.getPathString()))
		print('{0:s}isdir               {1:s}'.format(prefix, self.getIsDirString()))
		print('{0:s}size                {1:s}'.format(prefix, self.getSizeString()))
		print('{0:s}creation time       {1:s}'.format(prefix, self.getCTimeString()))
		print('{0:s}access time         {1:s}'.format(prefix, self.getATimeString()))
		print('{0:s}modification time   {1:s}'.format(prefix, self.getMTimeString()))
		print('{0:s}checksum            {1:s}'.format(prefix, self.getChecksumString()))



class NodeContainer(object):

	def __init__(self):
		pass

	def __apply(self, nodes, func):
		for n in nodes:
			func(n)
			if not n.children is None:
				self.__apply(n.children, func)

	def apply(self, func):
		self.__apply(self, func)

	def __prettyPrint(self, nodes, depth):
		for n in nodes:
			n.prettyPrint(depth * '    ')
			#print((depth * '    ') + n.name)
			if not n.children is None:
				self.__prettyPrint(n.children, depth + 1)

	def prettyPrint(self):
		self.__prettyPrint(self, 0)



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

	def update(self, other):
		self.__dictByUniqueID.update(other.__dictByUniqueID)
		self.__dictByPythonID.update(other.__dictByPythonID)

	def getByPythonID(self, pythonid):
		return self.__dictByPythonID[pythonid]

	def delByPythonID(self, pythonid):
		node = self.__dictByPythonID[pythonid]
		del self.__dictByUniqueID[node.getUniqueKey()]
		del self.__dictByPythonID[node.pythonid]

	def getByUniqueID(self, uniqueid):
		if uniqueid not in self.__dictByUniqueID:
			return None
		return self.__dictByUniqueID[uniqueid]

	def delByUniqueID(self, uniqueid):
		node = self.__dictByUniqueID[uniqueid]
		del self.__dictByUniqueID[node.getUniqueKey()]
		del self.__dictByPythonID[node.pythonid]



class Tree(object):

	def __init__(self):
		self.signalNewFile = None
		self.signalBytesDone = None

	def open(self):
		raise MyException('Not implemented.', 3)

	def close(self):
		raise MyException('Not implemented.', 3)

	def isOpen(self):
		raise MyException('Not implemented.', 3)

	def reset(self):
		raise MyException('Not implemented.', 3)

	def getRootNode(self):
		raise MyException('Not implemented.', 3)

	def fetch(self, node):
		raise MyException('Not implemented.', 3)

	def calculate(self, node):
		raise MyException('Not implemented.', 3)

	def transferUniqueInformation(self, destNode, srcNode):
		raise MyException('Not implemented.', 3)

	def getChildren(self, node):
		raise MyException('Not implemented.', 3)

	def getParent(self, node):
		raise MyException('Not implemented.', 3)

	def getNodeByPath(self, path):
		raise MyException('Not implemented.', 3)

	def insertNode(self, node):
		raise MyException('Not implemented.', 3)

	def commit(self):
		raise MyException('Not implemented.', 3)

	def registerHandlers(self, signalNewFile, signalBytesDone):
		self.signalNewFile = signalNewFile
		self.signalBytesDone = signalBytesDone

	def __recursiveGetTree(self, nodetree):
		for node in nodetree:
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, node.size)
			self.calculate(node)
			if node.isdir:
				node.children = self.getChildren(node)
				self.__recursiveGetTree(node.children)

	def recursiveGetTree(self):
		nodetree = NodeDict()
		nodetree.append(self.getRootNode())
		self.__recursiveGetTree(nodetree)
		return nodetree

	def __recursiveCopy(self, dest, nodelist):
		for node in nodelist:
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, node.size)
			self.calculate(node)
			dest.insertNode(node)
			if node.isdir:
				self.__recursiveCopy(dest, self.getChildren(node))

	def recursiveCopy(self, dest):
		nodelist = NodeDict()
		nodelist.append(self.getRootNode())
		self.__recursiveCopy(dest, nodelist)
		dest.commit()

	def __recursiveGetStatistics(self, nodelist, statistics):
		for node in nodelist:
			if not node.isdir:
				statistics[0] += 1
				statistics[1] += node.size
			else:
				statistics[2] += 1
				statistics[3] += node.size
				self.__recursiveGetStatistics(self.getChildren(node), statistics)

	def getStatistics(self, node):
		statistics = [ 0, 0, 0, 0 ]
		nodelist = NodeDict()
		nodelist.append(node)
		self.__recursiveGetStatistics(nodelist, statistics)
		return statistics

	def __recursiveGetDiffTree(self, other, selfnodes, othernodes, removeOkNodes):
		okNodes = []
		for snode in selfnodes:
			if self.signalNewFile is not None:
				self.signalNewFile(snode.path, snode.size)
			self.calculate(snode)
			onode = othernodes.getByUniqueID(snode.getUniqueKey())
			if not onode is None:
				# nodes existing in selfnodes and othernodes: already known nodes
				self.transferUniqueInformation(onode, snode)
				other.transferUniqueInformation(snode, onode)
				if other.signalNewFile is not None:
					other.signalNewFile(onode.path, onode.size)
				other.calculate(onode)
				# compare and set status
				snode.compareEqualNodesAndSetStatus(onode)
				# recurse
				if snode.isdir:
					# get children, but construct a tree just for self not for other
					snode.children = self.getChildren(snode)
					onode_children = other.getChildren(onode)
					self.__recursiveGetDiffTree(other, snode.children, onode_children, removeOkNodes)
					# collect nodes that are okay or have no descendants
					# (or only descendants that are okay and those have been removed)
					if snode.status == NodeStatus.OK and len(snode.children) == 0:
						okNodes.append(snode.getUniqueKey())
				else:
					# collect nodes that are okay
					if snode.status == NodeStatus.OK:
						okNodes.append(snode.getUniqueKey())
				othernodes.delByUniqueID(onode.getUniqueKey())
			else:
				# nodes existing in selfnodes but not in othernodes: new nodes
				snode.status = NodeStatus.New
				if snode.isdir:
					snode.children = self.getChildren(snode)
					self.__recursiveGetTree(snode.children)
					snode.children.apply(lambda n: n.setStatus(NodeStatus.New))
		# remove nodes marked as ok
		if removeOkNodes:
			for s in okNodes:
				selfnodes.delByUniqueID(s)
		# nodes existing in othernodes but not in selfnodes: missing nodes
		for onode in othernodes:
			if other.signalNewFile is not None:
				other.signalNewFile(onode.path, onode.size)
			other.calculate(onode)
			onode.status = NodeStatus.Missing
			if onode.isdir:
				onode.children = other.getChildren(onode)
				other.__recursiveGetTree(onode.children)
				onode.children.apply(lambda n: n.setStatus(NodeStatus.Missing))
		selfnodes.update(othernodes)

	def recursiveGetDiffTree(self, other, removeOkNodes=True):
		selfnodes = NodeDict()
		selfnodes.append(self.getRootNode())
		othernodes = NodeDict()
		othernodes.append(other.getRootNode())
		self.__recursiveGetDiffTree(other, selfnodes, othernodes, removeOkNodes)
		if len(selfnodes) == 0:
			# keep housekeeping root node if removed by removeOkNodes feature
			selfnodes.append(self.getRootNode())
		return selfnodes



class Database(Tree):

	def __init__(self, rootDir, metaDir):
		super(Database, self).__init__()
		self.__dbFile = os.path.join(metaDir, 'base.sqlite3')
		self.__sgFile = os.path.join(metaDir, 'base.signature')
		self.__dbcon = None

		# --- SQL strings for database access ---
		# Always keep in sync with Node and NodeInfo classes!
		# Careful with changing spaces: some strings are auto-generated!
		self.__databaseCreateString = \
			'nodeid integer primary key,' + \
			'parent integer,' + \
			'name text,' + \
			'isdir boolean not null,' + \
			'size integer,' + \
			'ctime timestamp,' + \
			'atime timestamp,' + \
			'mtime timestamp,' + \
			'checksum blob'
		self.__databaseVarNames = [s.split(' ')[0] for s in self.__databaseCreateString.split(',')]
		self.__databaseInsertVars = ','.join(self.__databaseVarNames[1:])
		self.__databaseInsertQMarks = (len(self.__databaseVarNames)-2) * '?,' + '?'
		self.__databaseSelectString = ','.join(self.__databaseVarNames)
		self.__databaseUpdateString = '=?,'.join(self.__databaseVarNames[1:]) + '=?'

	def __del__(self):
		if self.isOpen():
			self.close()

	def open(self):
		cs = Checksum()
		cs.calculateForFile(self.__dbFile)
		if not cs.isValidUsingSavedFile(self.__sgFile):
			raise MyException('The internal database has been corrupted.', 3)
		self.dbOpen()

	def close(self):
		self.dbClose()
		cs = Checksum()
		cs.calculateForFile(self.__dbFile)
		cs.saveToFile(self.__sgFile)

	def isOpen(self):
		return not self.__dbcon is None

	def reset(self):
		# close if it was open
		wasOpen = self.isOpen()
		if wasOpen:
			self.dbClose()
		# delete files if existing
		if os.path.exists(self.__dbFile):
			os.remove(self.__dbFile)
		if os.path.exists(self.__sgFile):
			os.remove(self.__sgFile)
		# create database
		self.dbOpen()
		self.__dbcon.execute('create table nodes (' + self.__databaseCreateString + ')')
		self.__dbcon.execute('create index checksumindex on nodes (checksum)')
		self.close()
		# reopen if necessary
		if wasOpen:
			self.open()

	def getRootNode(self):
		node = Node()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where parent is null')
		self.fetch(node, cursor.fetchone())
		node.path = ''
		cursor.close()
		return node

	def fetch(self, node, row):
		node.nodeid = row[0]
		node.parentid = row[1]
		node.name = row[2]
		node.isdir = row[3]
		node.size = row[4]
		node.ctime = row[5]
		node.atime = row[6]
		node.mtime = row[7]
		if not node.isdir:
			node.checksum = Checksum()
			node.checksum.setBinary(row[8])

	def calculate(self, node):
		# nothing to do, just signal that the job is done if necessary
		if self.signalBytesDone is not None:
			self.signalBytesDone(node.size)

	def transferUniqueInformation(self, destNode, srcNode):
		destNode.nodeid = srcNode.nodeid
		destNode.parentid = srcNode.parentid

	def getChildren(self, node):
		result = NodeDict()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where parent=?', (node.nodeid,))
		for row in cursor:
			child = Node()
			self.fetch(child, row)
			result.append(child)
		cursor.close()
		return result

	def getParent(self, node):
		if node.parentid is None:
			return None
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where nodeid=?', (node.parentid,))
		parent = Node()
		self.fetch(parent, cursor.fetchone())
		cursor.close()
		return parent

	def getNodeByPath(self, path):
		if path == '':
			node = self.getRootNode()
			node.path = ''
			return node
		# split path into list of names
		namelist = []
		p = path
		while not p == '':
			s = os.path.split(p)
			namelist.append(s[1])
			p = s[0]
		# traverse through tree until last but one entry
		cursor = self.__dbcon.cursor()
		cursor.execute('select nodeid from nodes where parent is null')
		nodeid = cursor.fetchone()[0]
		while len(namelist) > 1:
			cursor.execute('select nodeid from nodes where parent=? and name=?', \
				(nodeid, namelist.pop()))
			nodeid = cursor.fetchone()[0]
		# get last entry and fetch its information
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where parent=? and name=?', (nodeid, namelist.pop()))
		node = Node()
		self.fetch(node, cursor.fetchone())
		node.path = path
		cursor.close()
		return node

	def insertNode(self, node):
		if not node.nodeid is None:
			raise MyException('Node already contains a valid node id, ' + \
				'so maybe you want to update instead of insert?', 3)
		cursor = self.__dbcon.cursor()
		if node.checksum is None:
			checksum = None
		else:
			checksum = node.checksum.getBinary()
		cursor.execute('insert into nodes (' + self.__databaseInsertVars + \
			') values (' + self.__databaseInsertQMarks + ')', \
			(node.parentid, node.name, node.isdir, node.size, \
			node.ctime, node.atime, node.mtime, checksum))
		node.nodeid = cursor.lastrowid
		cursor.close()

	def commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')

	### following methods are Database specific and not from Tree

	def getNodeByChecksum(self, checksum):
		result = NodeList()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where checksum=X\'{0:s}\''.format(checksum.getString()))
		for row in cursor:
			child = Node()
			self.fetch(child, row)
			result.append(child)
		cursor.close()
		return result

	def dbOpen(self):
		self.__dbcon = sqlite3.connect(self.__dbFile, \
			# necessary for proper retrival of datetime objects from the database,
			# otherwise the cursor will return string values with the timestamps
			detect_types=sqlite3.PARSE_DECLTYPES)
		# stores strings as ascii strings in the database, not as unicodes
		# makes program easily compatible with python 2.X but introduces
		# problems when file system supports unicode... :-(
		if sys.version[0] == '2':
			self.__dbcon.text_factory = str

	def dbClose(self):
		self.__dbcon.close()
		self.__dbcon = None

	def retrieveNodePath(self, node):
		n = node
		namelist = []
		while True:
			if n is None:
				break
			else:
				namelist.append(n.name)
			n = self.getParent(n)
		namelist.reverse()
		node.path = reduce(lambda x, y: os.path.join(x, y), namelist)



class Filesystem(Tree):

	def __init__(self, rootDir, metaDir):
		super(Filesystem, self).__init__()
		self.__rootDir = rootDir
		self.__metaDir = metaDir
		self.isOpen = False

	def open(self):
		self.isOpen = True

	def close(self):
		self.isOpen = False

	def isOpen(self):
		return self.isOpen

	def reset(self):
		if not os.path.exists(self.__metaDir):
			os.mkdir(self.__metaDir)

	def getRootNode(self):
		node = Node()
		node.path = ''
		self.fetch(node)
		return node

	def fetch(self, node):
		fullpath = os.path.join(self.__rootDir, node.path)
		if not os.path.exists(fullpath):
			raise MyException('Cannot fetch data for non-existing path.', 3)
		node.name = os.path.split(node.path)[1]
		node.isdir = os.path.isdir(fullpath)
		node.size = os.path.getsize(fullpath)
		# this conversion from unix time stamp to local date/time might fail after year 2038...
		node.ctime = datetime.datetime.fromtimestamp(os.path.getctime(fullpath))
		node.atime = datetime.datetime.fromtimestamp(os.path.getatime(fullpath))
		node.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))

	def calculate(self, node):
		if node.isdir:
			if self.signalBytesDone is not None:
				self.signalBytesDone(node.size)
		if not node.isdir:
			fullpath = os.path.join(self.__rootDir, node.path)
			node.checksum = Checksum()
			node.checksum.calculateForFile(fullpath, self.signalBytesDone)

	def transferUniqueInformation(self, destNode, srcNode):
		destNode.path = srcNode.path

	def getChildren(self, node):
		result = NodeDict()
		for childname in os.listdir(os.path.join(self.__rootDir, node.path)):
			childpath = os.path.join(node.path, childname)
			if self.__isOnBlacklist(os.path.join(self.__rootDir, childpath)):
				continue
			child = Node()
			child.path = childpath
			child.parentid = node.nodeid # important when importing nodes into the db
			self.fetch(child)
			result.append(child)
		return result

	def getParent(self, node):
		if node.path == '':
			return None
		parent = Node()
		parent.path = os.path.split(node.path)[0]
		self.fetch(parent)
		return parent

	def getNodeByPath(self, path):
		if not os.path.join(self.__rootDir, path):
			return None
		node = Node()
		node.path = path
		self.fetch(node)
		return node

	### following methods are Database specific and not from Tree

	def __isOnBlacklist(self, path):
		# skip the metadir, we do not want to add that to the database
		if path == self.__metaDir:
			return True
		return False

class Instance:

	def __init__(self, path):
		# check if specified root dir exists
		if not os.path.exists(path):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(path):
			raise MyException('Given root directory is not a directory.', 3)
		# get rootdir (full path) and metadir
		self.__rootDir = path
		self.__metaName = '.' + ProgramName
		self.__metaDir = os.path.join(self.__rootDir, self.__metaName)
		# initialize two Trees, the filesystem and the database
		self.__fs = Filesystem(self.__rootDir, self.__metaDir)
		self.__db = Database(self.__rootDir, self.__metaDir)

	def findRoot(self, path):
		# try to find a metadir in rootdir, then go further up in the
		# directory tree until you reach the root looking for an existing
		# metadir
		rootDir = os.path.abspath(path)
		while True:
			metaDir = os.path.join(rootDir, self.__metaName)
			if os.path.exists(metaDir):
				return rootDir
			newRoot = os.path.split(rootDir)[0]
			if newRoot == rootDir:
				return None
			rootDir = newRoot

	def getRootDir(self):
		return self.__rootDir

	def open(self):
		self.__fs.open()
		self.__db.open()

	def close(self):
		self.__fs.close()
		self.__db.close()

	def reset(self):
		self.__fs.reset()
		self.__db.reset()

	def importTree(self, signalNewFile=None, signalBytesDone=None):
		self.__fs.registerHandlers(signalNewFile, signalBytesDone)
		self.__fs.recursiveCopy(self.__db)
		self.__fs.registerHandlers(None, None)

	def getStatistics(self):
		return self.__fs.getStatistics(self.__fs.getRootNode())
		#return self.__db.getStatistics(self.__db.getRootNode())

	def getFilesystemTree(self, signalNewFile=None, signalBytesDone=None):
		self.__fs.registerHandlers(signalNewFile, signalBytesDone)
		tree = self.__fs.recursiveGetTree()
		self.__fs.registerHandlers(None, None)
		return tree

	def getDatabaseTree(self, signalNewFile=None, signalBytesDone=None):
		self.__db.registerHandlers(signalNewFile, signalBytesDone)
		tree = self.__db.recursiveGetTree()
		self.__db.registerHandlers(None, None)
		return tree

	def getDiffTree(self, signalNewFile=None, signalBytesDone=None):
		# careful when testing: handlers have to fit to statistics
		# determined in getStatistics!
		self.__fs.registerHandlers(signalNewFile, signalBytesDone)
		tree = self.__fs.recursiveGetDiffTree(self.__db)
		self.__fs.registerHandlers(None, None)
		#self.__db.registerHandlers(signalNewFile, signalBytesDone)
		#tree = self.__db.recursiveGetDiffTree(self.__fs)
		#self.__db.registerHandlers(None, None)
		return tree




###########################################
################### GUI ###################
###########################################

class FileProcessingProgressDialog(wx.Dialog):

	def __init__(self, parent, title):
		wx.Dialog.__init__(self, parent, title=title, size=(500,350), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		self.currentBytesDone = None
		self.currentBytesAll = None
		self.totalFilesDone = None
		self.totalFilesAll = None
		self.totalBytesDone = None
		self.totalBytesAll = None
		self.cancelRequest = False

		border = 5

		self.processingText = wx.StaticText(self, label='Initializing ...')
		self.currentPathText = wx.StaticText(self, label='')
		processingSizer = wx.BoxSizer(wx.VERTICAL)
		processingSizer.Add(self.processingText, 0, wx.ALL | wx.EXPAND, border)
		processingSizer.Add(self.currentPathText, 0, wx.BOTTOM | wx.EXPAND, border+25)

		self.currentBytesHeader = wx.StaticText(self)
		self.currentBytesGauge = wx.Gauge(self)
		self.currentBytesGaugeText = wx.StaticText(self, size=(40,-1))
		currentBytesSizer = wx.BoxSizer(wx.HORIZONTAL)
		currentBytesSizer.Add(self.currentBytesGauge, 1, wx.ALL | wx.EXPAND, border)
		currentBytesSizer.Add(self.currentBytesGaugeText, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		self.totalFilesHeader = wx.StaticText(self)
		self.totalFilesGauge = wx.Gauge(self)
		self.totalFilesGaugeText = wx.StaticText(self, size=(40,-1))
		totalFilesSizer = wx.BoxSizer(wx.HORIZONTAL)
		totalFilesSizer.Add(self.totalFilesGauge, 1, wx.ALL | wx.EXPAND, border)
		totalFilesSizer.Add(self.totalFilesGaugeText, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		self.totalBytesHeader = wx.StaticText(self)
		self.totalBytesGauge = wx.Gauge(self)
		self.totalBytesGaugeText = wx.StaticText(self, size=(40,-1))
		totalBytesSizer = wx.BoxSizer(wx.HORIZONTAL)
		totalBytesSizer.Add(self.totalBytesGauge, 1, wx.ALL | wx.EXPAND, border)
		totalBytesSizer.Add(self.totalBytesGaugeText, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		self.button = wx.Button(self, label='Cancel')
		self.button.SetFocus()
		self.Bind(wx.EVT_BUTTON, self.OnClick, self.button)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(processingSizer, 0, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.currentBytesHeader, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(currentBytesSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.totalFilesHeader, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(totalFilesSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.totalBytesHeader, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(totalBytesSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.button, 0, wx.ALL | wx.ALIGN_CENTER, border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

		self.OnPaint()

	def OnClick(self, event):
		if self.button.GetLabel() == 'OK':
			self.Destroy()
		else:
			self.cancelRequest = True

	def Init(self, totalFiles, totalSize):
		#print('init for {0:d} files and {1:d} bytes'.format(totalFiles, totalSize))
		self.totalFilesDone = 0
		self.totalFilesAll = totalFiles
		self.totalFilesGauge.SetRange(totalFiles)
		self.totalBytesDone = 0
		self.totalBytesAll = totalSize
		self.totalBytesGauge.SetRange(totalSize)
		self.OnPaint()

	def SignalNewFile(self, path, size):
		#print('signal new file "{0:s}", size {1:d}'.format(path, size))
		if not self.currentBytesDone == self.currentBytesAll:
			raise MyException('Signaled a new file but the old one is not done yet.', 3)
		if self.totalBytesDone == 0:
			self.processingText.SetLabel('Processing ...')
		if path is None:
			self.currentPathText.SetLabel('<No known path>')
		else:
			self.currentPathText.SetLabel(path)
		self.currentBytesDone = 0
		self.currentBytesAll = size
		self.currentBytesGauge.SetRange(size)
		if size == 0:
			self.totalFilesDone += 1
		self.OnPaint()
		if self.cancelRequest:
			raise UserCancelledException()

	def SignalBytesDone(self, bytesDone):
		#print('signal {0:d} bytes done, current is {1:d}/{2:d}'.format( \
		#	bytesDone, self.currentBytesDone, self.currentBytesAll))
		# ignore zero byte changes
		if bytesDone == 0:
			return
		# update current bytes
		self.currentBytesDone += bytesDone
		if self.currentBytesDone > self.currentBytesAll:
			raise MyException('Signaled current size larger than full size.', 3)
		elif self.currentBytesDone == self.currentBytesAll:
			# file is complete
			self.totalFilesDone += 1
			if self.totalFilesDone > self.totalFilesAll:
				raise MyException('Signaled number of files larger than full size.', 3)
		# update total bytes
		self.totalBytesDone += bytesDone
		if self.totalBytesDone > self.totalBytesAll:
			raise MyException('Signaled total size larger than full size.', 3)
		self.OnPaint()
		if self.cancelRequest:
			raise UserCancelledException()

	def SignalFinished(self):
		#print('signal finished, cancel request is {0:b}'.format(self.cancelRequest))
		self.button.SetLabel('OK')
		if self.cancelRequest:
			self.processingText.SetLabel('Canceled by user.')
		else:
			self.processingText.SetLabel('All files successfully processed.')
		self.currentPathText.SetLabel('')
		self.ShowModal()

	def OnPaint(self):
		# size of current file
		if self.currentBytesDone is not None and self.currentBytesAll is not None:
			self.currentBytesHeader.SetLabel('Current File {0:s}/{1:s}'.format( \
				sizeToString(self.currentBytesDone), sizeToString(self.currentBytesAll)))
			if self.currentBytesAll == 0:
				self.currentBytesGauge.SetRange(1)
				self.currentBytesGauge.SetValue(1)
				self.currentBytesGaugeText.SetLabel('100 %')
			else:
				self.currentBytesGauge.SetValue(self.currentBytesDone)
				self.currentBytesGaugeText.SetLabel('{0:d} %'.format( \
				(100 * self.currentBytesDone) / self.currentBytesAll))
		else:
			self.currentBytesHeader.SetLabel('Current File -/-')
			self.currentBytesGauge.SetValue(0)
			self.currentBytesGaugeText.SetLabel('--- %')
		# total number of files
		if self.totalFilesDone is not None and self.totalFilesAll is not None:
			self.totalFilesHeader.SetLabel('Total Number of Files {0:d}/{1:d}'.format( \
				self.totalFilesDone, self.totalFilesAll))
			if self.totalFilesAll == 0:
				self.totalFilesGauge.SetRange(1)
				self.totalFilesGauge.SetValue(1)
				self.totalFilesGaugeText.SetLabel('100 %')
			else:
				self.totalFilesGauge.SetValue(self.totalFilesDone)
				self.totalFilesGaugeText.SetLabel('{0:d} %'.format( \
				(100 * self.totalFilesDone) / self.totalFilesAll))
		else:
			self.totalFilesHeader.SetLabel('Total Number of Files -/-')
			self.totalFilesGauge.SetValue(0)
			self.totalFilesGaugeText.SetLabel('--- %')
		# total size of all files
		if self.totalBytesDone is not None and self.totalBytesAll is not None:
			self.totalBytesHeader.SetLabel('Total Size {0:s}/{1:s}'.format( \
				sizeToString(self.totalBytesDone), sizeToString(self.totalBytesAll)))
			if self.totalBytesAll == 0:
				self.totalBytesGauge.SetRange(1)
				self.totalBytesGauge.SetValue(1)
				self.totalBytesGaugeText.SetLabel('100 %')
			else:
				self.totalBytesGauge.SetValue(self.totalBytesDone)
				self.totalBytesGaugeText.SetLabel('{0:d} %'.format( \
				(100 * self.totalBytesDone) / self.totalBytesAll))
		else:
			self.totalBytesHeader.SetLabel('Total Size -/-')
			self.totalBytesGauge.SetValue(0)
			self.totalBytesGaugeText.SetLabel('--- %')
		# force a repaint of the dialog
		self.Update()
		# allow wx to process events like for the cancel button
		wx.YieldIfNeeded()



class ListControl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):

	def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, \
		size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		listmix.ListCtrlAutoWidthMixin.__init__(self)



class ListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		# setup listctrl and columns
		self.list = self.list = ListControl(self, size=(-1,100), style=wx.LC_REPORT)
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
		self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
		self.list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.OnRightClick) # for wxMSW
		self.list.Bind(wx.EVT_RIGHT_UP, self.OnRightClick) # for wxGTK
		self.coldefs = \
			[ \
				('', 22), \
				('', 22), \
				('Name', 150), \
				('Size', 130), \
				('CTime', 142), \
				('ATime', 142), \
				('MTime', 142), \
				('Checksum', 132)
			]
		index = 0
		for coldef in self.coldefs:
			self.list.InsertColumn(index, coldef[0])
			self.list.SetColumnWidth(index, coldef[1])
			index = index + 1

		# for listmix.ListCtrlAutoWidthMixin, auto extend name column
		self.list.setResizeColumn(3)

		# start with empty node tree
		self.nodestack = []
		self.namestack = []

		# some constants
		self.__emptyNameString = '<empty>'
		self.__parentNameString = '..'

		# one pseudo boxer with the listctrl filling the whole panel
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

		# prepare image list
		self.imagelist = wx.ImageList(16, 16)
		self.iconError = self.imagelist.Add(icons.IconError.GetBitmap())
		self.iconMissing = self.imagelist.Add(icons.IconMissing.GetBitmap())
		self.iconNew = self.imagelist.Add(icons.IconNew.GetBitmap())
		self.iconOk = self.imagelist.Add(icons.IconOk.GetBitmap())
		self.iconUnknown = self.imagelist.Add(icons.IconUnknown.GetBitmap())
		self.iconWarning = self.imagelist.Add(icons.IconWarning.GetBitmap())
		self.list.SetImageList(self.imagelist, wx.IMAGE_LIST_SMALL)

	def AppendNode(self, node):
		if node.status is None:
			index = self.list.InsertImageItem(sys.maxint, self.iconUnknown)
		elif node.status == NodeStatus.OK:
			index = self.list.InsertImageItem(sys.maxint, self.iconOk)
		elif node.status == NodeStatus.New:
			index = self.list.InsertImageItem(sys.maxint, self.iconNew)
		elif node.status == NodeStatus.Missing:
			index = self.list.InsertImageItem(sys.maxint, self.iconMissing)
		elif node.status == NodeStatus.Warn:
			index = self.list.InsertImageItem(sys.maxint, self.iconWarning)
		elif node.status == NodeStatus.Error:
			index = self.list.InsertImageItem(sys.maxint, self.iconError)
		else:
			raise Exception('Unknown node status {0:d}'.format(node.status))
		if node.isdir:
			self.list.SetStringItem(index, 1, '>')
		self.list.SetStringItem(index, 2, node.name)
		self.list.SetStringItem(index, 3, node.getSizeString())
		self.list.SetStringItem(index, 4, node.getCTimeString())
		self.list.SetStringItem(index, 5, node.getATimeString())
		self.list.SetStringItem(index, 6, node.getMTimeString())
		self.list.SetStringItem(index, 7, node.getChecksumString())
		self.list.SetItemData(index, node.pythonid)

	def IsRoot(self):
		return len(self.nodestack) <= 1

	def Clear(self):
		self.list.DeleteAllItems()

	def RefreshTree(self):
		self.Clear()
		if not self.IsRoot():
			# for directories other than root show entry to go back to parent
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, 2, self.__parentNameString)
		if len(self.nodestack) == 0:
			# for an empty list show a special string
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, 2, self.__emptyNameString)
		else:
			for node in self.nodestack[-1]:
				self.AppendNode(node)
		path = reduce(lambda x, y: os.path.join(x, y), self.namestack)
		self.GetParent().SetAddressLine(path)

	def ShowNodeTree(self, nodetree):
		self.list.SetFocus()
		self.nodestack = []
		if nodetree[0].children is not None:
			self.nodestack.append(nodetree[0].children)
		self.namestack = []
		self.namestack.append('')
		self.RefreshTree()

	def OnItemSelected(self, event):
		index = event.m_itemIndex
		namecol = self.list.GetItem(index, 2).GetText()
		if namecol == self.__parentNameString or namecol == self.__emptyNameString:
			self.list.SetItemState(index, 0, wx.LIST_STATE_SELECTED)
		event.Skip()

	def OnItemActivated(self, event):
		index = event.m_itemIndex
		namecol = self.list.GetItem(index, 2).GetText()
		if namecol == self.__parentNameString:
			self.nodestack.pop()
			self.namestack.pop()
			self.RefreshTree()
			return
		pythonid = self.list.GetItemData(index)
		node = self.nodestack[-1].getByPythonID(pythonid)
		if node.isdir:
			self.nodestack.append(node.children)
			self.namestack.append(node.name)
			self.RefreshTree()

	def OnRightClick(self, event):
		index = self.list.GetFirstSelected()
		if index == -1:
			event.Skip()
			return

		# only do this part the first time so the events are only bound once
		if not hasattr(self, "popupID1"):
			self.popupIdRefresh = wx.NewId()
			self.popupIdUpdateDB = wx.NewId()

			self.Bind(wx.EVT_MENU, self.OnPopupRefresh, id=self.popupIdRefresh)
			self.Bind(wx.EVT_MENU, self.OnPopupUpdateDB, id=self.popupIdUpdateDB)

			menu = wx.Menu()
			menu.Append(self.popupIdRefresh, "Refresh")
			menu.Append(self.popupIdUpdateDB, "Update DB")

			# Popup the menu.  If an item is selected then its handler
			# will be called before PopupMenu returns.
			self.PopupMenu(menu)
			menu.Destroy()

	def OnPopupRefresh(self, event):
		index = self.list.GetFirstSelected()
		while not index == -1:
			pythonid = self.list.GetItemData(index)
			node = self.nodestack[-1].getByPythonID(pythonid)
			print(node.name) # some something useful here
			index = self.list.GetNextSelected(index)

	def OnPopupUpdateDB(self, event):
		pass



class MainFrame(wx.Frame):
	def __init__(self, parent):
		self.baseTitle = ProgramName + ' ' + ProgramVersion
		wx.Frame.__init__(self, parent, title=self.baseTitle, size=(1024,300))

		# main menue definition
		fileMenu = wx.Menu()
		menuImport = fileMenu.Append(wx.ID_FILE1, 'Import', 'Import Directory')
		self.Bind(wx.EVT_MENU, self.OnImport, menuImport)
		menuCheck = fileMenu.Append(wx.ID_FILE2, 'Check', 'Check Directory')
		self.Bind(wx.EVT_MENU, self.OnCheck, menuCheck)
		fileMenu.AppendSeparator()
		menuExit = fileMenu.Append(wx.ID_EXIT, 'E&xit', 'Terminate Program')
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		helpMenu = wx.Menu()
		menuAbout = helpMenu.Append(wx.ID_ABOUT, 'About', 'Information about this program')
		self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
		# assemble menu
		menuBar = wx.MenuBar()
		menuBar.Append(fileMenu, '&File')
		menuBar.Append(helpMenu, 'Help')
		self.SetMenuBar(menuBar)

		# main window consists of address line and directory listing
		self.address = wx.TextCtrl(self, -1, style=wx.TE_READONLY)
		self.list = ListControlPanel(self)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.address, 0, wx.ALL | wx.EXPAND, 5)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

		self.CreateStatusBar()

		self.Show(True)

	def SetAddressLine(self, path):
		self.address.SetValue(path)

	def OnImport(self, event):
		# get path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for import:", \
			style=wx.DD_DEFAULT_STYLE)
		dirDialog.SetPath('../dtint-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			userPath = dirDialog.GetPath()
		else:
			return
		self.Title = self.baseTitle + ' - ' + userPath

		# create and reset instance
		instance = Instance(userPath)
		instance.reset()
		instance.open()

		# create progress dialog
		progressDialog = FileProcessingProgressDialog(self, 'Importing ' + userPath)
		progressDialog.Show()
		stats = instance.getStatistics()
		progressDialog.Init(stats[0] + stats[2], stats[1] + stats[3])

		# execute task
		try:
			instance.importTree(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
		except UserCancelledException:
			self.list.Clear()
			progressDialog.SignalFinished()
			return
		except MyException as e:
			progressDialog.Destroy()
			e.showDialog('Importing ' + userPath)
			return

		# signal that we have returned from calculation, either
		# after it is done or after progressDialog signalled that the
		# user stopped the calcuation using the cancel button
		progressDialog.SignalFinished()

		tree = instance.getDatabaseTree()
		tree.apply(lambda n: n.setStatus(NodeStatus.OK))
		self.list.ShowNodeTree(tree)

		instance.close()

	def OnCheck(self, event):
		# get path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for check:", \
			style=wx.DD_DEFAULT_STYLE)
		dirDialog.SetPath('../dtint-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			userPath = dirDialog.GetPath()
		else:
			return
		self.Title = self.baseTitle + ' - ' + userPath

		# create and reset instance
		instance = Instance(userPath)
		instance.open()

		# create progress dialog
		progressDialog = FileProcessingProgressDialog(self, 'Checking ' + userPath)
		progressDialog.Show()
		stats = instance.getStatistics()
		progressDialog.Init(stats[0] + stats[2], stats[1] + stats[3])

		# execute task
		try:
			tree = instance.getDiffTree(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
		except UserCancelledException:
			self.list.Clear()
			progressDialog.SignalFinished()
			return
		except MyException as e:
			progressDialog.Destroy()
			e.showDialog('Checking ' + userPath)
			return

		# signal that we have returned from calculation, either
		# after it is done or after progressDialog signalled that the
		# user stopped the calcuation using the cancel button
		progressDialog.SignalFinished()

		self.list.ShowNodeTree(tree)

		instance.close()


	def OnExit(self, event):
		self.Close(True)

	def OnAbout(self, event):
		pass



if __name__ == '__main__':
	app = wx.App(False)
	frame = MainFrame(None)
	frame.Show()
	app.MainLoop()