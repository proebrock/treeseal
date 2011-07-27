import sqlite3
import sys
import os
import hashlib
import shlex
import subprocess
import time

def ExecuteShell(cmdline):
	args = shlex.split(cmdline)
	fnull = open(os.devnull, 'w')
	proc = subprocess.Popen(args, stdin=fnull, stdout=fnull, stderr=fnull)
	fnull.close()
	proc.communicate()

def LogPrint(lvl, message):
	if (lvl == 0):
		print(message)
	elif (lvl == 1):
		print("Warning: " + message)
	elif (lvl == 2):
		print("### Error: " + message)
	elif (lvl == 3):
		print("### Fatal Error: " + message)
		sys.exit()
	else:
		raise Exception('Unknown log level {0:d}'.format(lvl))

def CreateTables(dbcon):
	dbcon.execute('create table nodes (' + \
		'parent int,' + \
		'path text not null,' + \
		'isdir boolean not null,' + \
		'checksum blob' + \
		')')

def DropTables(dbcon):
	dbcon.execute('drop table nodes')

def GetFileChecksum(path):
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
	checksum = hashlib.sha256()
	entries = os.listdir(path)
	for e in entries:
		if os.path.isdir(e):
			checksum.update(b'\x01')
		else:
			checksum.update(b'\x00')
		checksum.update(e.encode('utf-8'))
	return checksum.digest()

def ChecksumToString(checksum):
	if checksum == None:
		return 'no checksum'
	else:
		return ''.join('%02x' % byte for byte in checksum[0:7]) + '...'

def GetChecksum(path, isdir):
	if isdir:
		return GetDirChecksum(path)
	else:
		return GetFileChecksum(path)

def CheckChecksum(path, isdir, checksum):
	LogPrint(0, 'checking ' + path + ' ...')
	if checksum == None:
		LogPrint(1, 'No checksum defined for ' + path)
	elif checksum != GetChecksum(path, isdir):
		LogPrint(2, 'Checksum error for ' + path)

def Import(dbcon, path):
	cur = dbcon.cursor()
	# check if path is already in the database
	cur.execute('select rowid from nodes where parent is null and path=?', (path,))
	if not cur.fetchone() == None:
		LogPrint(3, 'Path ' + path + ' already exists.')
	# add entry
	LogPrint(0, 'importing ' + path + ' ...')
	isdir = os.path.isdir(path)
	cur.execute('insert into nodes (parent, path, isdir, checksum) values (null,?,?,?)', \
		(path, isdir, GetChecksum(path, isdir)))
	if isdir:
		ImportRecurse(dbcon, cur.lastrowid, path)
	cur.close()
	dbcon.commit()
	LogPrint(0, 'done\n')

def ImportRecurse(dbcon, rowid, path):
	cur = dbcon.cursor()
	entries = os.listdir(path)
	for e in entries:
		fullpath = os.path.join(path, e)
		isdir = os.path.isdir(fullpath)
		LogPrint(0, 'importing ' + fullpath + ' ...')
		cur.execute('insert into nodes (parent, path, isdir, checksum) values (?,?,?,?)', \
			(rowid, e, isdir, GetChecksum(fullpath, isdir)))
		if isdir:
			ImportRecurse(dbcon, cur.lastrowid, fullpath)
	cur.close()

def Update(dbcon, path):
	cur = dbcon.cursor()
	if path == None:
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null')
	else:
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null and path=?', (path,))
	for row in cur:
		CheckChecksum(row[1], row[2], row[3])
		if row[2]:
			UpdateRecurse(dbcon, row[0], row[1])
	cur.close()
	dbcon.commit()
	LogPrint(0, 'done\n')

def UpdateRecurse(dbcon, rowid, path):
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
			LogPrint(1, 'adding ' + fullpath)
			cur.execute('insert into nodes (parent, path, isdir, checksum) values (?,?,?,?)', \
				(rowid, e, isdir, GetChecksum(fullpath, isdir)))
			# if directory do the recursion
			if isdir:
				UpdateRecurse(dbcon, cur.lastrowid, fullpath)
	# iterate over remaining entries in rowdict, those entries should be removed
	for i in rowdict.values():
		row = rows[i]
		LogPrint(1, 'deleting ' + os.path.join(path, row[1]))
		DeleteRecurse(dbcon, row[0])
		cur.execute('delete from nodes where rowid=?', (row[0],))
	cur.close()

