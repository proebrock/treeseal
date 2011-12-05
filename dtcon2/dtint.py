import sqlite3
import sys
import os
import hashlib
import shlex
import subprocess
import time
import datetime
import binascii
import argparse
import textwrap



# ==================================================================
# ============================== Util ==============================
# ==================================================================

ProgramName = 'dtint'
ProgramVersion = '2.0'

def SizeToString(size):
	"""
	Return string with (file) size with appropriate SI prefix
	"""
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

def GetChecksum(path):
	"""
	Calculate checksum of a file by blockwise reading and processing the file content
	"""
	checksum = hashlib.sha256()
	buffersize = 2**20
	f = open(path,'rb')
	while True:
		data = f.read(buffersize)
		if not data:
			break
		checksum.update(data)
	f.close()
	return checksum.digest()

def ChecksumToString(checksum, shorten=False):
	"""
	Calculate checksum of a file by reading the directory contents.
	Checksum can be shortened in order to have a more compact display.
	"""
	if checksum == None:
		return '<none>'
	else:
		if shorten:
			return binascii.hexlify(checksum[0:7]).decode('utf-8') + '...'
		else:
			return binascii.hexlify(checksum).decode('utf-8')



# ======================================================================
# ============================== LogEntry ==============================
# ======================================================================

class LogEntry:

	def __init__(self, level, message, path=None):
		"""
		Constructor of LogEntry class
		"""
		self.__time = datetime.datetime.now()
		self.__level = level
		self.__message = message
		self.__path = path
	
	def ToString(self, showdate=True, showlevel=True):
		"""
		Covert log entry to string (long format is default)
		"""
		result = ''
		if showdate:
			result += self.__time.strftime('%Y-%m-%d %H:%M:%S')
			result += ' '
		if self.__level == 0:
			pass
		elif self.__level == 1:
			result += 'Warning: '
		elif self.__level == 2:
			result += 'Error: '
		elif self.__level == 3:
			result += '### Fatal Error: '
		else:
			raise Exception('Unknown log level {0:d}'.format(self.__level))
		result += self.__message
		if self.__path != None:
			result += ' ' + self.__path
		return result
	
	def Print(self, showdate=True, showlevel=True):
		"""
		Print log entry to console
		"""
		print(self.ToString(showdate, showlevel))
	
	def Write(self, f,showdate=True, showlevel=True):
		"""
		Write log entry to file
		"""
		f.write(self.ToString(showdate, showlevel) + '\n')

class LogFacility:

	def __init__(self, path):
		"""
		Constructor of LogFacility class
		"""
		self.__starttime = time.clock()
		self.__warnings = []
		self.__errors = []
		self.__fatalerrors = []
		if path != None:
			self.__f = open(path, 'a')
		else:
			self.__f = None

	def ClearBuffers(self):
		"""
		Clear all buffers
		"""
		self.__warnings = []
		self.__errors = []
		self.__fatalerrors = []

	def __del__(self):
		"""
		Destructor of LogFacility class
		"""
		if self.__f != None:
			self.__f.close()
		print('elapsed time ' + self.ElapsedTimeStr())
		if len(self.__fatalerrors) > 0:
			print('\n{0:d} fatal errors:'.format(len(self.__fatalerrors)))
			for f in self.__fatalerrors:
				f.Print(False, False)
		if len(self.__errors) > 0:
			print('\n{0:d} errors:'.format(len(self.__errors)))
			for e in self.__errors:
				e.Print(False, False)
		if len(self.__warnings) > 0:
			print('\n{0:d} warnings:'.format(len(self.__warnings)))
			for w in self.__warnings:
				w.Print(False, False)
		if (len(self.__warnings) == 0) and (len(self.__errors) == 0) and (len(self.__fatalerrors) == 0):
			print('\nno warnings, errors or fatal errors')
		else:
			input("\nPress any key ...") 

	def Print(self, level, message, path=None):
		"""
		Print message of certain importance level. Printing is handled by the log facility.
		Importance levels are: 0 - Notice, 1 - Warning, 2 - Error, 3 - Fatal Error
		"""
		# create log entry
		entry = LogEntry(level, message, path)
		# determine if and where message entry should be saved (not for Notice level)
		if level == 0:
			pass
		elif level == 1:
			self.__warnings.append(entry)
		elif level == 2:
			self.__errors.append(entry)
		elif level == 3:
			self.__fatalerrors.append(entry)
		else:
			raise Exception('Unknown log level {0:d}'.format(level))
		# write message to different targets
		entry.Print(False, True)
		if self.__f != None:
			entry.Write(self.__f)
		# if fatal, exit program
		if level == 3:
			sys.exit()

	def ElapsedTime(self):
		"""
		Determine elapsed time since start of the program.
		(Or more exactly: since instantiation of an object of this class)
		"""
		return time.clock() - self.__starttime

	def ElapsedTimeStr(self):
		"""
		Determine elapsed time since start of the program as a string.
		"""
		elapsed = self.ElapsedTime()
		if elapsed < 1:
			return '{0:.1f}ms'.format(elapsed*1000)
		elif elapsed < 60:
			return '{0:.1f}s'.format(elapsed)
		elif elapsed < 60 * 60:
			return '{0:.1f}min'.format(elapsed/60)
		elif elapsed < 24 * 60 * 60:
			return '{0:.1f}h'.format(elapsed/60/60)
		else:
			return '{0:.1f}d'.format(elapsed/24/60/60)

