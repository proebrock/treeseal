import sqlite3
import sys
import os
import hashlib

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

def ClearDB(dbcon):
	# TODO: accept name here
	# delete all nodes except the root nodes
	dbcon.execute('delete from nodes where parent not null')
	# clear all existing checksums for root nodes
	dbcon.execute('update nodes set checksum=null where parent is null')

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

def ExecuteOnAllNodes(dbcon, path, rootfunc, innernodefunc):
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
			rootfunc(dbcon, row[0], None, row[1], row[1], row[2], row[3])
			ExecuteOnAllRecurse(dbcon, row[0], row[1], innernodefunc)
		else:
			if not os.path.isfile(row[1]):
				LogPrint(1, 'There is no file ' + row[1] + ', so we are ignoring it')
				return
			rootfunc(dbcon, row[0], None, row[1], row[1], row[2], row[3])
	cur.close()

def ExecuteOnAllRecurse(dbcon, rowid, path, innernodefunc):
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
	for row in cur:
		fullpath = os.path.join(path, row[1]);
		if row[2]:
			if not os.path.isdir(fullpath):
				LogPrint(1, 'There is no directory ' + fullpath + ', so we are ignoring it')
				return
			innernodefunc(dbcon, rowid, row[0], row[1], fullpath, row[2], row[3])
			ExecuteOnAllRecurse(dbcon, row[0], fullpath, innernodefunc)
		else:
			if not os.path.isfile(fullpath):
				LogPrint(1, 'There is no file ' + fullpath + ', so we are ignoring it')
				return
			innernodefunc(dbcon, rowid, row[0], row[1], fullpath, row[2], row[3])
	cur.close()

def PrintRoot(dbcon, rowid, parent, path, fullpath, isdir, checksum):
	print('### root node (id {0:d}): {1:s}'.format(rowid, fullpath))

def PrintInnerNode(dbcon, rowid, parent, path, fullpath, isdir, checksum):
	print('node (id {0:d}, parent {1:d}, isdir {2:b}): {3:s}'.format(rowid, parent, isdir, fullpath))

def CheckNode(dbcon, rowid, parent, path, fullpath, isdir, checksum):
	print('checking ' + fullpath + ' ...');
	if isdir:
		CheckDirChecksum(fullpath, checksum)
	else:
		CheckFileChecksum(fullpath, checksum)



dbcon = sqlite3.connect(':memory:')
CreateTables(dbcon)
Import(dbcon, "C:\\Projects\\src\\Mathlib")
Import(dbcon, "C:\\Projects\\Others\\dtcon2\\checkformat.py")
#ExecuteOnAllNodes(dbcon, None, PrintRoot, PrintInnerNode)
ExecuteOnAllNodes(dbcon, None, CheckNode, CheckNode)
dbcon.close()

