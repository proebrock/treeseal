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
Central facility for logging purposes used by all functions.
"""
log = LogFacility('dtcon2.log')



NodeSelectColumnString = 'rowid, parent, name, isdir, size, checksum'

class Node:

	def __init__(self):
		self.rowid = None
		self.parent = None
		self.depth = None
		self.name = None
		self.path = None
		self.isdir = None
		self.size = None
		self.checksum = None

	def FetchFromDatabaseRow(self, row):
		self.rowid = row[0]
		self.parent = row[1]
		# self.depth has to be set while traversing
		self.name = row[2]
		# self.path has to be set while traversing
		self.isdir = row[3]
		self.size = row[4]
		self.checksum = row[5]
	
	def FetchFromDirectory(self, path, name):
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
		cursor = dbcon.cursor()
		cursor.execute('insert into nodes (parent, name, isdir, size, checksum) values (?,?,?,?,?)', \
			(self.parent, self.name, self.isdir, self.size, self.checksum))
		self.rowid = cursor.lastrowid
		cursor.close()
	
	def Print(self, numindent):
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

	def Import(self, dbcon, path):
		for e in os.listdir(self.path):
			n = Node()
			n.FetchFromDirectory(os.path.join(path, e), e)
			log.Print(0, 'importing ' + n.path + ' ...')
			n.parent = self.rowid
			n.WriteToDatabase(dbcon)
			if n.isdir:
				n.Import(dbcon, n.path)

	def TraverseDatabase(self, dbcon, path, depth, func, param):
		cursor = dbcon.cursor()
		cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent=?', (self.rowid,))
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.depth = depth
			n.path = os.path.join(path, n.name)
			func(n, dbcon, param)
			if n.isdir:
				n.TraverseDatabase(dbcon, n.path, depth + 1, func, param)
		cursor.close()

	def TraversePrint(self, dbcon, param):
		self.Print(self.depth)

	def TraverseExport(self, dbcon, param):
		log.Print(0, 'exporting ' + self.path + ' ...')
		if self.depth == 0:
			if self.isdir:
				param.write('\t{0:d} [ style=bold, shape=box, label="{0:d}\\n{1:s}" ];\n'\
					.format(self.rowid, self.name.replace('\\', '\\\\')))
			else:
				param.write('\t{0:d} [ style=bold, shape=ellipse, label="{0:d}\\n{1:s}\\n{2:s}" ];\n'\
					.format(self.rowid, self.name.replace('\\', '\\\\'), ChecksumToString(self.checksum, True)))
		else:
			if self.isdir:
				param.write('\t{0:d} [ shape=box, label="{0:d}\\n{1:s}" ];\n'\
					.format(self.rowid, self.name))
			else:
				param.write('\t{0:d} [ shape=ellipse, label="{0:d}\\n{1:s}\\n{2:s}" ];\n'\
					.format(self.rowid, self.name, ChecksumToString(self.checksum, True)))
			param.write('\t{0:d} -> {1:d};\n'.format(self.parent, self.rowid))
	
	def TraverseCheck(self, dbcon, param):
		if not self.isdir:
			log.Print(0, 'checking ' + self.path + ' ...')
			if self.checksum == None:
				log.Print(2, 'No checksum defined for ' + path)
			elif self.checksum != GetChecksum(self.path):
				log.Print(2, 'Checksum error for ' + path)


class NodeDB:

	def __init__(self, dbpath):
		"""
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

	def Close(self):
		"""
		Close database: close database and then update the separate checksum file 
		"""
		self.__dbcon.close()
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

	def Import(self, path):
		# TODO: check if path exists
		# TODO: use TraverseDirectory to be reused in Update
		n = Node()
		n.FetchFromDirectory(path, None)
		log.Print(0, 'importing ' + path + ' ...')
		n.WriteToDatabase(self.__dbcon)
		if n.isdir:
			n.Import(self.__dbcon, path)
		self.__dbcon.commit()
		log.Print(0, 'done\n')

	def TraverseDatabase(self, path, func, param):
		cursor = self.__dbcon.cursor()
		if path == None:
			cursor.execute('select count(rowid) from nodes where parent is null')
			if cursor.fetchone()[0] == 0:
				log.Print(3, 'There are no nodes in the database.')
			cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent is null')
		else:
			cursor.execute('select count(rowid) from nodes where parent is null and name=?', (path,))
			if cursor.fetchone()[0] == 0:
				log.Print(3, 'Path ' + path + ' does not exist in the database.')
			cursor.execute('select ' + NodeSelectColumnString + ' from nodes where parent is null and name=?', (path,))
		for row in cursor:
			n = Node()
			n.FetchFromDatabaseRow(row)
			n.path = n.name
			n.depth = 0
			func(n, self.__dbcon, param)
			if n.isdir:
				n.TraverseDatabase(self.__dbcon, n.name, 1, func, param)
		cursor.close()

	def Print(self, path):
		self.TraverseDatabase(path, Node.TraversePrint, None)
		log.Print(0, '')

	def Export(self, path, filename):
		f = open(filename + '.dot', 'w')
		f.write('digraph G\n{\n')
		self.TraverseDatabase(path, Node.TraverseExport, f)
		f.write('}\n')
		f.close()
		ExecuteShell('dot -Tsvg -o' + filename + '.svg ' + filename + '.dot')
		os.remove(filename + '.dot')
		log.Print(0, 'done\n')

	def Check(self, path):
		self.TraverseDatabase(path, Node.TraverseCheck, None)
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

	#ndb.Print(None)
	ndb.Print('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a')

	ndb.Export(None, 'schema')
	#ndb.Export('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a', 'schema')

	#ndb.Check(None)
	#ndb.Check('C:\\Users\\roebrocp\\Desktop\\dtcon2\\a')

	ndb.Close()

Main()