"""
Central facility for logging purposes used by all methods.
"""
log = LogFacility(ProgramName + '.log')



# ==================================================================
# ============================== Node ==============================
# ==================================================================

NodeInsertString = 'parent,name,isdir,size,ctime,atime,mtime,checksum'
NodeSelectString = 'nodeid,' + NodeInsertString
NodeUpdateString = '=?,'.join(NodeInsertString.rsplit(',')) + '=?'

class Node:

	def __init__(self):
		"""
		Constructor of Node class
		"""
		self.nodeid = None
		self.parent = None
		self.depth = None
		self.name = None
		self.path = None
		self.isdir = None
		self.size = None
		self.ctime = None
		self.atime = None
		self.mtime = None
		self.checksum = None

	def FetchFromDatabaseRow(self, row):
		"""
		When database was read using a cursor, this method is used to extract
		information from a cursor row into a node.
		Some information cannot be retrieved from the database row, check
		comments below.
		"""
		self.nodeid = row[0]
		self.parent = row[1]
		# self.depth has to be set while traversing
		self.name = row[2]
		# self.path has to be set while traversing
		self.isdir = row[3]
		self.size = row[4]
		self.ctime = row[5]
		self.atime = row[6]
		self.mtime = row[7]
		self.checksum = row[8]
	
	def FetchFromDirectory(self, path, name):
		"""
		When a directory was searched for file names, this method is used to
		extract information into a node. "path" is the full featured
		directory path of the node, name is the name under which the node
		is stored in the database (full featured path for root node, file
		name or directory name otherwise)
		Some information cannot be retrieved from the database row, check
		comments below.
		"""
		# self.nodeid is set after writing to database
		# self.parent has to be set while traversing
		# self.depth has to be set while traversing
		if name == None:
			self.name = path
		else:
			self.name = name
		self.path = path
		if not os.path.exists(self.path):
			return
		self.isdir = os.path.isdir(self.path)
		if not self.isdir:
			self.size = os.path.getsize(self.path)
		# this conversion from unix time stamp to local date/time might fail after year 2038...
		self.ctime = datetime.datetime.fromtimestamp(os.path.getctime(self.path))
		self.atime = datetime.datetime.fromtimestamp(os.path.getatime(self.path))
		self.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))
		if not self.isdir:
			self.checksum = GetChecksum(self.path)
	
	def DictKey(self):
		"""
		When building up a dictionary with directory entries as keys,
		it is not enough to use the file names because there might be a 
		directory and a file both with the same name. This method returns
		a flag indicating if the file is a directory or not and the file name
		"""
		return '{0:b}{1:s}'.format(self.isdir, self.name)

	def WriteToDatabase(self, dbcon):
		"""
		Write node (NOT EXISTING in database) to database
		and set nodeid due to the one received from the database
		"""
		cursor = dbcon.cursor()
		cursor.execute('insert into nodes (' + NodeInsertString + \
			') values (?,?,?,?,?,?,?,?)', \
			(self.parent, self.name, self.isdir, self.size, \
			self.ctime, self.atime, self.mtime, self.checksum))
		self.nodeid = cursor.lastrowid
		cursor.close()
	
	def UpdateDatabase(self, dbcon):
		"""
		Write node (ALREADY EXISTING in database) to database
		"""
		dbcon.execute('update nodes set ' + NodeUpdateString + ' where nodeid=?',\
			(self.parent, self.name, self.isdir, self.size, \
			self.ctime, self.atime, self.mtime, self.checksum, self.nodeid))
	
	def Compare(self, other):
		"""
		Compare the properties of two nodes. This function is called when
		checking information stored in the database with the current situation
		on the disk.
		"""
		#self.Print(None)
		#other.Print(None)
		if self.isdir and not other.isdir:
			log.Print(2, 'Directory became a file.', self.path)
		if not self.isdir and other.isdir:
			log.Print(2, 'File became a directory.', self.path)
		if not (self.isdir or other.isdir):
			if self.checksum != other.checksum:
				message = 'Checksum error for ' + self.path
				sameMetaData = True
				if self.size != other.size:
					message += ', file size changed ({0:d} -> {1:d})'.\
						format(self.size, other.size)
					sameMetaData = False
				if self.ctime != other.ctime:
					message += ', ctime changed ({0:s} -> {1:s})'.\
						format(self.ctime.strftime('%Y-%m-%d %H:%M:%S'), \
							other.ctime.strftime('%Y-%m-%d %H:%M:%S'))
					sameMetaData = False
				if self.atime != other.atime:
					message += ', atime changed ({0:s} -> {1:s})'.\
						format(self.atime.strftime('%Y-%m-%d %H:%M:%S'), \
							other.atime.strftime('%Y-%m-%d %H:%M:%S'))
					sameMetaData = False
				if self.mtime != other.mtime:
					message += ', mtime changed ({0:s} -> {1:s})'.\
						format(self.mtime.strftime('%Y-%m-%d %H:%M:%S'), \
							other.mtime.strftime('%Y-%m-%d %H:%M:%S'))
					sameMetaData = False
				if sameMetaData:
					message += ', file meta info seems to be the same but checksum changed, THIS IS SERIOUS!'
				log.Print(2, message)
			
	
	def Print(self, numindent=0):
		"""
		Print details about current node into the log facility
		"""
		if numindent == None:
			prefix = ''
		else:
			prefix = '  ' * numindent
		print('{0:s}node'.format(prefix))
		prefix += '->'
		if self.nodeid != None:
			print('{0:s}nodeid              {1:d}'.\
				format(prefix, self.nodeid))
		else:
			print('{0:s}nodeid              <none>'.\
				format(prefix))
		if self.parent != None:
			print('{0:s}parent              {1:d}'.\
				format(prefix, self.parent))
		else:
			print('{0:s}parent              <none>'.\
				format(prefix))
		if self.depth != None:
			print('{0:s}depth               {1:d}'\
				.format(prefix, self.depth))
		print('{0:s}name                {1:s}'.\
			format(prefix, self.name))
		print('{0:s}path                {1:s}'.\
			format(prefix, self.path))
		print('{0:s}isdir               {1:b}'.\
			format(prefix, self.isdir))
		if self.size != None:
			print('{0:s}size                {1:s}'.\
				format(prefix, SizeToString(self.size)))
		if self.ctime != None:
			print('{0:s}creation time       {1:s}'.\
				format(prefix, self.ctime.strftime('%Y-%m-%d %H:%M:%S')))
		if self.atime != None:
			print('{0:s}access time         {1:s}'.\
				format(prefix, self.atime.strftime('%Y-%m-%d %H:%M:%S')))
		if self.mtime != None:
			print('{0:s}modification time   {1:s}'.\
				format(prefix, self.mtime.strftime('%Y-%m-%d %H:%M:%S')))
		if self.checksum != None:
			print('{0:s}checksum            {1:s}'.\
				format(prefix, ChecksumToString(self.checksum)))

	def Export(self, filehandle):
		"""
		Write node information into file using the dot format (graphviz)
		"""
		if self.depth == 0:
			if self.isdir:
				filehandle.write('\t{0:d} [ style=bold, shape=box, label="{0:d}\\n{1:s}" ];\n'\
					.format(self.nodeid, self.name.replace('\\', '\\\\')))
			else:
				filehandle.write('\t{0:d} [ style=bold, shape=ellipse, label="{0:d}\\n{1:s}\\n{2:s}" ];\n'\
					.format(self.nodeid, self.name.replace('\\', '\\\\'), ChecksumToString(self.checksum, True)))
		else:
			if self.isdir:
				filehandle.write('\t{0:d} [ shape=box, label="{0:d}\\n{1:s}" ];\n'\
					.format(self.nodeid, self.name))
			else:
				filehandle.write('\t{0:d} [ shape=ellipse, label="{0:d}\\n{1:s}\\n{2:s}" ];\n'\
					.format(self.nodeid, self.name, ChecksumToString(self.checksum, True)))
			filehandle.write('\t{0:d} -> {1:d};\n'.format(self.parent, self.nodeid))

	def Delete(self, dbcon):
		"""
		Delete node in database
		"""
		dbcon.execute('delete from nodes where nodeid=?', (self.nodeid,))
	
	def DeleteDescendants(self, dbcon):
		"""
		Delete all descendants of node (recursively) in database
		"""
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectString + \
			' from nodes where parent=?', (self.nodeid,))
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.depth = self.depth + 1
			n.path = os.path.join(self.path, n.name)
			if n.isdir:
				n.DeleteDescendants(dbcon)
		cursor.execute('delete from nodes where parent=?', (self.nodeid,))
		cursor.close()

	def Import(self, dbcon):
		"""
		Recursive part of NodeDB.Import
		"""
		for e in os.listdir(self.path):
			n = Node()
			n.FetchFromDirectory(os.path.join(self.path, e), e)
			n.parent = self.nodeid
			n.depth = self.depth + 1
			log.Print(0, 'Importing', n.path)
			n.WriteToDatabase(dbcon)
			if n.isdir:
				n.Import(dbcon)

	def TraverseDatabase(self, dbcon, func, param):
		"""
		Recursive part of NodeDB.TraverseDatabase
		"""
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectString + \
			' from nodes where parent=?', (self.nodeid,))
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.depth = self.depth + 1
			n.path = os.path.join(self.path, n.name)
			if n.isdir:
				n.TraverseDatabase(dbcon, func, param)
			func(n, dbcon, param)
		cursor.close()

	def TraversePrint(self, dbcon, param):
		"""
		Method executed on every node by TraverseDatabase when
		NodeDB.Print is called
		"""
		self.Print(self.depth)

	def TraverseExport(self, dbcon, param):
		"""
		Method executed on every node by TraverseDatabase when
		NodeDB.Export is called
		"""
		log.Print(0, 'Exporting', self.path)
		self.Export(param)

	def TraverseCheck(self, dbcon, param):
		"""
		Method executed on every node by TraverseDatabase when
		NodeDB.Check is called
		"""
		if os.path.exists(self.path):
			dirnode = Node()
			dirnode.FetchFromDirectory(self.path, self.name)
			log.Print(0, 'Checking', dirnode.path)
			self.Compare(dirnode)
		else:
			log.Print(2, 'Path does not exist in file system', self.path)
	
	def TraverseDelete(self, dbcon, param):
		"""
		Method executed on every node by TraverseDatabase when
		NodeDB.SlowDelete is called
		"""
		self.Delete(dbcon)

	def Update(self, dbcon, docheck=True):
		"""
		Recursive part of NodeDB.Update
		"""
		# fetch child nodes and create a map: name -> node
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectString + \
			' from nodes where parent=?', (self.nodeid,))
		dbnodes = {}
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.depth = self.depth + 1
			n.path = os.path.join(self.path, n.name)
			dbnodes[n.DictKey()] = n
		# iterate over all directory entries and check them one by one
		entries = os.listdir(self.path)
		for e in entries:
			dirnode = Node()
			dirnode.FetchFromDirectory(os.path.join(self.path, e), e)
			dirnode.parent = self.nodeid
			dirnode.depth = self.depth + 1
			if dirnode.DictKey() in dbnodes:
				# node exists in database: get the database node 
				dbnode = dbnodes[dirnode.DictKey()]
				if not dirnode.isdir:
					if docheck:
						# check the entry
						log.Print(0, 'Checking', dirnode.path)
						dbnode.Compare(dirnode)
				else:
					# if directory do the recursion (use dbnode because it has the correct nodeid)
					dbnode.Update(dbcon, docheck)
				if not docheck:
					# update the entry in the database with the current dirnode information
					log.Print(0, 'Updating', dirnode.path)
					dirnode.nodeid = dbnode.nodeid
					dirnode.UpdateDatabase(dbcon)
				# remove processed entry from dictionary
				del dbnodes[dirnode.DictKey()]
			else:
				# add non-existing entry to list
				log.Print(1, 'Adding', dirnode.path)
				dirnode.WriteToDatabase(dbcon)
				# if directory do the recursion (WriteToDatabase set the nodeid)
				if dirnode.isdir:
					dirnode.Update(dbcon)
		cursor.close()
		# iterate over remaining entries in rowdict, those entries should be removed
		for n in dbnodes.values():
			log.Print(1, 'Deleting', n.path)
			n.DeleteDescendants(dbcon)
			n.Delete(dbcon)



