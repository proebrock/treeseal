import os
import sqlite3
import sys

from misc import MyException, Checksum
from node import NodeInfo, Node
from tree import Tree



class DatabaseTree(Tree):

	def __init__(self, path):
		super(DatabaseTree, self).__init__()
		metaDir = os.path.join(path, '.dtint')
		self.__databaseFile = os.path.join(metaDir, 'base.sqlite3')
		self.__signatureFile = os.path.join(metaDir, 'base.signature')

		# Buffering of the contents of a directory speeds up some operations
		# like exists() and getNodeByNid(), slows down some others like up()
		# and down() due to prefetching at that time. Besides it allows
		# sorting of entries in the generator
		self.__useBuffer = True

		# --- SQL strings for database access ---
		# Always keep in sync with Node and NodeInfo classes!
		# Careful with changing spaces: some strings are auto-generated!
		self.__databaseCreateString = \
			'nodekey integer primary key,' + \
			'parentkey integer,' + \
			'name text,' + \
			'isdir boolean,' + \
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

		self.__dbcon = None
		self.open()
		self.gotoRoot()

	def __del__(self):
		self.close()

	def __str__(self):
		result = '('
		result += 'DatabaseTree: '
		result += 'depth=\'' + str(self.getDepth()) + '\''
		result += ', path=\'' + self.getPath() + '\''
		result += ', id stack=\'' + ', '.join(str(id) for id in self.__parentKeyStack) + '\''
		return result + ')'

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentKeyStack) - 1

	def getPath(self, filename=None):
		path = reduce(lambda x, y: os.path.join(x, y), self.__parentNameStack)
		if filename is None:
			return path
		else:
			return os.path.join(path, filename)

	def reset(self):
		# close database
		self.dbClose()
		# delete files if existing
		if os.path.exists(self.__databaseFile):
			os.remove(self.__databaseFile)
		if os.path.exists(self.__signatureFile):
			os.remove(self.__signatureFile)
		# create database
		self.dbOpen()
		self.__dbcon.execute('create table nodes (' + self.__databaseCreateString + ')')
		self.__dbcon.execute('insert into nodes (name, isdir) values (\'<rootnode>\', 1)')
		self.__dbcon.execute('create index checksumindex on nodes (checksum)')
		self.commit()
		self.close()
		# reopen
		self.open()
		# goto root dir
		self.gotoRoot()

	def gotoRoot(self):
		self.__parentKeyStack = [ self.getRootId() ]
		self.__parentNameStack = [ '' ]
		if self.__useBuffer:
			self.readCurrentDir()

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		self.__parentKeyStack.pop()
		name = self.__parentNameStack.pop()
		if self.__useBuffer:
			self.readCurrentDir()
		return name

	def down(self, node):
		if not node.isDirectory():
			raise MyException('\'down\' on file \'' + node.name + '\' is not possible.', 3)
		self.__parentKeyStack.append(node.dbkey)
		self.__parentNameStack.append(node.name)
		if self.__useBuffer:
			self.readCurrentDir()

	def insert(self, node):
		if not node.dbkey is None:
			raise MyException('Node already contains a valid node id, ' + \
				'so maybe you want to update instead of insert?', 3)
		cursor = self.__dbcon.cursor()
		if node.isDirectory():
			cursor.execute('insert into nodes (' + self.__databaseInsertVars + \
				') values (' + self.__databaseInsertQMarks + ')', \
				(self.getCurrentParentId(), node.name, True, None, \
				None, None, None, None))
		else:
			cursor.execute('insert into nodes (' + self.__databaseInsertVars + \
				') values (' + self.__databaseInsertQMarks + ')', \
				(self.getCurrentParentId(), node.name, False, node.info.size, \
				node.info.ctime, node.info.atime, node.info.mtime, \
				node.info.checksum.getBinary()))
		node.dbkey = cursor.lastrowid
		cursor.close()
		# insert info buffer
		if self.__useBuffer:
			self.__buffer[node.getNid()] = node

	def update(self, node):
		if node.dbkey is None:
			raise MyException('Node does not contain a valid node id, ' + \
				'so maybe you want to insert instead of update?', 3)
		if node.isDirectory():
			self.__dbcon.execute('update nodes set ' + self.__databaseUpdateString + \
				' where nodekey=?', \
				(self.getCurrentParentId(), node.name, True, None, \
				None, None, None, None, node.dbkey))
		else:
			self.__dbcon.execute('update nodes set ' + self.__databaseUpdateString + \
				' where nodekey=?', \
				(self.getCurrentParentId(), node.name, False, node.info.size, \
				node.info.ctime, node.info.atime, node.info.mtime, \
				node.info.checksum.getBinary(), node.dbkey))
		# update buffer
		if self.__useBuffer:
			self.__buffer[node.getNid()] = node

	def delete(self, nid):
		self.__dbcon.execute('delete from nodes where parentkey=? and name=? and isdir=?', \
			(self.getCurrentParentId(), Node.nid2Name(nid), Node.nid2IsDirectory(nid)))
		# remove from buffer
		if self.__useBuffer:
			del self.__buffer[nid]

	def commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')

	def exists(self, nid):
		if self.__useBuffer:
			return nid in self.__buffer
		else:
			cursor = self.__dbcon.cursor()
			cursor.execute('select nodekey from nodes where parentkey=? and name=? and isdir=?', \
				(self.getCurrentParentId(), Node.nid2Name(nid), Node.nid2IsDirectory(nid)))
			result = cursor.fetchone() == None
			cursor.close()
			return result

	def getNodeByNid(self, nid):
		if self.__useBuffer:
			if self.exists(nid):
				return self.__buffer[nid]
			else:
				return None
		else:
			cursor = self.__dbcon.cursor()
			cursor.execute('select ' + self.__databaseSelectString + \
				' from nodes where parentkey=? and name=? and isdir=?', \
				(self.getCurrentParentId(), Node.nid2Name(nid), Node.nid2IsDirectory(nid)))
			row = cursor.fetchone()
			if row is None:
				return None
			node = self.__fetch(row)
			cursor.close()
			return node

	def __iter__(self):
		if self.__useBuffer:
			for nid in sorted(self.__buffer.keys()):
				yield self.__buffer[nid]
		else:
			cursor = self.__dbcon.cursor()
			cursor.execute('select ' + self.__databaseSelectString + \
				' from nodes where parentkey=?', (self.getCurrentParentId(),))
			for row in cursor:
				yield self.__fetch(row)
			cursor.close()

	def calculate(self, node):
		# nothing to do, just signal that the job is done if necessary
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), node.info.size)
			if self.signalBytesDone is not None:
				self.signalBytesDone(node.info.size)

	def globalGetPathsByChecksum(self, checksumString):
		result = set()
		cursor = self.__dbcon.cursor()
		cursor.execute('select nodekey from nodes where checksum=X\'{0:s}\''.format(checksumString))
		for row in cursor:
			result.add(self.IdToPath(row[0]))
		cursor.close()
		return result

	### the following methods are not implementations of base class methods

	def open(self):
		# if neither database file nor signature file exist, make a silent reset
		if not (os.path.exists(self.__databaseFile) and os.path.exists(self.__signatureFile)):
			self.reset()
		cs = Checksum()
		cs.calculateForFile(self.__databaseFile)
		if not cs.isValidUsingSavedFile(self.__signatureFile):
			raise MyException('The internal database has been corrupted.', 3)
		self.dbOpen()

	def isOpen(self):
		return not self.__dbcon is None

	def close(self):
		if self.isOpen():
			self.dbClose()
			cs = Checksum()
			cs.calculateForFile(self.__databaseFile)
			cs.saveToFile(self.__signatureFile)

	def dbOpen(self):
		self.__dbcon = sqlite3.connect(self.__databaseFile, \
			# necessary for proper retrival of datetime objects from the database,
			# otherwise the cursor will return string values with the timestamps
			detect_types=sqlite3.PARSE_DECLTYPES)
		# stores strings as ascii strings in the database, not as unicodes
		# makes program easily compatible with python 2.X but introduces
		# problems when file system supports unicode... :-(
		if sys.version[0] == '2':
			self.__dbcon.text_factory = str

	def dbClose(self):
		if self.__dbcon is not None:
			self.__dbcon.close()
			self.__dbcon = None

	def getCurrentParentId(self):
		return self.__parentKeyStack[-1]

	def getRootId(self):
		cursor = self.__dbcon.cursor()
		cursor.execute('select nodekey from nodes where parentkey is null')
		result = cursor.fetchone()[0]
		cursor.close()
		return result

	def IdToPath(self, nodeid):
		rootid = self.getRootId()
		currentid = nodeid
		namelist = []
		while not currentid == rootid:
			cursor = self.__dbcon.cursor()
			cursor.execute('select name,parentkey from nodes where nodekey=?', (currentid,))
			row = cursor.fetchone()
			namelist.append(row[0])
			currentid = row[1]
			cursor.close()
		return reduce(lambda x, y: os.path.join(x, y), reversed(namelist))

	def readCurrentDir(self):
		self.__buffer = {}
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where parentkey=?', (self.getCurrentParentId(),))
		for row in cursor:
			node = self.__fetch(row)
			self.__buffer[node.getNid()] = node
		cursor.close()

	def __fetch(self, row):
		node = Node(row[2])
		node.dbkey = row[0]
		if not row[3]:
			node.info = NodeInfo()
			node.info.size = row[4]
			node.info.ctime = row[5]
			node.info.atime = row[6]
			node.info.mtime = row[7]
			node.info.checksum = Checksum()
			node.info.checksum.setBinary(row[8])
		return node
