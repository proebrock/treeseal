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



class Checksum:

	def __init__(self):
		self.__checksum = None # is of type 'buffer'
		self.__checksumbits = 256

	def __str__(self):
		return self.getString()

	def __eq__(self, other):
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

	def calculateForFile(self, path):
		checksum = hashlib.sha256()
		buffersize = 2**20
		f = open(path,'rb')
		while True:
			data = f.read(buffersize)
			if not data:
				break
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
		result = ''
		if self.__level == 0:
			result += 'Info: '
		elif self.__level == 1:
			result += 'Warning: '
		elif self.__level == 2:
			result += 'Error: '
		elif self.__level == 3:
			result += '### Fatal Error: '
		else:
			raise Exception('Unknown log level {0:d}'.format(self.__level))
		result += self.__message
		return result



class NodeStatus:

	OK = 0
	New = 1
	Missing = 2
	Warn = 3
	Error = 4



class Node:

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
			if self.size < 1000:
				sizestr = '{0:d} '.format(self.size)
			elif self.size < 1000**2:
				sizestr = '{0:.1f} K'.format(self.size/1000)
			elif self.size < 1000**3:
				sizestr = '{0:.1f} M'.format(self.size/1000**2)
			elif self.size < 1000**4:
				sizestr = '{0:.1f} G'.format(self.size/1000**3)
			elif self.size < 1000**5:
				sizestr = '{0:.1f} T'.format(self.size/1000**4)
			elif self.size < 1000**6:
				sizestr = '{0:.1f} P'.format(self.size/1000**5)
			else:
				sizestr = '{0:.1f} E'.format(self.size/1000**6)
			return sizestr + 'B'

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



class NodeContainer:

	def __recursiveApply(self, nodes, func):
		for n in nodes:
			func(n)
			if not n.children is None:
				self.__recursiveApply(n.children, func)

	def recursiveApply(self, func):
		self.__recursiveApply(self, func)

	def __recursivePrettyPrint(self, nodes, depth):
		for n in nodes:
			n.prettyPrint(depth * '    ')
			#print((depth * '    ') + n.name)
			if not n.children is None:
				self.__recursivePrettyPrint(n.children, depth + 1)

	def recursivePrettyPrint(self):
		self.__recursivePrettyPrint(self, 0)



class NodeList(NodeContainer, list):
	pass



class NodeDict(NodeContainer):

	def __init__(self):
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

	def getByUniqueID(self, uniqueid):
		if uniqueid not in self.__dictByUniqueID:
			return None
		return self.__dictByUniqueID[uniqueid]

	def delByUniqueID(self, uniqueid):
		node = self.__dictByUniqueID[uniqueid]
		del self.__dictByUniqueID[node.getUniqueKey()]
		del self.__dictByPythonID[node.pythonid]



class Tree:

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

	def __recursiveGetTree(self, nodetree):
		for node in nodetree:
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
			dest.insertNode(node)
			if node.isdir:
				self.__recursiveCopy(dest, self.getChildren(node))

	def recursiveCopy(self, dest):
		nodelist = NodeDict()
		nodelist.append(self.getRootNode())
		self.__recursiveCopy(dest, nodelist)
		dest.commit()

	def __recursiveGetDiffTree(self, other, selfnodes, othernodes, removeOkNodes):
		okNodes = []
		for snode in selfnodes:
			onode = othernodes.getByUniqueID(snode.getUniqueKey())
			if not onode is None:
				# nodes existing in selfnodes and othernodes: already known nodes
				snode.compareEqualNodesAndSetStatus(onode)
				if snode.isdir:
					snode.children = self.getChildren(snode)
					onode_children = other.getChildren(onode)
					self.__recursiveGetDiffTree(other, snode.children, onode_children, removeOkNodes)
					if snode.status == NodeStatus.OK and len(snode.children) == 0:
						okNodes.append(snode.getUniqueKey())
				else:
					if snode.status == NodeStatus.OK:
						okNodes.append(snode.getUniqueKey())
				othernodes.delByUniqueID(onode.getUniqueKey())
			else:
				# nodes existing in selfnodes but not in othernodes: new nodes
				snode.status = NodeStatus.New
				if snode.isdir:
					snode.children = self.getChildren(snode)
					self.__recursiveGetTree(snode.children)
					snode.children.recursiveApply(lambda n: n.setStatus(NodeStatus.New))
		# file nodes marked as ok or dir nodes with only ok descentants
		if removeOkNodes:
			for s in okNodes:
				selfnodes.delByUniqueID(s)
		# nodes existing in othernodes but not in selfnodes: missing nodes
		for onode in othernodes:
			onode.status = NodeStatus.Missing
			if onode.isdir:
				onode.children = other.getChildren(onode)
				other.__recursiveGetTree(onode.children)
				onode.children.recursiveApply(lambda n: n.setStatus(NodeStatus.Missing))
		selfnodes.update(othernodes)

	def recursiveGetDiffTree(self, other, removeOkNodes=False):
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
		if not node.isdir:
			node.checksum = Checksum()
			node.checksum.calculateForFile(fullpath)

	def getChildren(self, node):
		result = NodeDict()
		for childname in os.listdir(os.path.join(self.__rootDir, node.path)):
			childpath = os.path.join(node.path, childname)
			# skip the metadir, we do not want to add that to the database
			if os.path.join(self.__rootDir, childpath) == self.__metaDir:
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