# ====================================================================
# ============================== NodeDB ==============================
# ====================================================================

class NodeDB:

	def __init__(self, dbpath):
		"""
		Constructor of NodeDB class
		Open database: first determine checksum of database file and compare it
		with the one stored in a separate checksum file to check for corruption
		of the database. If the database file is a newly created, create tables.
		"""
		self.__dbcon = None
		self.__dbpath = dbpath
		if self.__dbpath == ':memory:':
			dbexisted = False
		else:
			self.__csumpath = self.__dbpath + '.sha256'
			dbexisted = os.path.exists(self.__dbpath)
			# get checksum from separate checksum file and check it with database checksum
			if dbexisted:
				f = open(self.__csumpath, 'r')
				csumfile = f.read()
				f.close()
				csum = ChecksumToString(GetChecksum(self.__dbpath))
				if csum != csumfile:
					log.Print(3, 'Database file has been corrupted.', dbpath)
		self.__dbcon = sqlite3.connect(self.__dbpath, \
			# necessary for proper retrival of datetime objects from the database,
			# otherwise the cursor will return string values with the timestamps
			detect_types=sqlite3.PARSE_DECLTYPES)
		# stores strings as ascii strings in the database, not as unicodes
		# makes program easily compatible with python 2.X but introduces
		# problems when file system supports unicode... :-(
		if sys.version[0] == '2':
			self.__dbcon.text_factory = str
		if not dbexisted:
			self.CreateTables()

	def __del__(self):
		"""
		Destructor of LogFacility class
		"""
		if self.__dbcon != None:
			self.Close()

	def Close(self):
		"""
		Close database: close database and then update the separate checksum file 
		"""
		self.__dbcon.close()
		self.__dbcon = None
		if self.__dbpath != ':memory:':
			# get checksum of database file and store it in an addtional file
			csum = ChecksumToString(GetChecksum(self.__dbpath))
			f = open(self.__csumpath, 'w')
			f.write(csum)
			f.close()

	def CreateTables(self):
		"""
		Initialization of empty database: create tables used by program
		"""
		self.__dbcon.execute('create table nodes (' + \
			'nodeid integer primary key,' + \
			'parent integer,' + \
			'name text not null,' + \
			'isdir boolean not null,' + \
			'size integer,' + \
			'ctime timestamp,' + \
			'atime timestamp,' + \
			'mtime timestamp,' + \
			'checksum blob' + \
			')')

	def DropTables(self):
		"""
		Remove all tables from the database connected with program
		"""
		self.__dbcon.execute('drop table nodes')

	def RecreateTables(self):
		"""
		Remove and the create all tables used by program
		"""
		self.DropTables()
		self.CreateTables()
	
	def RootPathExistsInDatabase(self, path=None):
		"""
		Method that checks the availability of either any root node
		in the database (path=None) or a certain root node specified
		by path
		"""
		cursor = self.__dbcon.cursor()
		if path == None:
			cursor.execute('select count(nodeid) from nodes where parent is null')
		else:
			cursor.execute('select count(nodeid) from nodes where parent is null and name=?', (path,))
		result = cursor.fetchone()[0] > 0
		cursor.close()
		return result

	def GetRootNodes(self, path=None):
		"""
		Method retrieves all root notes of the database (path=None) or
		a certain root node specified by path. Format is a database cursor
		which must be closed after use (!)
		"""
		cursor = self.__dbcon.cursor()
		if path == None:
			if not self.RootPathExistsInDatabase(path):
				log.Print(3, 'There are no root nodes in the database.')
			cursor.execute('select ' + NodeSelectString + \
				' from nodes where parent is null')
		else:
			if not self.RootPathExistsInDatabase(path):
				log.Print(3, 'Path  does not exist in the database.', path)
			cursor.execute('select ' + NodeSelectString + \
				' from nodes where parent is null and name=?', (path,))
		return cursor

	def Import(self, path):
		"""
		Import contents of path recursively into the database
		"""
		if self.RootPathExistsInDatabase(path):
			log.Print(3, 'Path already exist in the database.', path)
		if not os.path.exists(path):
			log.Print(3, 'Path cannot be found on disk.', path)
		n = Node()
		n.FetchFromDirectory(path, None)
		n.parent = None
		n.depth = 0
		log.Print(0, 'Importing',path)
		n.WriteToDatabase(self.__dbcon)
		if n.isdir:
			n.Import(self.__dbcon)
		self.__dbcon.commit()
		log.Print(0, 'Done.\n')

	def TraverseDatabase(self, path, func, param):
		"""
		Execute function func on every node in the database. Is used by
		Print, Export and Check and SlowDelete. It takes the contents of
		the database as reference and does not access the contents of the
		file system, even though this can be implemented in the function
		like Check determining checksums of files.
		For the function inferface of func check the examples mentioned.
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		cursor = self.GetRootNodes(path)
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.path = n.name
			n.depth = 0
			func(n, self.__dbcon, param)
			if n.isdir:
				n.TraverseDatabase(self.__dbcon, func, param)
		cursor.close()

	def Print(self, path=None):
		"""
		Print tree structure in database to the console.
		Makes only sense for small directory trees and for debugging.
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		self.TraverseDatabase(path, Node.TraversePrint, None)
		print('')

	def Status(self):
		"""
		Print status of database contents: list of root nodes and some statistics
		"""
		cursor = self.__dbcon.cursor()
		# root nodes
		cursor.execute('select count(nodeid) from nodes where parent is null')
		numrootnodes = cursor.fetchone()[0]
		if numrootnodes > 0:
			print('{0:d} root nodes in database:'.format(numrootnodes))
			cursor.execute('select ' + NodeSelectString + \
				' from nodes where parent is null')
			for row in cursor:
				n = Node()
				n.FetchFromDatabaseRow(row)
				n.path = n.name
				if os.path.exists(n.path):
					print('  ' + n.path)
				else:
					print('  ' + n.path + ' (not found in file system)')
		else:
			print('No root nodes in database.')
		if numrootnodes > 0:
			# total number of nodes
			cursor.execute('select count(nodeid),sum(size) from nodes')
			row = cursor.fetchone()
			numnodes = row[0]
			totalsize = row[1]
			cursor.execute('select count(nodeid) from nodes where isdir=1')
			numdirs = cursor.fetchone()[0]
			cursor.execute('select count(nodeid) from nodes where isdir=0')
			numfiles = cursor.fetchone()[0]
			print('')
			print('{0:d} nodes, {1:d} dirs, {2:d} files, {3:s} size stored in database'.\
				format(numnodes, numdirs, numfiles, SizeToString(totalsize)))
		# cleanup
		cursor.close()
		print('')

	def Relocate(self, oldpath, newpath):
		"""
		Change root node path of one entry in the database, useful if directory tree has been moved
		"""
		# check if old root node exists and new one does not exist in the database
		if not self.RootPathExistsInDatabase(oldpath):
			log.Print(3, 'Path does not exist in the database.', oldpath)
		if self.RootPathExistsInDatabase(newpath):
			log.Print(3, 'Path already exist in the database.', newpath)
		# do the renaming
		self.__dbcon.execute('update nodes set name=? where parent is null and name=?', (newpath, oldpath))
		self.__dbcon.commit()

	def Export(self, filename, path=None):
		"""
		Export tree structure in database to a svg showing a graphical representation of the
		node tree in the database. Makes only sense for small directory trees and for debugging.
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		# write temporary graphviz dot file
		f = open(filename + '.dot', 'w')
		f.write('digraph "' + ProgramName + ' schema"\n{\n')
		self.TraverseDatabase(path, Node.TraverseExport, f)
		f.write('}\n')
		f.close()
		# process file with graphviz dot
		cmdline = 'dot -Tsvg -o' + filename + '.svg ' + filename + '.dot'
		args = shlex.split(cmdline)
		fnull = open(os.devnull, 'w')
		proc = subprocess.Popen(args, stdin=fnull, stdout=fnull, stderr=fnull)
		fnull.close()
		proc.communicate()
		# clean up and exit
		os.remove(filename + '.dot')
		log.Print(0, 'Done.\n')

	def Check(self, path=None):
		"""
		For each entry in the database check the checksum
		(Does not update the database, e.g. if directory structure contains
		new entries or if database contains no longer existing ones, check
		Update if you want that functionality)
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		self.TraverseDatabase(path, Node.TraverseCheck, None)
		log.Print(0, 'Done.\n')

	def SlowDelete(self, path=None):
		"""
		Delete a path and all its contents recursively from the database.
		REMARK: This is just implemented because of academic interest
		because it uses TraverseDatabase and modifies the database. Better
		use Delete because of speed
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		self.TraverseDatabase(path, Node.TraverseDelete, None)
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')
		log.Print(0, 'Done.\n')
	
	def Delete(self, path=None):
		"""
		Delete a path and all its contents recursively from the database.
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		if path == None:
			log.Print(0, 'Deleting all nodes')
			self.__dbcon.execute('delete from nodes')
		else:
			cursor = self.GetRootNodes(path)
			n = Node()
			n.FetchFromDatabaseRow(cursor.fetchone())
			n.path = n.name
			n.depth = 0
			n.DeleteDescendants(self.__dbcon)
			n.Delete(self.__dbcon)
			cursor.close()
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')
		log.Print(0, 'Done.\n')

	def Update(self, path=None, docheck=True):
		"""
		Update contents of database by adding new directory entries,
		deleting non-existing ones. If docheck is true (default), all
		entries existing in the database and the file system are checked,
		if the flag is false, the entries are updated in the database
		according to the new file status.
		If path is specified, it must be the root of a directory tree under
		control of program and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		cursor = self.GetRootNodes(path)
		for row in cursor:
			dbnode = Node()
			dbnode.FetchFromDatabaseRow(row)
			dbnode.path = dbnode.name
			dbnode.depth = 0
			dirnode = Node()
			dirnode.FetchFromDirectory(dbnode.path, dbnode.name)
			if not dbnode.isdir:
				if docheck:
					# check the entry
					log.Print(0, 'Checking', dirnode.path)
					dbnode.Compare(dirnode)
			else:
				dbnode.Update(self.__dbcon, docheck)
			if not docheck:
				# update the entry in the database with the current dirnode information
				log.Print(0, 'Updating', dirnode.path)
				dirnode.nodeid = dbnode.nodeid
				dirnode.UpdateDatabase(self.__dbcon)
		cursor.close()
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')
		log.Print(0, 'Done.\n')



# ==================================================================
# ============================== Main ==============================
# ==================================================================

class MyArgParser(argparse.ArgumentParser):
	ActionList = []
	DatabaseInMemory = False



class MainAction(argparse.Action):
	def __call__(self, parser, namespace, values, option_string=None):
		"""
		Parser action method:
		Put commands into command list, check for "memory" flag
		"""
		if self.dest == 'memory':
			parser.DatabaseInMemory = True
		else:
			parser.ActionList.append([self.dest, values])



def Main():
	"""
	Main entry point of program
	"""
	# configure parser
	parser = MyArgParser(prog=ProgramName, \
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''
		%(prog)s - Directory tree integrity checking

		Program to secure the contents of one or more directory structures by
		calculating checksums for all files and storing them in a separate database.
		This database can be used to later on to verify the integrity of the data.
		'''), \
		epilog=textwrap.dedent('''
		The command line parameters for status, import, delete, print, export,
		check and update can be combined to realize a certain squence of orders.
		For example the command '(prog)s -d -i foo' will first delete all nodes
		in the database and then import the file or directory 'foo'. The command
		'(prog)s -i foo -c -p -e -s' will import the file or directory 'foo',
		then run a check, then print and export the current database contents and
		finally print a status on the console.

		Files used by %(prog)s:
		%(prog)s.py              Program file
		%(prog)s.log             Log file
		%(prog)s.sqlite          Database file
		%(prog)s.sqlite.sha256   Checksum file of database to secure the database
		schema.svg            Tree graph of database contents as saved by export
		'''))
	parser.add_argument('-v', '--version', action='version', version='%(prog)s version 2.0')
	parser.add_argument('-m', '--memory', dest='memory', nargs=0, action=MainAction, \
		help='Use database located in memory. This database is empty at the beginning so use' + \
		' import first. All data is gone after the program has finished. For testing purposes.')
	parser.add_argument('-s', '--status', dest='status', nargs=0, action=MainAction, \
		help='Print status of database to console')
	parser.add_argument('-r', '--relocate', dest='relocate', nargs=2, metavar=('OLD_PATH', 'NEW_PATH'), action=MainAction, \
		help='Indicate to the database that a path to a directory tree has been changed ' + \
		'by specifying the old and the new path. Useful if directory tree has been moved.')
	parser.add_argument('-i', '--import', dest='import', nargs=1, metavar='PATH', action=MainAction, \
		help='Import file or directory tree specified by PATH into database')
	parser.add_argument('-d', '--delete', dest='delete', nargs='?', metavar='PATH', action=MainAction, \
		help='Delete PATH or (if none specified) all paths from database')
	parser.add_argument('-p', '--print', dest='print', nargs='?', metavar='PATH', action=MainAction, \
		help='Print PATH or (if none specified) all paths from database to console')
	parser.add_argument('-e', '--export', dest='export', nargs='?', metavar='PATH', action=MainAction, \
		help='Export PATH or (if none specified) all paths from database into a SVG ' + \
		'representation of the tree. Output file is \'schema.svg\'. ' + \
		'Mainly used for debugging purposes.')
	parser.add_argument('-c', '--check', dest='check', nargs='?', metavar='PATH', action=MainAction, \
		help='Check PATH or (if none specified) all paths from database by ' + \
		'traversing nodes in database and checking checksums of existing files. ' + \
		'No update of database when directory structure has changed, database is ' + \
		'not changed by this command.')
	parser.add_argument('-u', '--update', dest='update', nargs='?', metavar='PATH', action=MainAction, \
		help='Update PATH or (if none specified) all paths from database by ' + \
		'traversing the directory structure and checking files existing in the ' + \
		'database, adding new ones to the database and removing no longer existing ' + \
		'ones from the database.')
	# parse arguments
	parser.parse_args()
	# if no actions specified, just show help
	if len(parser.ActionList) == 0:
		parser.print_help()
		return
	# open database dependent on arguments
	if parser.DatabaseInMemory:
		db = NodeDB(':memory:')
	else:
		db = NodeDB(ProgramName + '.sqlite')
	# execute actions specified by arguments
	for action in parser.ActionList:
		if action[0] == 'status':
			db.Status()
		elif action[0] == 'relocate':
			db.Relocate(action[1][0], action[1][1])
		elif action[0] == 'import':
			db.Import(action[1][0])
		elif action[0] == 'delete':
			db.Delete(action[1])
		elif action[0] == 'print':
			db.Print(action[1])
		elif action[0] == 'export':
			db.Export(action[1], 'schema')
		elif action[0] == 'check':
			db.Check(action[1])
		elif action[0] == 'update':
			db.Update(action[1])
		else:
			log.Print(3, 'Command line parser returned with unknown command \'' + self.dest + '\'.')
	# close database
	db.Close()



Main()
