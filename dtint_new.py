#!/usr/bin/env python

import binascii
import hashlib
import os
import sqlite3
import sys
import wx

ProgramName = 'dtint'
ProgramVersion = '2.0'



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



class Node:

	def __init__(self):
		self.path = None
		self.dbcon = None
	
		self.nodeid = None
		self.name = None
		
		self.dbInfo = NodeInfo()
		self.fsInfo = NodeInfo()



DatabaseCreateString = \
	'nodeid integer primary key,' + \
	'parent integer,' + \
	'name text not null,' + \
	'isdir boolean not null,' + \
	'size integer,' + \
	'ctime timestamp,' + \
	'atime timestamp,' + \
	'mtime timestamp,' + \
	'checksum blob'



class Database:

	def __init__(self, path):
		self.__dbfile = path + '.sqlite3'
		self.__sigfile = path + '.signature'
		self.__dbcon = None

	def __del__(self):
		if self.IsOpen():
			self.CloseAndSecure()

	def Open(self):
		self.__dbcon = sqlite3.connect(self.__dbfile, \
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
		cs.CalculateChecksum(self.__dbfile)
		if not cs.IsValid(self.__sigfile):
			raise MyException('The internal database has been corrupted.', 3)
		self.Open()
		
	def Close(self):
		self.__dbcon.close()
		self.__dbcon = None
			
	def CloseAndSecure(self):
		self.Close()
		cs = Checksum()
		cs.CalculateChecksum(self.__dbfile)
		cs.WriteToFile(self.__sigfile)
	
	def IsOpen(self):
		return not self.__dbcon == None
	
	def Reset(self):
		# close if it was open
		wasOpen = self.IsOpen()
		if wasOpen:
			self.Close()
		# delete files if existing
		if os.path.exists(self.__dbfile):
			os.remove(self.__dbfile)
		if os.path.exists(self.__sigfile):
			os.remove(self.__sigfile)
		# create database
		self.Open()
		self.__dbcon.execute('create table nodes (' + DatabaseCreateString + ')')
		self.CloseAndSecure()
		# reopen if necessary
		if wasOpen:
			self.CheckAndOpen()



class Main:

	def __init__(self, path):
		self.__rootDir = path
		self.__metaDir = os.path.join(self.__rootDir, '.' + ProgramName)
		self.__db = Database(os.path.join(self.__metaDir, 'base'))

	def Reset(self):
		if not os.path.exists(self.__metaDir):
			os.mkdir(self.__metaDir)
		self.__db.Reset()

	def Open(self):
		self.__db.CheckAndOpen()

	def Close(self):
		self.__db.CloseAndSecure()



m = Main('/home/roebrocp/Projects/dtint-example')
m.Reset()
m.Open()
m.Close()	
		
		
