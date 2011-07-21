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
		print("Warning: " + message)
	elif (lvl == 1):
		print("### Error: " + message)
	elif (lvl == 2):
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

def CheckFileChecksum(path, checksum):
	if checksum != GetFileChecksum(path):
		LogPrint(1, 'Checksum error for file ' + path)

def GetDirChecksum(path):
	checksum = hashlib.sha256()
	entries = os.listdir(path)
	for e in entries:
		checksum.update(e.encode('utf-8'))
	return checksum.hexdigest()

def CheckDirChecksum(path, checksum):
	if checksum != GetDirChecksum(path):
		LogPrint(1, 'Checksum error for directory ' + path)

def Import(dbcon, path):
	print('importing ' + path + ' ...')
	# TODO: check if path already exists as a root node
	cur = dbcon.cursor()
	if os.path.isdir(path):
		cur.execute('insert into nodes (parent, path, isdir, checksum) values(null,?,?,?)', \
			(path, True, GetDirChecksum(path)))
		ImportRecurse(dbcon, cur.lastrowid, path)
	elif os.path.isfile(path):
		cur.execute('insert into nodes (parent, path, isdir, checksum) values(null,?,?,?)', \
			(path, False, GetFileChecksum(path)))
	else:
		LogPrint(2, 'Unknown directory entry ' + path + '.')
	cur.close()

def ImportRecurse(dbcon, rowid, path):
	print('importing ' + path + ' ...')
	cur = dbcon.cursor()
	entries = os.listdir(path)
	for e in entries:
		fullpath = os.path.join(path, e)
		if os.path.isdir(fullpath):
			cur.execute('insert into nodes (parent, path, isdir, checksum) values(?,?,?,?)', \
				(rowid, e, True, GetDirChecksum(fullpath)))
			ImportRecurse(dbcon, cur.lastrowid, fullpath)
		elif os.path.isfile(fullpath):
			cur.execute('insert into nodes (parent, path, isdir, checksum) values(?,?,?,?)', \
				(rowid, e, False, GetFileChecksum(fullpath)))
		else:
			LogPrint(2, 'Unknown directory entry.')
	cur.close()

def Delete(dbcon, path):
	if path == None:
		dbcon.execute('delete from nodes where parent not null')
		dbcon.execute('update nodes set checksum=null where parent is null')
	else:
		cur = dbcon.cursor()
		cur.execute('select rowid,isdir from nodes where parent is null and path=?', (path,))
		row = cur.FetchOne();
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

def ExecuteOnAllNodes(dbcon, path, rootfunc, innernodefunc, param):
	cur = dbcon.cursor()
	if path == None:
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null')
	else:
		cur.execute('select rowid,path,isdir,checksum from nodes where parent is null and path=?', (path,))
	for row in cur:
		if row[2]:
			if not os.path.isdir(row[1]):
				LogPrint(1, 'There is no directory ' + row[1] + ', so we are ignoring it')
				return
			rootfunc(dbcon, row[0], None, row[1], row[1], row[2], row[3], param)
			ExecuteOnAllRecurse(dbcon, row[0], row[1], innernodefunc, param)
		else:
			if not os.path.isfile(row[1]):
				LogPrint(1, 'There is no file ' + row[1] + ', so we are ignoring it')
				return
			rootfunc(dbcon, row[0], None, row[1], row[1], row[2], row[3], param)
	cur.close()

def ExecuteOnAllRecurse(dbcon, rowid, path, innernodefunc, param):
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
	for row in cur:
		fullpath = os.path.join(path, row[1])
		if row[2]:
			if not os.path.isdir(fullpath):
				LogPrint(1, 'There is no directory ' + fullpath + ', so we are ignoring it')
				return
			innernodefunc(dbcon, row[0], rowid, row[1], fullpath, row[2], row[3], param)
			ExecuteOnAllRecurse(dbcon, row[0], fullpath, innernodefunc, param)
		else:
			if not os.path.isfile(fullpath):
				LogPrint(1, 'There is no file ' + fullpath + ', so we are ignoring it')
				return
			innernodefunc(dbcon, row[0], rowid, row[1], fullpath, row[2], row[3], param)
	cur.close()

def PrintRoot(dbcon, rowid, parent, path, fullpath, isdir, checksum, param):
	print('### root node (id {0:d}): {1:s}'.format(rowid, fullpath))

def PrintInnerNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param):
	print('node (id {0:d}, parent {1:d}, isdir {2:b}): {3:s}'.format(rowid, parent, isdir, fullpath))

def ExportRoot(dbcon, rowid, parent, path, fullpath, isdir, checksum, param):
	if isdir:
		shape = 'box'
	else:
		shape = 'ellipse'
	param.write('\t{0:d} [ style=bold, shape={1:s}, label="{2:s}\\n{3:s}..." ];\n'\
		.format(rowid, shape, fullpath.replace('\\', '\\\\'), checksum[0:15]))

def ExportInnerNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param):
	if isdir:
		shape = 'box'
	else:
		shape = 'ellipse'
	param.write('\t{0:d} [ shape={1:s}, label="{2:s}\\n{3:s}..." ];\n'\
		.format(rowid, shape, path, checksum[0:15]))
	param.write('\t{0:d} -> {1:d};\n'.format(parent, rowid))

def CheckNode(dbcon, rowid, parent, path, fullpath, isdir, checksum, param):
	print('checking ' + fullpath + ' ...')
	if isdir:
		CheckDirChecksum(fullpath, checksum)
	else:
		CheckFileChecksum(fullpath, checksum)

def PrintNodes(dbcon, path):
	ExecuteOnAllNodes(dbcon, path, PrintRoot, PrintInnerNode, None)

def ExportNodeToDot(dbcon, path, filename):
	f = open(filename + '.dot', 'w')
	f.write('digraph G\n{\n')
	ExecuteOnAllNodes(dbcon, path, ExportRoot, ExportInnerNode, f)
	f.write('}\n')
	f.close()
	ExecuteShell('dot -Tpng -o' + filename + '.png ' + filename + '.dot')
	os.remove(filename + '.dot')
	
def CheckNodes(dbcon, path):
	ExecuteOnAllNodes(dbcon, path, CheckNode, CheckNode, None)

dbcon = sqlite3.connect(':memory:')
CreateTables(dbcon)
Import(dbcon, 'C:\\Projects\\Others\dtcon2\\test')
Import(dbcon, 'C:\\Projects\\Others\\dtcon2\\checkformat.py')
PrintNodes(dbcon, None)
Delete(dbcon, None)
PrintNodes(dbcon, None)
#CheckNodes(dbcon, None)
#ExportNodeToDot(dbcon, None, 'test')
dbcon.close()

