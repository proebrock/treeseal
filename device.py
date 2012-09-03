import datetime
import os
import sqlite3
import sys

from misc import MyException, Checksum
from node import NodeStatus, NodeInfo, Node, NodeStatistics, NodeList, NodeDict



class Device(object):

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

	def updateNode(self, node):
		raise MyException('Not implemented.', 3)

	def deleteNode(self, node):
		raise MyException('Not implemented.', 3)

	def commit(self):
		raise MyException('Not implemented.', 3)

	def registerHandlers(self, signalNewFile, signalBytesDone):
		self.signalNewFile = signalNewFile
		self.signalBytesDone = signalBytesDone

	def __getNodeTree(self, nodetree):
		for node in nodetree:
			self.calculate(node)
			if node.isDirectory():
				node.children = self.getChildren(node)
				self.__getNodeTree(node.children)

	def getNodeTree(self):
		nodetree = NodeDict()
		nodetree.append(self.getRootNode())
		self.__getNodeTree(nodetree)
		return nodetree

	def __copyNodeTree(self, dest, nodes):
		for node in nodes:
			self.calculate(node)
			dest.insertNode(node)
			if node.isDirectory():
				self.__copyNodeTree(dest, self.getChildren(node))

	def copyNodeTree(self, dest):
		nodes = NodeDict()
		nodes.append(self.getRootNode())
		self.__copyNodeTree(dest, nodes)
		dest.commit()

	def __recursiveGetStatistics(self, nodes, stats):
		for node in nodes:
			stats.update(node)
			if node.isDirectory():
				self.__recursiveGetStatistics(self.getChildren(node), stats)

	def getStatistics(self, node):
		stats = NodeStatistics()
		nodes = NodeDict()
		nodes.append(node)
		self.__recursiveGetStatistics(nodes, stats)
		return stats

	def __recursiveGetDiffTree(self, other, selfnodes, othernodes, removeOkNodes):
		okNodes = []
		for snode in selfnodes:
			self.calculate(snode)
			onode = othernodes.getByUniqueID(snode.getUniqueKey())
			if not onode is None:
				# nodes existing in selfnodes and othernodes: already known nodes
				self.transferUniqueInformation(onode, snode)
				other.transferUniqueInformation(snode, onode)
				other.calculate(onode)
				if snode.isDirectory():
					# get children, but chain the tree just for self not for other
					snode.children = self.getChildren(snode)
					onode_children = other.getChildren(onode)
					self.__recursiveGetDiffTree(other, snode.children, onode_children, removeOkNodes)
					# set node status (after statuses of children are known)
					if len(snode.children) == 0:
						snode.status = NodeStatus.OK
					else:
						snode.status = snode.children[0].status
						for i in range(1, len(snode.children)):
							if not snode.status == snode.children[i].status:
								snode.status = NodeStatus.Unknown
								break
				else:
					# save other node
					snode.other = onode
					# compare snode and onode and set status
					if snode.info == onode.info:
						if snode.info.checksum == onode.info.checksum:
							snode.status = NodeStatus.OK
						else:
							snode.status = NodeStatus.Error
					else:
						snode.status = NodeStatus.Warn
				if removeOkNodes:
					# collect nodes to delete, we cannot delete them from
					# selfnodes because we are iterating over it
					if snode.status == NodeStatus.OK:
						okNodes.append(snode.getUniqueKey())
				othernodes.delByUniqueID(onode.getUniqueKey())
			else:
				# nodes existing in selfnodes but not in othernodes: new nodes
				snode.status = NodeStatus.New
				if snode.isDirectory():
					snode.children = self.getChildren(snode)
					self.__getNodeTree(snode.children)
					snode.children.setStatus(NodeStatus.New)
		# remove nodes marked as ok
		if removeOkNodes:
			for s in okNodes:
				selfnodes.delByUniqueID(s)
		# nodes existing in othernodes but not in selfnodes: missing nodes
		for onode in othernodes:
			other.calculate(onode)
			onode.status = NodeStatus.Missing
			if onode.isDirectory():
				onode.children = other.getChildren(onode)
				other.__getNodeTree(onode.children)
				onode.children.setStatus(NodeStatus.Missing)
		selfnodes.mergeAndUpdate(othernodes)

	def recursiveGetDiffTree(self, other, removeOkNodes=True):
		selfnodes = NodeDict()
		selfnodes.append(self.getRootNode())
		othernodes = NodeDict()
		othernodes.append(other.getRootNode())
		self.__recursiveGetDiffTree(other, selfnodes, othernodes, removeOkNodes)
		if len(selfnodes) == 0:
			# keep housekeeping root node with empty children
			# if all nodes have been removed by removeOkNodes feature
			node = self.getRootNode()
			node.children = NodeDict()
			selfnodes.append(node)
		return selfnodes



