import sqlite3
import sys
import os
import hashlib
import shlex
import subprocess
import time



class LogFacility:

	def __init__(self, path):
		"""
		Constructor of LogFacility class
		"""
		self.__starttime = time.clock()
		self.Reset()
		if path != None:
			self.__f = open(path, 'w')
		else:
			self.__f = None

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
				print(f)
		if len(self.__errors) > 0:
			print('\n{0:d} errors:'.format(len(self.__errors)))
			for e in self.__errors:
				print(e)
		if len(self.__warnings) > 0:
			print('\n{0:d} warnings:'.format(len(self.__warnings)))
			for w in self.__warnings:
				print(w)
		if (len(self.__warnings) == 0) and (len(self.__errors) == 0) and (len(self.__fatalerrors) == 0):
			print('\nno warnings, errors or fatal errors')
		else:
			input("\nPress any key ...") 

	def Reset(self):
		"""
		Reset buffers
		"""
		self.__warnings = []
		self.__errors = []
		self.__fatalerrors = []

	def Print(self, lvl, message):
		"""
		Print message of certain importance level. Printing is handled by the log facility.
		Importance levels are: 0 - Notice, 1 - Warning, 2 - Error, 3 - Fatal Error
		"""
		# determine message prefix and update counters
		if lvl == 0:
			prefix = ''
		elif lvl == 1:
			prefix = 'Warning: '
			self.__warnings.append(message)
		elif lvl == 2:
			prefix = 'Error: '
			self.__errors.append(message)
		elif lvl == 3:
			prefix = '### Fatal Error: '
			self.__fatalerrors.append(message)
		else:
			raise Exception('Unknown log level {0:d}'.format(lvl))
		# write message to different targets
		print(prefix + message)
		if self.__f != None:
			self.__f.write(prefix + message + '\n')
		# if fatal, exit program
		if lvl == 3:
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
		if elapsed < 60:
			return '{0:.1f}s'.format(elapsed)
		elif elapsed < 60 * 60:
			return '{0:.1f}min'.format(elapsed/60)
		else:
			return '{0:.1f}h'.format(elapsed/60/60)

"""
Central facility for logging purposes used by all methods.
"""
log = LogFacility('dtcon2.log')



NodeSelectColumnString = 'rowid, parent, name, isdir, size, checksum'

