#!/usr/bin/env python

import binascii
import datetime
import hashlib
import os
import sqlite3
import sys
import wx

ProgramName = 'dtint'
ProgramVersion = '2.0'



def SizeToString(size):
	if size < 1000:
		sizestr = '{0:d}'.format(size)
	elif size < 1000**2:
		sizestr = '{0:.1f}K'.format(size/1000)
	elif size < 1000**3:
		sizestr = '{0:.1f}M'.format(size/1000**2)
	elif size < 1000**4:
		sizestr = '{0:.1f}G'.format(size/1000**3)
	elif size < 1000**5:
		sizestr = '{0:.1f}T'.format(size/1000**4)
	elif size < 1000**6:
		sizestr = '{0:.1f}P'.format(size/1000**5)
	else:
		sizestr = '{0:.1f}E'.format(size/1000**6)
	return sizestr + 'B'



class Checksum:

	def __init__(self):
		self.__checksum = None # is of type 'buffer'
		self.__checksumbits = 256

	def Calculate(self, path):
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

	def SetBinary(self, checksum):
		if not len(checksum) == self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = checksum

	def GetBinary(self):
		return self.__checksum

	def SetString(self, checksum):
		if not len(checksum) == 2*self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = binascii.unhexlify(checksum)

	def GetString(self, short=False):
		if self.__checksum == None:
			return '<none>'
		else:
			if short:
				return binascii.hexlify(self.__checksum[0:7]).decode('utf-8') + '...'
			else:
				return binascii.hexlify(self.__checksum).decode('utf-8')

	def WriteToFile(self, path):
		f = open(path, 'w')
		f.write(self.GetString())
		f.close()
		
	def IsValid(self, path):
		f = open(path, 'r')
		csum = f.read()
		f.close()
		return csum == self.GetString()

	def Print(self):
		print(self.GetString())

	def IsEqual(self, other):
		return self.GetString() == other.GetString()



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



class Node:

	def __init__(self):
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

	def Print(self, prefix=''):
		if self.nodeid == None:
			print('{0:s}nodeid              <unknown>'.format(prefix))
		else:
			print('{0:s}nodeid              {1:d}'.format(prefix, self.nodeid))
		if self.parentid == None:
			print('{0:s}parentid            <unknown>'.format(prefix))
		else:
			print('{0:s}parentid            {1:d}'.format(prefix, self.parentid))
		if self.name == None:
			print('{0:s}name                <unknown>'.format(prefix))
		else:
			print('{0:s}name                {1:s}'.format(prefix, self.name))
		if self.path == None:
			print('{0:s}path                <unknown>'.format(prefix))
		else:
			print('{0:s}path                {1:s}'.format(prefix, self.path))
		if self.isdir == None:
			print('{0:s}isdir               <unknown>'. format(prefix))
		else:
			print('{0:s}isdir               {1:b}'.format(prefix, self.isdir))
		if self.size == None:
			print('{0:s}size                <unknown>'. format(prefix))
		else:
			print('{0:s}size                {1:s}'.format(prefix, SizeToString(self.size)))
		if self.ctime == None:
			print('{0:s}creation time       <unknown>'.format(prefix))
		else:
			print('{0:s}creation time       {1:s}'.\
				format(prefix, self.ctime.strftime('%Y-%m-%d %H:%M:%S')))
		if self.atime == None:
			print('{0:s}access time         <unknown>'.format(prefix))
		else:
			print('{0:s}access time         {1:s}'.\
				format(prefix, self.atime.strftime('%Y-%m-%d %H:%M:%S')))
		if self.mtime == None:
			print('{0:s}modification time   <unknown>'.format(prefix))
		else:
			print('{0:s}modification time   {1:s}'.\
				format(prefix, self.mtime.strftime('%Y-%m-%d %H:%M:%S')))
		if self.checksum == None:
			print('{0:s}checksum            <unknown>'.format(prefix))
		else:
			cs = Checksum()
			cs.SetChecksum(self.checksum)
			print('{0:s}checksum            {1:s}'.\
				format(prefix, cs.GetChecksumString(True)))



