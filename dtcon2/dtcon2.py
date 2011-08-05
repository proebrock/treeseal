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
		self.starttime = time.clock()
		self.Reset()
		if path != None:
			self.f = open(path, 'w')
		else:
			self.f = None
	def __del__(self):
		"""
		Destructor of LogFacility class
		"""
		if self.f != None:
			self.f.close()
		print('elapsed time ' + self.ElapsedTimeStr())
		if len(self.FatalErrors) > 0:
			print('\n{0:d} fatal errors:'.format(len(self.FatalErrors)))
			for f in self.FatalErrors:
				print(f)
		if len(self.Errors) > 0:
			print('\n{0:d} errors:'.format(len(self.Errors)))
			for e in self.Errors:
				print(e)
		if len(self.Warnings) > 0:
			print('\n{0:d} warnings:'.format(len(self.Warnings)))
			for w in self.Warnings:
				print(w)
		if (len(self.Warnings) == 0) and (len(self.Errors) == 0) and (len(self.FatalErrors) == 0):
			print('\nno warnings, errors or fatal errors')
		else:
			input("\nPress any key ...") 
	def Reset(self):
		"""
		Reset buffers
		"""
		self.Warnings = []
		self.Errors = []
		self.FatalErrors = []
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
			self.Warnings.append(message)
		elif lvl == 2:
			prefix = 'Error: '
			self.Errors.append(message)
		elif lvl == 3:
			prefix = '### Fatal Error: '
			self.FatalErrors.append(message)
		else:
			raise Exception('Unknown log level {0:d}'.format(lvl))
		# write message to different targets
		print(prefix + message)
		if self.f != None:
			self.f.write(prefix + message + '\n')
		# if fatal, exit program
		if lvl == 3:
			sys.exit()
	def ElapsedTime(self):
		"""
		Determine elapsed time since start of the program.
		(Or more exactly: since instantiation of an object of this class)
		"""
		return time.clock() - self.starttime
	def ElapsedTimeStr(self):
		"""
		Determine elapsed time since start of the program as a string.
		"""
		elapsed = self.ElapsedTime()
		if elapsed < 60:
			return '{0:.1f}s'.format(elapsed)
		elif elapsed < 60*60:
			return '{0:.1f}min'.format(elapsed/60)
		else:
			return '{0:.1f}h'.format(elapsed/60/60)

"""
Central facility for logging purposes used by all functions.
"""
log = LogFacility('dtcon2.log')

def ExecuteShell(cmdline):
	"""
	Execute specified command line in a shell. Do not get console output.
	"""
	args = shlex.split(cmdline)
	fnull = open(os.devnull, 'w')
	proc = subprocess.Popen(args, stdin=fnull, stdout=fnull, stderr=fnull)
	fnull.close()
	proc.communicate()

def OpenDatabase(path):
	"""
	Open database: first determine checksum of database file and compare it
	with the one stored in a separate checksum file to check for corruption
	of the database. If the database file is a newly created, create tables.
	"""
	dbexisted = os.path.exists(path)
	# get checksum from separate checksum file and check it with database checksum
	if dbexisted:
		csumfilename = path + '.sha256'
		f = open(csumfilename, 'r')
		csumfile = f.read()
		f.close()
		csum = ''.join('%02x' % byte for byte in GetFileChecksum(path))
		if csum != csumfile:
			log.Print(3, 'Database file has been corrupted')
	dbcon = sqlite3.connect(path)
	if not dbexisted:
		CreateTables(dbcon)
	return dbcon

def CloseDatabase(path, dbcon):
	"""
	Close database: close database and then update the separate checksum file 
	"""
	dbcon.close()
	# get checksum of database file and store it in an addtional file
	csum = ''.join('%02x' % byte for byte in GetFileChecksum(path))
	csumfilename = path + '.sha256'
	f = open(csumfilename, 'w')
	f.write(csum)
	f.close()

def CreateTables(dbcon):
	"""
	Initialization of empty database: create tables used by dtcon2
	"""
	dbcon.execute('create table nodes (' + \
		'parent int,' + \
		'path text not null,' + \
		'isdir boolean not null,' + \
		'checksum blob' + \
		')')

