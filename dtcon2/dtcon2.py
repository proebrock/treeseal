import sqlite3
import sys
import shlex
import subprocess
import os
import hashlib

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
		'checksum text' + \
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
	return checksum.hexdigest()

def GetDirChecksum(path):
	checksum = hashlib.sha256()
	entries = os.listdir(path)
	for e in entries:
		checksum.update(e.encode('utf-8'))
	return checksum.hexdigest()

def CheckChecksum(path, isdir, checksum):
	if isdir:
		if checksum == None:
			LogPrint(1, 'Checksum not defined for directory ' + path)
		elif checksum != GetDirChecksum(path):
			LogPrint(2, 'Checksum error for directory ' + path)
	else:
		if checksum == None:
			LogPrint(1, 'Checksum not defined for file ' + path)
		elif checksum != GetFileChecksum(path):
			LogPrint(2, 'Checksum error for file ' + path)

def Import(dbcon, path):
	cur = dbcon.cursor()
	cur.execute('select rowid from nodes where parent is null and path=?', (path,))
	if not cur.fetchone() == None:
		LogPrint(3, 'Path ' + path + ' already exists.')
	if os.path.isdir(path):
		print('importing ' + path + ' ...')
		cur.execute('insert into nodes (parent, path, isdir, checksum) values (null,?,?,?)', \
			(path, True, GetDirChecksum(path)))
		ImportRecurse(dbcon, cur.lastrowid, path)
	elif os.path.isfile(path):
		print('importing ' + path + ' ...')
		cur.execute('insert into nodes (parent, path, isdir, checksum) values (null,?,?,?)', \
			(path, False, GetFileChecksum(path)))
	else:
		LogPrint(3, 'Unknown directory entry ' + path + '.')
	cur.close()
	print('done\n')

def ImportRecurse(dbcon, rowid, path):
	cur = dbcon.cursor()
	entries = os.listdir(path)
	for e in entries:
		fullpath = os.path.join(path, e)
		if os.path.isdir(fullpath):
			print('importing ' + fullpath + ' ...')
			cur.execute('insert into nodes (parent, path, isdir, checksum) values (?,?,?,?)', \
				(rowid, e, True, GetDirChecksum(fullpath)))
			ImportRecurse(dbcon, cur.lastrowid, fullpath)
		elif os.path.isfile(fullpath):
			cur.execute('insert into nodes (parent, path, isdir, checksum) values (?,?,?,?)', \
				(rowid, e, False, GetFileChecksum(fullpath)))
		else:
			LogPrint(3, 'Unknown directory entry.')
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
		cur.execute('delete from nodes where parent=?', (row[0],))
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
		if row[2]:
			if not os.path.isdir(row[1]):
				LogPrint(2, 'There is no directory ' + row[1] + ', so we are ignoring it')
			else:
				nodefunc(dbcon, row[0], None, row[1], row[1], row[2], row[3], param, 0)
				ExecuteOnAllRecurse(dbcon, row[0], row[1], nodefunc, param, 1)
		else:
			if not os.path.isfile(row[1]):
				LogPrint(2, 'There is no file ' + row[1] + ', so we are ignoring it')
			else:
				nodefunc(dbcon, row[0], None, row[1], row[1], row[2], row[3], param, 0)
	cur.close()

def ExecuteOnAllRecurse(dbcon, rowid, path, nodefunc, param, depth):
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
	for row in cur:
		fullpath = os.path.join(path, row[1])
		if row[2]:
			if not os.path.isdir(fullpath):
				LogPrint(2, 'There is no directory ' + fullpath + ', so we are ignoring it')
			else:
				nodefunc(dbcon, row[0], rowid, row[1], fullpath, row[2], row[3], param, depth)
				ExecuteOnAllRecurse(dbcon, row[0], fullpath, nodefunc, param, depth + 1)
		else:
			if not os.path.isfile(fullpath):
				LogPrint(2, 'There is no file ' + fullpath + ', so we are ignoring it')
			else:
				nodefunc(dbcon, row[0], rowid, row[1], fullpath, row[2], row[3], param, depth)
	cur.close()

def PrintNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	if depth == 0:
		print('root (id {0:d}, isdir {1:b}): {2:s}'.format(rowid, isdir, fullpath))
	else:
		print('{0:s}node (id {1:d}, parent {2:d}, isdir {3:b}): {4:s}'.format(depth * '  ', rowid, parent, isdir, fullpath))

def PrintTree(dbcon, path):
	ExecuteOnAllNodes(dbcon, path, PrintNode, None)
	print('')

def ExportNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param, depth):
	if isdir:
		shape = 'box'
	else:
		shape = 'ellipse'
	if checksum == None:
		csumstr = 'no checksum'
	else:
		csumstr = checksum[0:15] + '...';
	if depth == 0:
		param.write('\t{0:d} [ style=bold, shape={1:s}, label="{0:d}\\n{2:s}\\n{3:s}" ];\n'\
			.format(rowid, shape, fullpath.replace('\\', '\\\\'), csumstr))
	else:
		param.write('\t{0:d} [ shape={1:s}, label="{0:d}\\n{2:s}\\n{3:s}" ];\n'\
			.format(rowid, shape, path, csumstr))
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
	if isdir or depth == 0:
		print('checking ' + fullpath + ' ...')
	CheckChecksum(fullpath, isdir, checksum)

def CheckTree(dbcon, path):
	ExecuteOnAllNodes(dbcon, path, CheckNode, None)
	print('done\n')

dbcon = sqlite3.connect(':memory:')
CreateTables(dbcon)
Import(dbcon, 'C:\\Projects\\Others\dtcon2\\test')
Import(dbcon, 'C:\\Projects\\Others\dtcon2\\test\\test3')
Import(dbcon, 'C:\\Projects\\Others\\dtcon2\\checkformat.py')
PrintTree(dbcon, None)
#ExportTree(dbcon, None, 'tree')
CheckTree(dbcon, None)
dbcon.close()