class Database(Device):

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
		if not row[3]:
			node.info = NodeInfo()
			node.info.size = row[4]
			node.info.ctime = row[5]
			node.info.atime = row[6]
			node.info.mtime = row[7]
			node.info.checksum = Checksum()
			node.info.checksum.setBinary(row[8])

	def calculate(self, node):
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, 0)
		else:
			# nothing to do, just signal that the job is done if necessary
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, node.info.size)
			if self.signalBytesDone is not None:
				self.signalBytesDone(node.info.size)

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
			child.chainWithParent(node)
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
		if node.isDirectory():
			cursor.execute('insert into nodes (' + self.__databaseInsertVars + \
				') values (' + self.__databaseInsertQMarks + ')', \
				(node.parentid, node.name, True, None, \
				None, None, None, None))
		else:
			cursor.execute('insert into nodes (' + self.__databaseInsertVars + \
				') values (' + self.__databaseInsertQMarks + ')', \
				(node.parentid, node.name, False, node.info.size, \
				node.info.ctime, node.info.atime, node.info.mtime, \
				node.info.checksum.getBinary()))
		node.nodeid = cursor.lastrowid
		if not node.children is None:
			for child in node.children:
				child.chainWithParent(node)
		cursor.close()

	def updateNode(self, node):
		if node.nodeid is None:
			raise MyException('Node does not contain a valid node id, ' + \
			'so maybe you want to insert instead of update?', 3)
		if node.isDirectory():
			self.__dbcon.execute('update nodes set ' + self.__databaseUpdateString + \
				' where nodeid=?', \
				(node.parentid, node.name, True, None, \
				None, None, None, None, node.nodeid))
		else:
			self.__dbcon.execute('update nodes set ' + self.__databaseUpdateString + \
				' where nodeid=?', \
				(node.parentid, node.name, False, node.info.size, \
				node.info.ctime, node.info.atime, node.info.mtime, \
				node.info.checksum.getBinary(), node.nodeid))

	def deleteNode(self, node):
		self.__dbcon.execute('delete from nodes where nodeid=?', (node.nodeid,))

	def commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')

	### following methods are Database specific and not from Device

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



class Filesystem(Device):

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
		if not os.path.isdir(fullpath):
			node.info = NodeInfo()
			node.info.size = os.path.getsize(fullpath)
			# this conversion from unix time stamp to local date/time might fail after year 2038...
			node.info.ctime = datetime.datetime.fromtimestamp(os.path.getctime(fullpath))
			node.info.atime = datetime.datetime.fromtimestamp(os.path.getatime(fullpath))
			node.info.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))

	def calculate(self, node):
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(node.path, node.info.size)
			fullpath = os.path.join(self.__rootDir, node.path)
			node.info.checksum = Checksum()
			node.info.checksum.calculateForFile(fullpath, self.signalBytesDone)

	def transferUniqueInformation(self, destNode, srcNode):
		destNode.path = srcNode.path

	def getChildren(self, node):
		result = NodeDict()
		for childname in os.listdir(os.path.join(self.__rootDir, node.path)):
			childpath = os.path.join(node.path, childname)
			if self.__isBlacklisted(os.path.join(self.__rootDir, childpath)):
				continue
			child = Node()
			child.path = childpath
			self.fetch(child)
			child.chainWithParent(node)
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

	def insertNode(self, node):
		# a node contains the metadata necessary to create the file,
		# instead of the file content just its checksum...
		print('Filesystem.insertNode(\'' + node.name + '\') is not implemented.')

	def updateNode(self, node):
		# a node contains the metadata necessary to update the file,
		# instead of the file content just its checksum...
		print('Filesystem.updateNode(\'' + node.name + '\') is not implemented.')

	def deleteNode(self, node):
		fullpath = os.path.join(self.__rootDir, node.path)
		if node.isDirectory():
			os.rmdir(fullpath)
		else:
			os.remove(fullpath)

	def commit(self):
		pass

	### following methods are Database specific and not from Device

	def __isBlacklisted(self, path):
		# skip the metadir, we do not want to add that to the database
		if path == self.__metaDir:
			return True
		return False



class XmlFile(Device):
	pass
