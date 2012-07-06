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
		self.__checksum = None

	def CalculateChecksum(self, path):
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

	def SetChecksum(self, checksum):
		self.__checksum = checksum

	def GetChecksum(self):
		return self.__checksum

	def GetChecksumString(self, short=False):
		if self.__checksum == None:
			return '<none>'
		else:
			if short:
				return binascii.hexlify(self.__checksum[0:7]).decode('utf-8') + '...'
			else:
				return binascii.hexlify(self.__checksum).decode('utf-8')

	def WriteToFile(self, path):
		f = open(path, 'w')
		f.write(self.GetChecksumString())
		f.close()
		
	def IsValid(self, path):
		f = open(path, 'r')
		csum = f.read()
		f.close()
		return csum == self.GetChecksumString()



class MyException(Exception):

	def __init__(self, message, level):
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



class NodeInfo:

	def __init__(self):
		self.isdir = None
		self.size = None
		self.ctime = None
		self.atime = None
		self.mtime = None
		self.checksum = None

	def Print(self, prefix=''):
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

class Node:

	def __init__(self):
		# unique identifiers in filesystem and database
		self.name = None
		self.path = None
		self.nodeid = None
		# data
		self.fsInfo = None
		self.dbInfo = None
		
	def Print(self, prefix=''):
		if self.name == None:
			print('{0:s}name                <unknown>'.format(prefix))
		else:
			print('{0:s}name                {1:s}'.format(prefix, self.name))
		if self.path == None:
			print('{0:s}path                <unknown>'.format(prefix))
		else:
			print('{0:s}path                {1:s}'.format(prefix, self.path))
		if self.nodeid == None:
			print('{0:s}nodeid              <unknown>'.format(prefix))
		else:
			print('{0:s}nodeid              {1:d}'.format(prefix, self.nodeid))
		print('{0:s}info in filesystem:'.format(prefix))
		if self.fsInfo == None:
			print('{0:s}<unknown>'.format(prefix + '  '))
		else:
			self.fsInfo.Print(prefix + '  ')
		print('{0:s}info in database:'.format(prefix))
		if self.dbInfo == None:
			print('{0:s}<unknown>'.format(prefix + '  '))
		else:
			self.dbInfo.Print(prefix + '  ')



class NodeList(list):
	
	def Print(self):
		for node in self:
			node.Print()
		



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
DatabaseVarNames = map(lambda s: s.split(' ')[0], DatabaseCreateString.split(','))
DatabaseInsertVars = ','.join(DatabaseVarNames[1:])
DatabaseInsertQMarks = (len(DatabaseVarNames)-2) * '?,' + '?'
DatabaseSelectString = ','.join(DatabaseVarNames)
DatabaseUpdateString = '=?,'.join(DatabaseVarNames[1:]) + '=?'



class Database:

	def __init__(self, metaDir):
		if not os.path.isdir(metaDir):
			raise MyException('Given meta directory is not a directory.', 3)
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

	def GetRootNode(self):
		node = Node()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent is null')
		self.Fetch(node, cursor.fetchone())
		cursor.close()
		return node


	def Fetch(self, node, row):
		node.nodeid = row[0]
		# ignore parentid in row[1]
		node.name = row[2]
		node.dbInfo = NodeInfo()
		node.dbInfo.isdir = row[3]
		node.dbInfo.size = row[4]
		node.dbInfo.ctime = row[5]
		node.dbInfo.atime = row[6]
		node.dbInfo.mtime = row[7]
		node.dbInfo.checksum = row[8]
	
	def GetChildren(self, node):
		result = NodeList()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent=?', (node.nodeid,))
		for row in cursor:
			child = Node()
			self.Fetch(child, row)
			result.append(child)
		cursor.close()
		return result	
		
	def InsertNode(self, node, parentnode=None):
		if node.dbInfo == None:
			raise MyException('Cannot write an empty node to database.', 3)
		if not node.nodeid == None:
			raise MyException('Node already contains a valid node id, ' + \
				'so maybe you want to update instead of insert?', 3)
		if parentnode == None:
			parentid = None
		else:
			parentid = parentnode.nodeid
		cursor = self.__dbcon.cursor()
		cursor.execute('insert into nodes (' + DatabaseInsertVars + \
			') values (' + DatabaseInsertQMarks + ')', \
			(parentid, node.name, node.dbInfo.isdir, node.dbInfo.size, \
			node.dbInfo.ctime, node.dbInfo.atime, node.dbInfo.mtime, \
			node.dbInfo.checksum))
		node.nodeid = cursor.lastrowid
		cursor.close()
		
	def Commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')



class Filesystem:

	def __init__(self, rootDir, metaDir):
		if not os.path.isdir(metaDir):
			raise MyException('Given root directory is not a directory.', 3)
		self.__rootDir = rootDir
		self.__metaDir = metaDir

	def Reset(self):
		if not os.path.exists(self.__metaDir):
			os.mkdir(self.__metaDir)

	def GetRootNode(self):
		node = Node()
		node.name = ''
		node.path = self.__rootDir
		self.Fetch(node)
		return node

	def Fetch(self, node):
		node.fsInfo = NodeInfo()
		node.fsInfo.isdir = os.path.isdir(node.path)
		node.fsInfo.size = os.path.getsize(node.path)
		# this conversion from unix time stamp to local date/time might fail after year 2038...
		node.fsInfo.ctime = datetime.datetime.fromtimestamp(os.path.getctime(node.path))
		node.fsInfo.atime = datetime.datetime.fromtimestamp(os.path.getatime(node.path))
		node.fsInfo.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(node.path))
		if not node.fsInfo.isdir:
			cs = Checksum()
			cs.CalculateChecksum(node.path)
			node.fsInfo.checksum = cs.GetChecksum()

	def GetChildren(self, node):
		result = NodeList()
		for childname in os.listdir(node.path):
			childpath = os.path.join(node.path, childname)
			if childpath == self.__metaDir:
				continue
			child = Node()
			child.name = childname
			child.path = childpath
			self.Fetch(child)
			result.append(child)
		return result



class Main:

	def __init__(self, rootDir):
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
		
	def ImportRecurse(self, nodelist, parentnode):
		for node in nodelist:
			node.dbInfo = node.fsInfo
			self.__db.InsertNode(node, parentnode)
			if node.fsInfo.isdir:
				self.ImportRecurse(self.__fs.GetChildren(node), node)

	def Import(self):
		nodelist = NodeList()
		nodelist.append(self.__fs.GetRootNode())
		self.ImportRecurse(nodelist, None)
		self.__db.Commit()



m = Main('/home/roebrocp/Projects/dtint-example')
m.Reset()
m.Open()
m.Import()
m.Close()	