class Instance:

	def __init__(self, rootDir):
		if not os.path.exists(rootDir):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(rootDir):
			raise MyException('Given root directory is not a directory.', 3)

		self.__metaName = '.' + ProgramName
		self.__rootDir = rootDir
		while True:
			self.__metaDir = os.path.join(self.__rootDir, self.__metaName)
			if os.path.exists(self.__metaDir):
				self.foundExistingRoot = True
				break
			self.__rootDir = os.path.split(self.__rootDir)[0]
			if self.__rootDir == '':
				self.foundExistingRoot = False
				return

		self.__fs = Filesystem(self.__rootDir, self.__metaDir)
		self.__db = Database(self.__rootDir, self.__metaDir)

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

	def importTree(self):
		self.__fs.recursiveCopy(self.__db)
		#self.__db.recursiveCopy(self.__fs)

	def getDiffTree(self):
		#return self.__fs.recursiveGetTree()
		#return self.__db.recursiveGetTree()
		return self.__fs.recursiveGetDiffTree(self.__db)
		#return self.__db.recursiveGetDiffTree(self.__fs)



###########################################
################### GUI ###################
###########################################



class ListControl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):

	def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, \
		size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		listmix.ListCtrlAutoWidthMixin.__init__(self)



class ListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		# setup listctrl and columns
		self.list = self.list = ListControl(self, size=(-1,100), style=wx.LC_REPORT | wx.LC_SORT_ASCENDING)
		self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
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

		# for listmix.ListCtrlAutoWidthMixin
		self.list.setResizeColumn(3)

		# start with empty node tree
		self.nodestack = []
		self.namestack = []

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
		self.iconWarning = self.imagelist.Add(icons.IconWarning.GetBitmap())
		self.list.SetImageList(self.imagelist, wx.IMAGE_LIST_SMALL)

	def AppendNode(self, node):
		index = self.list.GetItemCount()
		if node.status is None:
			raise Exception('Node status is \'None\'.')
		elif node.status == NodeStatus.OK:
			self.list.InsertImageItem(index, self.iconOk)
		elif node.status == NodeStatus.New:
			self.list.InsertImageItem(index, self.iconNew)
		elif node.status == NodeStatus.Missing:
			self.list.InsertImageItem(index, self.iconMissing)
		elif node.status == NodeStatus.Warn:
			self.list.InsertImageItem(index, self.iconWarning)
		elif node.status == NodeStatus.Error:
			self.list.InsertImageItem(index, self.iconError)
		else:
			raise Exception('Unknown node status {0:d}'.format(node.status))
		if node.isdir:
			self.list.SetStringItem(index, 1, ' > ')
		self.list.SetStringItem(index, 2, node.name)
		self.list.SetStringItem(index, 3, node.getSizeString())
		self.list.SetStringItem(index, 4, node.getCTimeString())
		self.list.SetStringItem(index, 5, node.getATimeString())
		self.list.SetStringItem(index, 6, node.getMTimeString())
		self.list.SetStringItem(index, 7, node.getChecksumString())
		self.list.SetItemData(index, node.pythonid)

	def IsRoot(self):
		return len(self.nodestack) <= 1

	def RefreshTree(self):
		self.list.DeleteAllItems()
		if not self.IsRoot():
			self.list.InsertStringItem(0, '')
			self.list.SetStringItem(0, 2, '..')
		for node in self.nodestack[-1]:
			self.AppendNode(node)
		path = reduce(lambda x, y: os.path.join(x, y), self.namestack)
		self.GetParent().SetAddressLine(path)

	def ShowNodeTree(self, nodetree):
		self.list.SetFocus()
		if nodetree[0].children is None:
			self.list.InsertStringItem(0, '')
			self.list.SetStringItem(0, 2, '<empty>')
			return
		self.nodestack = []
		self.nodestack.append(nodetree[0].children)
		self.namestack = []
		self.namestack.append('')
		self.RefreshTree()

	def OnItemActivated(self, event):
		index = event.m_itemIndex
		if (not self.IsRoot()) and index == 0:
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



class MainFrame(wx.Frame):
	def __init__(self, parent):
		self.baseTitle = ProgramName + ' ' + ProgramVersion
		wx.Frame.__init__(self, parent, title=self.baseTitle, size=(1024,300))

		# main menue definition
		fileMenu = wx.Menu()
		menuOpen = fileMenu.Append(wx.ID_OPEN, 'Open', 'Open Directory')
		self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
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

		# initialize local attributes
		self.srcInstance = None

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.address, 0, wx.ALL | wx.EXPAND, 5)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

		self.CreateStatusBar()

		self.Show(True)

	def SetAddressLine(self, path):
		self.address.SetValue(path)

	def OnOpen(self, event):
		 # ask user with dir select dialog
		userPath = '../dtint-example'
		self.srcInstance = Instance(userPath)

		if not self.srcInstance.foundExistingRoot:
			# offer user to reset+import, otherwise exit
			#self.srcInstance.reset()
			#self.srcInstance.importTree()
			#self.srcInstance.open()
			return
		else:
			pass
			#self.srcInstance.open()

		self.Title = self.baseTitle + ' - ' + self.srcInstance.getRootDir()

		#self.srcInstance.reset() # TESTING
		self.srcInstance.open()
		#self.srcInstance.importTree() # TESTING
		self.list.ShowNodeTree(self.srcInstance.getDiffTree())
		self.srcInstance.close()

	def OnExit(self, event):
		self.Close(True)

	def OnAbout(self, event):
		pass



if __name__ == '__main__':
	app = wx.App(False)
	frame = MainFrame(None)
	frame.Show()
	app.MainLoop()