class NodeTree:

	def __init__(self):
		self.__dict = {}

	def append(self, node):
		self.__dict[node.name] = node

	def __iter__(self):
		return self.__dict.itervalues()

	def __getitem__(self, key):
		return self.__dict.values().__getitem__(key)

	def PrintRecurse(self, nodelist, depth):
		for node in nodelist:
			node.Print(depth * '    ')
			#print((depth * '    ') + node.name)
			if not node.children == None:
				self.PrintRecurse(node.children, depth + 1)

	def Print(self):
		self.PrintRecurse(self, 0)



# --- SQL strings for database access ---
# Always keep in sync with Node and NodeInfo classes!
# Careful with changing spaces: some strings are auto-generated!
DatabaseCreateString = \
	'nodeid integer primary key,' + \
	'parent integer,' + \
	'name text,' + \
	'isdir boolean not null,' + \
	'size integer,' + \
	'ctime timestamp,' + \
	'atime timestamp,' + \
	'mtime timestamp,' + \
	'checksum blob'
DatabaseVarNames = [s.split(' ')[0] for s in DatabaseCreateString.split(',')]
DatabaseInsertVars = ','.join(DatabaseVarNames[1:])
DatabaseInsertQMarks = (len(DatabaseVarNames)-2) * '?,' + '?'
DatabaseSelectString = ','.join(DatabaseVarNames)
DatabaseUpdateString = '=?,'.join(DatabaseVarNames[1:]) + '=?'



class Database:

	def __init__(self, metaDir):
		if not os.path.exists(metaDir):
			raise MyException('Given meta data directory does not exist.', 3)
		if not os.path.isdir(metaDir):
			raise MyException('Given meta data directory is not a directory.', 3)
		self.__dbFile = os.path.join(metaDir, 'base.sqlite3')
		self.__sgFile = os.path.join(metaDir, 'base.signature')
		self.__dbcon = None

	def __del__(self):
		if self.IsOpen():
			self.CloseAndSecure()

	def Open(self):
		self.__dbcon = sqlite3.connect(self.__dbFile, \
			# necessary for proper retrival of datetime objects from the database,
			# otherwise the cursor will return string values with the timestamps
			detect_types=sqlite3.PARSE_DECLTYPES)
		# stores strings as ascii strings in the database, not as unicodes
		# makes program easily compatible with python 2.X but introduces
		# problems when file system supports unicode... :-(
		if sys.version[0] == '2':
			self.__dbcon.text_factory = str

	def CheckAndOpen(self):
		cs = Checksum()
		cs.CalculateChecksum(self.__dbFile)
		if not cs.IsValid(self.__sgFile):
			raise MyException('The internal database has been corrupted.', 3)
		self.Open()

	def Close(self):
		self.__dbcon.close()
		self.__dbcon = None

	def CloseAndSecure(self):
		self.Close()
		cs = Checksum()
		cs.CalculateChecksum(self.__dbFile)
		cs.WriteToFile(self.__sgFile)

	def IsOpen(self):
		return not self.__dbcon == None

	def Reset(self):
		# close if it was open
		wasOpen = self.IsOpen()
		if wasOpen:
			self.Close()
		# delete files if existing
		if os.path.exists(self.__dbFile):
			os.remove(self.__dbFile)
		if os.path.exists(self.__sgFile):
			os.remove(self.__sgFile)
		# create database
		self.Open()
		self.__dbcon.execute('create table nodes (' + DatabaseCreateString + ')')
		self.CloseAndSecure()
		# reopen if necessary
		if wasOpen:
			self.CheckAndOpen()

	def GetRootNodeList(self):
		node = Node()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent is null')
		self.Fetch(node, cursor.fetchone())
		cursor.close()
		result = NodeTree()
		result.append(node)
		return result

	def Fetch(self, node, row):
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
			node.checksum.SetBinary(row[8])
	
	def GetChildren(self, node):
		result = NodeTree()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent=?', (node.nodeid,))
		for row in cursor:
			child = Node()
			self.Fetch(child, row)
			result.append(child)
		cursor.close()
		return result	
		
	def InsertNode(self, node):
		if not node.nodeid == None:
			raise MyException('Node already contains a valid node id, ' + \
				'so maybe you want to update instead of insert?', 3)
		cursor = self.__dbcon.cursor()
		cursor.execute('insert into nodes (' + DatabaseInsertVars + \
			') values (' + DatabaseInsertQMarks + ')', \
			(node.parentid, node.name, node.isdir, node.size, \
			node.ctime, node.atime, node.mtime, node.checksum))
		node.nodeid = cursor.lastrowid
		cursor.close()
		
	def Commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')