def DeleteTree(dbcon, path):
	if path == None:
		dbcon.execute('delete from nodes where parent not null')
		dbcon.execute('update nodes set checksum=null where parent is null')
	else:
		cur = dbcon.cursor()
		cur.execute('select rowid,isdir from nodes where parent is null and path=?', (path,))
		row = cur.fetchone()
		if row[1]:
			DeleteRecurse(dbcon, row[0])
		cur.execute('update nodes set checksum=null where parent=?', (row[0],))
		cur.close()

def DeleteRecurse(dbcon, rowid):
	cur = dbcon.cursor()
	cur.execute('select rowid,isdir from nodes where parent=?', (rowid,))
	for row in cur:
		if row[1]:
			DeleteRecurse(dbcon, row[0])
	cur.execute('delete from nodes where parent=?', (rowid,))
	cur.close()

def ExecuteOnAllNodes(dbcon, path, nodefunc, param):
	cur = dbcon.cursor()
	if path == None:
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null')
	else:
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null and path=?', (path,))
	for row in cur:
		nodefunc(dbcon, row[0], None, row[1], row[1], row[2], row[3], param, 0)
		if row[2]:
			ExecuteOnAllRecurse(dbcon, row[0], row[1], nodefunc, param, 1)
	cur.close()

def ExecuteOnAllRecurse(dbcon, rowid, path, nodefunc, param, depth):
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
	for row in cur:
		fullpath = os.path.join(path, row[1])
		nodefunc(dbcon, row[0], rowid, row[1], fullpath, row[2], row[3], param, depth)
		if row[2]:
			ExecuteOnAllRecurse(dbcon, row[0], fullpath, nodefunc, param, depth + 1)
	cur.close()

def PrintNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	if depth == 0:
		LogPrint(0, 'root (id {0:d}, isdir {1:b}): {2:s}'.\
			format(rowid, isdir, fullpath))
	else:
		LogPrint(0, '{0:s}node (id {1:d}, parent {2:d}, isdir {3:b}): {4:s}'.\
			format(depth * '  ', rowid, parent, isdir, fullpath))

def PrintTree(dbcon, path):
	ExecuteOnAllNodes(dbcon, path, PrintNode, None)
	LogPrint(0, '')

def ExportNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	if isdir:
		shape = 'box'
	else:
		shape = 'ellipse'
	if depth == 0:
		param.write('\t{0:d} [ style=bold, shape={1:s}, label="{0:d}\\n{2:s}\\n{3:s}" ];\n'\
			.format(rowid, shape, fullpath.replace('\\', '\\\\'), ChecksumToString(checksum)))
	else:
		param.write('\t{0:d} [ shape={1:s}, label="{0:d}\\n{2:s}\\n{3:s}" ];\n'\
			.format(rowid, shape, path, ChecksumToString(checksum)))
		param.write('\t{0:d} -> {1:d};\n'.format(parent, rowid))

def ExportTree(dbcon, path, filename):
	f = open(filename + '.dot', 'w')
	f.write('digraph G\n{\n')
	ExecuteOnAllNodes(dbcon, path, ExportNode, f)
	f.write('}\n')
	f.close()
	ExecuteShell('dot -Tpng -o' + filename + '.png ' + filename + '.dot')
	os.remove(filename + '.dot')
	
def CheckNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	CheckChecksum(fullpath, isdir, checksum)

def CheckTree(dbcon, path):
	ExecuteOnAllNodes(dbcon, path, CheckNode, None)
	LogPrint('done\n')

def Main():
	#dbcon = sqlite3.connect(':memory:')
	dbcon = sqlite3.connect('dbcon.sqlite')
	DropTables(dbcon)
	CreateTables(dbcon)
	Import(dbcon, 'C:\\Projects\\Others\dtcon2\\test')
	Import(dbcon, 'C:\\Projects\\Others\dtcon2\\test\\test3')
	Import(dbcon, 'C:\\Projects\\Others\\dtcon2\\checkformat.py')
	DeleteTree(dbcon, 'C:\\Projects\\Others\dtcon2\\test')
	DeleteTree(dbcon, 'C:\\Projects\\Others\dtcon2\\test\\test3')
	DeleteTree(dbcon, 'C:\\Projects\\Others\\dtcon2\\checkformat.py')
	#PrintTree(dbcon, None)
	Update(dbcon, 'C:\\Projects\\Others\dtcon2\\test')
	#PrintTree(dbcon, None)
	#CheckTree(dbcon, None)
	ExportTree(dbcon, None, 'tree')
	dbcon.close()

start = time.clock()
Main()
elapsed = (time.clock() - start)
print('time elapsed {0:.1f}s'.format(elapsed))
