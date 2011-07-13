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
	dbcon.execute('delete from nodes')

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

def Check(dbcon, rowid, path, isdir, checksum):
	print('checking ' + path + ' ...')
	if isdir:
		if not os.path.isdir(path):
			LogPrint(1, 'There is no directory ' + path + ', so we are ignoring it')
			return
		CheckDirChecksum(path, checksum)
		childnodes = dbcon.cursor()
		childnodes.execute('select rowid,path,isdir,checksum from nodes where parent=?', (rowid,))
		for row in childnodes:
			Check(dbcon, row[0], os.path.join(path,row[1]), row[2], row[3])
		childnodes.close()
	else:
		if not os.path.isfile(path):
			LogPrint(1, 'There is no file ' + path + ', so we are ignoring it')
			return
		CheckFileChecksum(path, checksum)

def DoWithOneRoot(dbcon, path, func):
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent is null and path=?', (path,))
	row = cur.fetchone()
	func(dbcon, row[0], row[1], row[2], row[3])
	cur.close()
	
def DoWithAllRoots(dbcon, func):
	cur = dbcon.cursor()
	cur.execute('select rowid,path,isdir,checksum from nodes where parent is null')
	for row in cur:
		func(dbcon, row[0], row[1], row[2], row[3])
	cur.close()



dbcon = sqlite3.connect(':memory:')
CreateTables(dbcon)
dbcon.execute('insert into nodes values (null, "C:\\Projects\\src\\Mathlib", 1, "9c5c210cf46dab4dbe6599fdcf48d704aa8509bede853467bb794dbe9324a92e")')
dbcon.execute('insert into nodes values (1,    "MathLib.sln",                0, "f051d99dcfe20aa882eb4821860b3bf0b5073950161580e8d0e56e73eb1d6290")')
DoWithAllRoots(dbcon, Check)
dbcon.close()