class Filesystem:

	def __init__(self, rootDir, metaDir):
		if not os.path.exists(rootDir):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(rootDir):
			raise MyException('Given root directory is not a directory.', 3)
		self.__rootDir = rootDir
		if not os.path.exists(metaDir):
			raise MyException('Given meta data directory does not exist.', 3)
		if not os.path.isdir(metaDir):
			raise MyException('Given meta data directory is not a directory.', 3)
		self.__metaDir = metaDir

	def Reset(self):
		if not os.path.exists(self.__metaDir):
			os.mkdir(self.__metaDir)

	def GetRootNodeList(self):
		node = Node()
		node.name = ''
		node.path = self.__rootDir
		self.Fetch(node)
		result = NodeTree()
		result.append(node)
		return result

	def Fetch(self, node):
		node.isdir = os.path.isdir(node.path)
		node.size = os.path.getsize(node.path)
		# this conversion from unix time stamp to local date/time might fail after year 2038...
		node.ctime = datetime.datetime.fromtimestamp(os.path.getctime(node.path))
		node.atime = datetime.datetime.fromtimestamp(os.path.getatime(node.path))
		node.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(node.path))
		if not node.isdir:
			cs = Checksum()
			cs.CalculateChecksum(node.path)
			node.checksum = cs.GetChecksum()

	def GetChildren(self, node):
		result = NodeTree()
		for childname in os.listdir(node.path):
			childpath = os.path.join(node.path, childname)
			if childpath == self.__metaDir:
				continue
			child = Node()
			child.name = childname
			child.path = childpath
			child.parentid = node.nodeid
			self.Fetch(child)
			result.append(child)
		return result



class Instance:

	def __init__(self, rootDir):
		if not os.path.exists(rootDir):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(rootDir):
			raise MyException('Given root directory is not a directory.', 3)
		metaDir = os.path.join(rootDir, '.' + ProgramName)
		self.__fs = Filesystem(rootDir, metaDir)
		self.__db = Database(metaDir)

	def Reset(self):
		self.__fs.Reset()
		self.__db.Reset()

	def Open(self):
		self.__db.CheckAndOpen()

	def Close(self):
		self.__db.CloseAndSecure()
		
	def ImportRecurse(self, nodelist):
		for node in nodelist:
			self.__db.InsertNode(node)
			if node.isdir:
				self.ImportRecurse(self.__fs.GetChildren(node))

	def Import(self):
		self.ImportRecurse(self.__fs.GetRootNodeList())
		self.__db.Commit()

	def GetTreeRecurse(self, nodetree, skipValids):
		for node in nodetree:
			if node.isdir:
				node.children = self.__fs.GetChildren(node)
				self.GetTreeRecurse(node.children, skipValids)

	def GetTree(self, skipValids=True):
		nodetree = self.__fs.GetRootNodeList()
		self.GetTreeRecurse(nodetree, skipValids)
		return nodetree



inst = Instance('../dtint-example')
inst.Reset()
inst.Open()
inst.Import()
t = inst.GetTree(False)
t.Print()
inst.Close()