class Node:

	def __init__(self):
		"""
		Constructor of Node class
		"""
		self.rowid = None
		self.parent = None
		self.depth = None
		self.name = None
		self.path = None
		self.isdir = None
		self.size = None
		self.checksum = None

	def FetchFromDatabaseRow(self, row):
		"""
		When database was read using a cursor, this method is used to extract
		information from a cursor row into a node.
		Some information cannot be retrieved from the database row, check
		comments below.
		"""
		self.rowid = row[0]
		self.parent = row[1]
		# self.depth has to be set while traversing
		self.name = row[2]
		# self.path has to be set while traversing
		self.isdir = row[3]
		self.size = row[4]
		self.checksum = row[5]
	
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
		# self.rowid is set after writing to database
		# self.parent has to be set while traversing
		# self.depth has to be set while traversing
		if name == None:
			self.name = path
		else:
			self.name = name
		self.path = path
		self.isdir = os.path.isdir(self.path)
		if not self.isdir:
			self.size = os.path.getsize(self.path)
			self.checksum = GetChecksum(self.path)

	def WriteToDatabase(self, dbcon):
		"""
		Write (not in database existing) node to database
		and set rowid due to the one received from the database
		"""
		cursor = dbcon.cursor()
		cursor.execute('insert into nodes (parent, name, isdir, size, checksum) values (?,?,?,?,?)', \
			(self.parent, self.name, self.isdir, self.size, self.checksum))
		self.rowid = cursor.lastrowid
		cursor.close()
	
	def Check(self):
		"""
		Check node by calculating checksum of filename specified by path
		and comparing it with stored checksum with
		"""
		if not self.isdir:
			log.Print(0, 'checking ' + self.path + ' ...')
			if self.checksum == None:
				log.Print(2, 'No checksum defined for ' + path)
			elif self.checksum != GetChecksum(self.path):
				log.Print(2, 'Checksum error for ' + path)
	
	def Print(self, numindent):
		"""
		Print details about current node into the log facility
		"""
		prefix = '  ' * numindent
		log.Print(0, '{0:s}node'.format(prefix, self.rowid))
		prefix += '->'
		log.Print(0, '{0:s}rowid      {1:d}'.format(prefix, self.rowid))
		if self.parent != None:
			log.Print(0, '{0:s}parent     {1:d}'.format(prefix, self.parent))
		else:
			log.Print(0, '{0:s}parent     <none>'.format(prefix))
		log.Print(0, '{0:s}depth      {1:d}'.format(prefix, self.depth))
		log.Print(0, '{0:s}name       {1:s}'.format(prefix, self.name))
		log.Print(0, '{0:s}path       {1:s}'.format(prefix, self.path))
		log.Print(0, '{0:s}isdir      {1:b}'.format(prefix, self.isdir))
		if self.size != None:
			log.Print(0, '{0:s}size       {1:d}'.format(prefix, self.size))
		if self.checksum != None:
			log.Print(0, '{0:s}checksum   {1:s}'.format(prefix, ChecksumToString(self.checksum, False)))

	def Export(self, filehandle):
		"""
		Write node information into file using the dot format (graphviz)
		"""
		if self.depth == 0:
			if self.isdir:
				filehandle.write('\t{0:d} [ style=bold, shape=box, label="{0:d}\\n{1:s}" ];\n'\
					.format(self.rowid, self.name.replace('\\', '\\\\')))
			else:
				filehandle.write('\t{0:d} [ style=bold, shape=ellipse, label="{0:d}\\n{1:s}\\n{2:s}" ];\n'\
					.format(self.rowid, self.name.replace('\\', '\\\\'), ChecksumToString(self.checksum, True)))
		else:
			if self.isdir:
				filehandle.write('\t{0:d} [ shape=box, label="{0:d}\\n{1:s}" ];\n'\
					.format(self.rowid, self.name))
			else:
				filehandle.write('\t{0:d} [ shape=ellipse, label="{0:d}\\n{1:s}\\n{2:s}" ];\n'\
					.format(self.rowid, self.name, ChecksumToString(self.checksum, True)))
			filehandle.write('\t{0:d} -> {1:d};\n'.format(self.parent, self.rowid))

	def Delete(self, dbcon):
		"""
		Delete node in database
		"""
		dbcon.execute('delete from nodes where rowid=?', (self.rowid,))
	
	def DeleteDescendants(self, dbcon):
		"""
		Delete all descendants of node (recursively) in database
		"""
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent=?', (self.rowid,))
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			if n.isdir:
				n.DeleteDescendants(dbcon)
		cursor.execute('delete from nodes where parent=?', (self.rowid,))
		cursor.close()

	def Import(self, dbcon):
		"""
		Recursive part of NodeDB.Import
		"""
		for e in os.listdir(self.path):
			n = Node()
			n.FetchFromDirectory(os.path.join(self.path, e), e)
			n.parent = self.rowid
			n.depth = self.depth + 1
			log.Print(0, 'importing into database ' + n.path + ' ...')
			n.WriteToDatabase(dbcon)
			if n.isdir:
				n.Import(dbcon)

	def TraverseDatabase(self, dbcon, func, param):
		"""
		Recursive part of NodeDB.TraverseDatabase
		"""
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent=?', (self.rowid,))
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
		log.Print(0, 'exporting ' + self.path + ' ...')
		self.Export(param)

	def TraverseCheck(self, dbcon, param):
		"""
		Method executed on every node by TraverseDatabase when
		NodeDB.Check is called
		"""
		self.Check()
	
	def TraverseDelete(self, dbcon, param):
		"""
		Method executed on every node by TraverseDatabase when
		NodeDB.SlowDelete is called
		"""
		self.Delete(dbcon)

	def Update(self, dbcon):
		"""
		Recursive part of NodeDB.Update
		"""
		# fetch child nodes and create a map: name -> node
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent=?', (self.rowid,))
		dbnodes = {}
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.depth = self.depth + 1
			n.path = os.path.join(self.path, n.name)
			dbnodes[n.name] = n
		# iterate over all directory entries and check them one by one
		entries = os.listdir(self.path)
		for e in entries:
			dirnode = Node()
			dirnode.FetchFromDirectory(os.path.join(self.path, e), e)
			dirnode.parent = self.rowid
			dirnode.depth = self.depth + 1
			if dirnode.name in dbnodes:
				# check file
				dirnode.Check()
				# if directory do the recursion (use dbnode because it has the correct rowid)
				if dirnode.isdir:
					dbnodes[dirnode.name].Update(dbcon)
				# remove checked entry from dictionary: this node is processed
				del dbnodes[dirnode.name]
			else:
				# add non-existing entry to list
				log.Print(1, 'adding to database ' + dirnode.path + ' ...')
				dirnode.WriteToDatabase(dbcon)
				# if directory do the recursion (WriteToDatabase set the rowid)
				if dirnode.isdir:
					dirnode.Update(dbcon)
		cursor.close()
		# iterate over remaining entries in rowdict, those entries should be removed
		for n in dbnodes.values():
			log.Print(1, 'deleting ' + n.path)
			n.DeleteDescendants(dbcon)
			n.Delete(dbcon)