def DropTables(dbcon):
	"""
	Remove all tables from the database connected with dtcon2
	"""
	dbcon.execute('drop table nodes')

def RecreateTables(dbcon):
	"""
	Remove and the create all tables used by dtcon2
	"""
	DropTables(dbcon)
	CreateTables(dbcon)

def GetFileChecksum(path):
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

def GetDirChecksum(path):
	"""
	Calculate checksum of a file by reading the directory contents
	"""
	return b'\x00'
	#checksum = hashlib.sha256()
	#entries = os.listdir(path)
	#for e in entries:
	#	if os.path.isdir(e):
	#		checksum.update(b'\x01')
	#	else:
	#		checksum.update(b'\x00')
	#	checksum.update(e.encode('utf-8'))
	#return checksum.digest()

def GetChecksum(path, isdir):
	"""
	Get checksum of object which can be a file or directory
	"""
	if isdir:
		return GetDirChecksum(path)
	else:
		return GetFileChecksum(path)

def CheckChecksum(path, isdir, checksum):
	"""
	Determine checksum of object which can be a file or directory and check it with given one
	"""
	log.Print(0, 'checking ' + path + ' ...')
	if checksum == None:
		log.Print(1, 'No checksum defined for ' + path)
	elif checksum != GetChecksum(path, isdir):
		log.Print(2, 'Checksum error for ' + path)

def ChecksumToString(checksum, shorten):
	"""
	Calculate checksum of a file by reading the directory contents.
	Checksum can be shortened in order to have a more compact display.
	"""
	if checksum == None:
		return 'no checksum'
	else:
		if shorten:
			return ''.join('%02x' % byte for byte in checksum[0:7]) + '...'
		else:
			return ''.join('%02x' % byte for byte in checksum) + '...'

def Import(dbcon, path):
	"""
	Import contents of path recursively into the database
	"""
	cur = dbcon.cursor()
	# check if path is already in the database
	cur.execute('select rowid from nodes where parent is null and path=?', (path,))
	if not cur.fetchone() == None:
		log.Print(3, 'Path ' + path + ' already exists.')
	# add entry
	log.Print(0, 'importing ' + path + ' ...')
	isdir = os.path.isdir(path)
	cur.execute('insert into nodes (parent, path, isdir, checksum) values (null,?,?,?)', \
		(path, isdir, GetChecksum(path, isdir)))
	if isdir:
		ImportRecurse(dbcon, cur.lastrowid, path)
	cur.close()
	dbcon.commit()
	log.Print(0, 'done\n')

def ImportRecurse(dbcon, rowid, path):
	"""
	Helper function of import
	"""
	cur = dbcon.cursor()
	entries = os.listdir(path)
	for e in entries:
		fullpath = os.path.join(path, e)
		isdir = os.path.isdir(fullpath)
		log.Print(0, 'importing ' + fullpath + ' ...')
		cur.execute('insert into nodes (parent, path, isdir, checksum) values (?,?,?,?)', \
			(rowid, e, isdir, GetChecksum(fullpath, isdir)))
		if isdir:
			ImportRecurse(dbcon, cur.lastrowid, fullpath)
	cur.close()

def Update(dbcon, path):
	"""
	Update contents of database by adding new directory entries,
	deleting non-existing ones and by checking all the other ones.
	If path is specified, it must be the root of a directory tree under control
	of dtcon2 and already existing in the database, if the root is not specified,
	all existing trees in the database are processed.
	"""
	cur = dbcon.cursor()
	if path == None:
		cur.execute('select count(rowid) from nodes where parent is null')
		if cur.fetchone()[0] == 0:
			log.Print(3, 'There are no nodes in the database.')
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null')
	else:
		cur.execute('select count(rowid) from nodes where parent is null and path=?', (path,))
		if cur.fetchone()[0] == 0:
			log.Print(3, 'Path ' + path + ' does not exist in the database.')
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null and path=?', (path,))
	for row in cur:
		CheckChecksum(row[1], row[2], row[3])
		if row[2]:
			UpdateRecurse(dbcon, row[0], row[1])
	cur.close()
	dbcon.execute('vacuum')
	dbcon.commit()
	log.Print(0, 'done\n')

