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

		self.__dbcon = None
		self.open()

		# --- SQL strings for database access ---
		# Always keep in sync with Node and NodeInfo classes!
		# Careful with changing spaces: some strings are auto-generated!
		self.__databaseCreateString = \
			'nodeid integer primary key,' + \
			'parent integer,' + \
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

		self.gotoRoot()

	def __del__(self):
		self.close()

	### implementation of base class methods, please keep order

	def getDepth(self):
		return len(self.__parentIdStack) - 1

	def getPath(self):
		return reduce(lambda x, y: os.path.join(x, y), self.__parentNameStack)

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
		self.__parentIdStack = [ self.getRootId() ]
		self.__parentNameStack = [ '' ]

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		self.__parentIdStack.pop()
		self.__parentNameStack.pop()

	def down(self, name):
		node = self.getNodeByName(name)
		if node is None:
			raise MyException('No node \'' + name + '\' in current dir.', 3)
		if not node.isDirectory():
			raise MyException('\'down\' on file \'' + name + '\' is not possible.', 3)
		self.__parentIdStack.append(node.nodeid)
		self.__parentNameStack.append(node.name)

	def insert(self, node):
		if not node.nodeid is None:
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
		node.nodeid = cursor.lastrowid
		cursor.close()

	def update(self, node):
		if node.nodeid is None:
			raise MyException('Node does not contain a valid node id, ' + \
				'so maybe you want to insert instead of update?', 3)
		if node.isDirectory():
			self.__dbcon.execute('update nodes set ' + self.__databaseUpdateString + \
				' where nodeid=?', \
				(self.getCurrentParentId(), node.name, True, None, \
				None, None, None, None, node.nodeid))
		else:
			self.__dbcon.execute('update nodes set ' + self.__databaseUpdateString + \
				' where nodeid=?', \
				(self.getCurrentParentId(), node.name, False, node.info.size, \
				node.info.ctime, node.info.atime, node.info.mtime, \
				node.info.checksum.getBinary(), node.nodeid))

	def delete(self, name):
		self.__dbcon.execute('delete from nodes where parent=? and name=?', (self.getCurrentParentId(),name))

	def commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')

	def getNodeByName(self, name):
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where parent=? and name=?', (self.getCurrentParentId(), name))
		node = Node()
		self.__fetch(node, cursor.fetchone())
		cursor.close()
		return node

	def __iter__(self):
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + self.__databaseSelectString + \
			' from nodes where parent=?', (self.getCurrentParentId(),))
		for row in cursor:
			node = Node()
			self.__fetch(node, row)
			yield node
		cursor.close()

	### the following methods are not implementations of base class methods

	def open(self):
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
		self.__dbcon.close()
		self.__dbcon = None

	def getCurrentParentId(self):
		return self.__parentIdStack[-1]

	def getRootId(self):
		cursor = self.__dbcon.cursor()
		cursor.execute('select nodeid from nodes where parent is null')
		result = cursor.fetchone()[0]
		cursor.close()
		return result

	def __fetch(self, node, row):
		node.nodeid = row[0]
		#node.parentid = row[1] # TODO: remove later
		node.name = row[2]
		if not row[3]:
			node.info = NodeInfo()
			node.info.size = row[4]
			node.info.ctime = row[5]
			node.info.atime = row[6]
			node.info.mtime = row[7]
			node.info.checksum = Checksum()
			node.info.checksum.setBinary(row[8])
		if self.doCalculate:
			self.__calculate(node)

	def __calculate(self, node):
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, 0)
		else:
			# nothing to do, just signal that the job is done if necessary
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, node.info.size)
			if self.signalBytesDone is not None:
				self.signalBytesDone(node.info.size)