class NodeDB:

	def __init__(self, dbpath):
		"""
		Constructor of NodeDB class
		Open database: first determine checksum of database file and compare it
		with the one stored in a separate checksum file to check for corruption
		of the database. If the database file is a newly created, create tables.
		"""
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
				csum = ''.join('%02x' % byte for byte in GetChecksum(self.__dbpath))
				if csum != csumfile:
					log.Print(3, 'Database file has been corrupted')
		self.__dbcon = sqlite3.connect(self.__dbpath)
		if not dbexisted:
			self.CreateTables()

	def __del__(self):
		"""
		Destructor of LogFacility class
		"""
		if self.__dbpath != None:
			self.Close()

	def Close(self):
		"""
		Close database: close database and then update the separate checksum file 
		"""
		self.__dbcon.close()
		self.__dbcon = None
		if self.__dbpath != ':memory:':
			# get checksum of database file and store it in an addtional file
			csum = ''.join('%02x' % byte for byte in GetChecksum(self.__dbpath))
			f = open(self.__csumpath, 'w')
			f.write(csum)
			f.close()

	def CreateTables(self):
		"""
		Initialization of empty database: create tables used by dtcon2
		"""
		self.__dbcon.execute('create table nodes (' + \
			'parent int,' + \
			'name text not null,' + \
			'isdir boolean not null,' + \
			'size int,' + \
			'checksum blob' + \
			')')

	def DropTables(self):
		"""
		Remove all tables from the database connected with dtcon2
		"""
		self.__dbcon.execute('drop table nodes')

	def RecreateTables(self):
		"""
		Remove and the create all tables used by dtcon2
		"""
		self.DropTables()
		self.CreateTables()
	
	def RootPathExistsInDatabase(self, path):
		"""
		Method that checks the availability of either any root node
		in the database (path=None) or a certain root node specified
		by path
		"""
		cursor = self.__dbcon.cursor()
		if path == None:
			cursor.execute('select count(rowid) from nodes where parent is null')
		else:
			cursor.execute('select count(rowid) from nodes where parent is null and name=?', (path,))
		result = cursor.fetchone()[0] > 0
		cursor.close()
		return result

	def GetRootNodes(self, path):
		"""
		Method retrieves all root notes of the database (path=None) or
		a certain root node specified by path. Format is a database cursor
		which must be closed after use (!)
		"""
		cursor = self.__dbcon.cursor()
		if path == None:
			if not self.RootPathExistsInDatabase(path):
				log.Print(3, 'There are no nodes in the database.')
			cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent is null')
		else:
			if not self.RootPathExistsInDatabase(path):
				log.Print(3, 'Path ' + path + ' does not exist in the database.')
			cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent is null and name=?', (path,))
		return cursor

	def Import(self, path):
		"""
		Import contents of path recursively into the database
		"""
		if self.RootPathExistsInDatabase(path):
			log.Print(3, 'Path ' + path + ' already exist in the database.')
		if not os.path.exists(path):
			log.Print(3, 'Path ' + path + ' cannot be found on disk.')
		n = Node()
		n.FetchFromDirectory(path, None)
		n.parent = None
		n.depth = 0
		log.Print(0, 'importing into database ' + n.path + ' ...')
		n.WriteToDatabase(self.__dbcon)
		if n.isdir:
			n.Import(self.__dbcon)
		self.__dbcon.commit()
		log.Print(0, 'done\n')

	def TraverseDatabase(self, path, func, param):
		"""
		Execute function func on every node in the database. Is used by
		Print, Export and Check and SlowDelete. It takes the contents of
		the database as reference and does not access the contents of the
		file system, even though this can be implemented in the function
		like Check determining checksums of files.
		For the function inferface of func check the examples mentioned.
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
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

	def Print(self, path):
		"""
		Print tree structure in database to the console.
		Makes only sense for small directory trees and for debugging.
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		self.TraverseDatabase(path, Node.TraversePrint, None)
		log.Print(0, '')

	def Export(self, path, filename):
		"""
		Export tree structure in database to a svg showing a graphical representation of the
		node tree in the database. Makes only sense for small directory trees and for debugging.
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		f = open(filename + '.dot', 'w')
		f.write('digraph G\n{\n')
		self.TraverseDatabase(path, Node.TraverseExport, f)
		f.write('}\n')
		f.close()
		ExecuteShell('dot -Tsvg -o' + filename + '.svg ' + filename + '.dot')
		os.remove(filename + '.dot')
		log.Print(0, 'done\n')

	def Check(self, path):
		"""
		For each entry in the database check the checksum
		(Does not update the database, e.g. if directory structure contains
		new entries or if database contains no longer existing ones, check
		Update if you want that functionality)
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		self.TraverseDatabase(path, Node.TraverseCheck, None)
		log.Print(0, 'done\n')

	def SlowDelete(self, path):
		"""
		Delete a path and all its contents recursively from the database.
		REMARK: This is just implemented because of academic interest
		because it uses TraverseDatabase and modifies the database. Better
		use Delete because of speed
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		self.TraverseDatabase(path, Node.TraverseDelete, None)
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')
		log.Print(0, 'done\n')
	
	def Delete(self, path):
		"""
		Delete a path and all its contents recursively from the database.
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		if path == None:
			log.Print(0, 'deleting all nodes ...\n')
			self.__dbcon.execute('delete from nodes')
		else:
			cursor = self.GetRootNodes(path)
			n = Node()
			n.FetchFromDatabaseRow(cursor.fetchone())
			n.DeleteDescendants(self.__dbcon)
			n.Delete(self.__dbcon)
			cursor.close()
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')
		log.Print(0, 'done\n')

	def Update(self, path):
		"""
		Update contents of database by adding new directory entries,
		deleting non-existing ones and by checking all the other ones.
		If path is specified, it must be the root of a directory tree under
		control of dtcon2 and already existing in the database, if the root
		is not specified, all existing trees in the database are processed.
		"""
		cursor = self.GetRootNodes(path)
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.path = n.name
			n.depth = 0
			n.Check()
			if n.isdir:
				n.Update(self.__dbcon)
		cursor.close()
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')
		log.Print(0, 'done\n')



def ExecuteShell(cmdline):
	"""
	Execute specified command line in a shell. Do not get console output.
	"""
	args = shlex.split(cmdline)
	fnull = open(os.devnull, 'w')
	proc = subprocess.Popen(args, stdin=fnull, stdout=fnull, stderr=fnull)
	fnull.close()
	proc.communicate()

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

def ChecksumToString(checksum, shorten):
	"""
	Calculate checksum of a file by reading the directory contents.
	Checksum can be shortened in order to have a more compact display.
	"""
	if checksum == None:
		return '<none>'
	else:
		if shorten:
			return ''.join('%02x' % byte for byte in checksum[0:7]) + '...'
		else:
			return ''.join('%02x' % byte for byte in checksum)



def Main():
	"""
	Main entry point of program
	"""
	#TODO: proper command line interface
	#ndb = NodeDB(':memory:')
	ndb = NodeDB('dtcon2.sqlite')
	ndb.RecreateTables()

	ndb.Import('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a')

	ndb.Print(None)
	ndb.Print('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a')

	ndb.Export(None, 'schema')
	ndb.Export('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a', 'schema')

	ndb.Check(None)
	ndb.Check('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a')

	ndb.Update(None)
	ndb.Update('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a')

Main()