def UpdateRecurse(dbcon, rowid, path):
	"""
	Helper function of Update
	"""
	# fetch child nodes and create a map: name -> rowindex
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
	rows = cur.fetchall()
	rowdict = {}
	for i in range(len(rows)):
		rowdict[rows[i][1]] = i
	# iterate over all directory entries and check them one by one
	entries = os.listdir(path)
	for e in entries:
		fullpath = os.path.join(path, e)
		isdir = os.path.isdir(fullpath)
		if e in rowdict:
			row = rows[rowdict[e]]
			# check file
			CheckChecksum(fullpath, row[2], row[3])
			# remove checked entry from dictionary: this node is processed
			del rowdict[e]
			# if directory do the recursion
			if isdir:
				UpdateRecurse(dbcon, row[0], fullpath)
		else:
			# add non-existing entry to list
			log.Print(1, 'adding ' + fullpath)
			cur.execute('insert into nodes (parent, path, isdir, checksum) values (?,?,?,?)', \
				(rowid, e, isdir, GetChecksum(fullpath, isdir)))
			# if directory do the recursion
			if isdir:
				UpdateRecurse(dbcon, cur.lastrowid, fullpath)
	# iterate over remaining entries in rowdict, those entries should be removed
	for i in rowdict.values():
		row = rows[i]
		log.Print(1, 'deleting ' + os.path.join(path, row[1]))
		DeleteRecurse(dbcon, row[0])
		cur.execute('delete from nodes where rowid=?', (row[0],))
	cur.close()

def Delete(dbcon, path):
	"""
	Delete a path and all its contents recursively from the database.
	If path is specified, it must be the root of a directory tree under control
	of dtcon2 and already existing in the database, if the root is not specified,
	all existing trees in the database are processed.
	"""
	if path == None:
		dbcon.execute('delete from nodes where parent not null')
		dbcon.execute('update nodes set checksum=null where parent is null')
	else:
		cur = dbcon.cursor()
		cur.execute('select count(rowid) from nodes where parent is null and path=?', (path,))
		if cur.fetchone()[0] == 0:
			log.Print(3, 'Path ' + path + ' does not exist in the database.')
		cur.execute('select rowid,isdir from nodes where parent is null and path=?', (path,))
		row = cur.fetchone()
		if row[1]:
			DeleteRecurse(dbcon, row[0])
		cur.execute('update nodes set checksum=null where parent=?', (row[0],))
		cur.close()
	dbcon.commit()
	log.Print(0, 'done\n')

def DeleteRecurse(dbcon, rowid):
	"""
	Helper function of Delete. Can be used to recursively delete a tree or subtree by rowid
	"""
	cur = dbcon.cursor()
	cur.execute('select rowid,isdir from nodes where parent=?', (rowid,))
	for row in cur:
		if row[1]:
			DeleteRecurse(dbcon, row[0])
	cur.execute('delete from nodes where parent=?', (rowid,))
	cur.close()

def ExecuteOnAllNodes(dbcon, path, nodefunc, param):
	"""
	Execute nodefunc on every node in the database. Is used by Print, Export and Check.
	It takes the contents of the database as reference and does not access the
	contents of the file system, even this can be done using nodefunc.
	If path is specified, it must be the root of a directory tree under control
	of dtcon2 and already existing in the database, if the root is not specified,
	all existing trees in the database are processed.
	"""
	cur = dbcon.cursor()
	if path == None:
		cur.execute('select count(rowid) from nodes where parent is null')
		if cur.fetchone()[0] == 0:
			log.Print(3, 'There are no nodes in the database.')
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null')
	else:
		cur.execute('select count(rowid) from nodes where parent is null and path=?', (path,))
		if cur.fetchone()[0] == 0:
			log.Print(3, 'Path ' + path + ' does not exist in the database.')
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null and path=?', (path,))
	for row in cur:
		nodefunc(dbcon, row[0], None, row[1], row[1], row[2], row[3], param, 0)
		if row[2]:
			ExecuteOnAllRecurse(dbcon, row[0], row[1], nodefunc, param, 1)
	cur.close()

def ExecuteOnAllRecurse(dbcon, rowid, path, nodefunc, param, depth):
	"""
	Helper function of ExecuteOnAllNodes
	"""
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
	for row in cur:
		fullpath = os.path.join(path, row[1])
		nodefunc(dbcon, row[0], rowid, row[1], fullpath, row[2], row[3], param, depth)
		if row[2]:
			ExecuteOnAllRecurse(dbcon, row[0], fullpath, nodefunc, param, depth + 1)
	cur.close()

def PrintNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	"""
	Helper function of Print
	"""
	if depth == 0:
		log.Print(0, 'root (id {0:d}, isdir {1:b}): {2:s}'.\
			format(rowid, isdir, fullpath))
	else:
		log.Print(0, '{0:s}node (id {1:d}, parent {2:d}, isdir {3:b}): {4:s}'.\
			format(depth * '  ', rowid, parent, isdir, fullpath))

def Print(dbcon, path):
	"""
	Print tree structure in database to the console.
	Makes only sense for small directory trees and for debugging.
	If path is specified, it must be the root of a directory tree under control
	of dtcon2 and already existing in the database, if the root is not specified,
	all existing trees in the database are processed.
	"""
	ExecuteOnAllNodes(dbcon, path, PrintNode, None)
	log.Print(0, '')

def ExportNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	"""
	Helper function of Export
	"""
	if isdir:
		shape = 'box'
	else:
		shape = 'ellipse'
	if depth == 0:
		param.write('\t{0:d} [ style=bold, shape={1:s}, label="{0:d}\\n{2:s}\\n{3:s}" ];\n'\
			.format(rowid, shape, fullpath.replace('\\', '\\\\'), ChecksumToString(checksum, True)))
	else:
		param.write('\t{0:d} [ shape={1:s}, label="{0:d}\\n{2:s}\\n{3:s}" ];\n'\
			.format(rowid, shape, path, ChecksumToString(checksum, True)))
		param.write('\t{0:d} -> {1:d};\n'.format(parent, rowid))

def Export(dbcon, path, filename):
	"""
	Export tree structure in database to a svg showing a graphical representation of the
	node tree in the database. Makes only sense for small directory trees and for debugging.
	If path is specified, it must be the root of a directory tree under control
	of dtcon2 and already existing in the database, if the root is not specified,
	all existing trees in the database are processed.
	"""
	f = open(filename + '.dot', 'w')
	f.write('digraph G\n{\n')
	ExecuteOnAllNodes(dbcon, path, ExportNode, f)
	f.write('}\n')
	f.close()
	ExecuteShell('dot -Tsvg -o' + filename + '.svg ' + filename + '.dot')
	os.remove(filename + '.dot')
	
def CheckNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	"""
	Helper function of Check
	"""
	CheckChecksum(fullpath, isdir, checksum)

def Check(dbcon, path):
	"""
	For each entry in the database check the checksum
	(Does not update the database, e.g. if directory structure contains
	new entries or if database contains no longer existing ones, check
	Update if you want that functionality)
	If path is specified, it must be the root of a directory tree under control
	of dtcon2 and already existing in the database, if the root is not specified,
	all existing trees in the database are processed.
	"""
	ExecuteOnAllNodes(dbcon, path, CheckNode, None)
	log.Print(0, 'done\n')

def Main():
	"""
	Main entry point of program
	"""
	dbcon = OpenDatabase(':memory:')
	filename = 'dtcon2.sqlite'
	dbcon = OpenDatabase(filename)

	#Import(dbcon, 'C:\\Projects')

	#Check(dbcon, 'C:\\Projects')

	#Delete(dbcon, None)
	Update(dbcon, 'C:\\Projects')

	#Export(dbcon, None, 'schema')

	CloseDatabase(filename, dbcon)

Main()
