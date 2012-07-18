#!/usr/bin/env python

import binascii
import datetime
import hashlib
import os
import sqlite3
import sys
import wx
import wx.lib.mixins.listctrl as listmix



ProgramName = 'dtint'
ProgramVersion = '3.0'



class Checksum:

	def __init__(self):
		self.__checksum = None # is of type 'buffer'
		self.__checksumbits = 256

	def Calculate(self, path):
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

	def SetBinary(self, checksum):
		if not len(checksum) == self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = checksum

	def GetBinary(self):
		return self.__checksum

	def SetString(self, checksum):
		if not len(checksum) == 2*self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = binascii.unhexlify(checksum)

	def GetString(self, short=False):
		if self.__checksum == None:
			return '<none>'
		else:
			if short:
				return binascii.hexlify(self.__checksum[0:7]).decode('utf-8') + '...'
			else:
				return binascii.hexlify(self.__checksum).decode('utf-8')

	def WriteToFile(self, path):
		f = open(path, 'w')
		f.write(self.GetString())
		f.close()

	def IsValid(self, path):
		f = open(path, 'r')
		csum = f.read()
		f.close()
		return csum == self.GetString()

	def Print(self):
		print(self.GetString())

	def IsEqual(self, other):
		return self.GetString() == other.GetString()



class MyException(Exception):

	def __init__(self, message, level):
		super(MyException, self).__init__(message)
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



class Node:

	def __init__(self):
		self.pythonid = id(self)
		self.nodeid = None
		self.parentid = None
		self.name = None
		self.path = None
		self.isdir = None
		self.size = None
		self.ctime = None
		self.atime = None
		self.mtime = None
		self.checksum = None

		self.children = None
		self.similar = None

		self.NoneString = ''

	def GetPythonID(self):
		return self.pythonid

	def GetNodeIDString(self):
		if self.nodeid == None:
			return self.NoneString
		else:
			return '{0:d}'.format(self.nodeid)

	def GetParentIDString(self):
		if self.parentid == None:
			return self.NoneString
		else:
			return '{0:d}'.format(self.parentid)

	def GetNameString(self):
		if self.name == None:
			return self.NoneString
		else:
			return self.name

	def GetPathString(self):
		if self.path == None:
			return self.NoneString
		else:
			return self.path

	def GetIsDirString(self):
		if self.isdir == None:
			return self.NoneString
		else:
			return '{0:b}'.format(self.isdir)

	def GetSizeString(self):
		if self.size == None:
			return self.NoneString
		else:
			if self.size < 1000:
				sizestr = '{0:d}'.format(self.size)
			elif self.size < 1000**2:
				sizestr = '{0:.1f}K'.format(self.size/1000)
			elif self.size < 1000**3:
				sizestr = '{0:.1f}M'.format(self.size/1000**2)
			elif self.size < 1000**4:
				sizestr = '{0:.1f}G'.format(self.size/1000**3)
			elif self.size < 1000**5:
				sizestr = '{0:.1f}T'.format(self.size/1000**4)
			elif self.size < 1000**6:
				sizestr = '{0:.1f}P'.format(self.size/1000**5)
			else:
				sizestr = '{0:.1f}E'.format(self.size/1000**6)
			return sizestr + 'B'

	def GetCTimeString(self):
		if self.ctime == None:
			return self.NoneString
		else:
			return self.ctime.strftime('%Y-%m-%d %H:%M:%S')

	def GetATimeString(self):
		if self.atime == None:
			return self.NoneString
		else:
			return self.atime.strftime('%Y-%m-%d %H:%M:%S')

	def GetMTimeString(self):
		if self.mtime == None:
			return self.NoneString
		else:
			return self.mtime.strftime('%Y-%m-%d %H:%M:%S')

	def GetChecksumString(self):
		if self.checksum == None:
			return self.NoneString
		else:
			return self.checksum.GetString(True)

	def Print(self, prefix=''):
		print('{0:s}nodeid              {1:s}'.format(prefix, self.GetNodeIDString()))
		print('{0:s}parentid            {1:s}'.format(prefix, self.GetParentIDString()))
		print('{0:s}name                {1:s}'.format(prefix, self.GetNameString()))
		print('{0:s}path                {1:s}'.format(prefix, self.GetPathString()))
		print('{0:s}isdir               {1:s}'.format(prefix, self.GetIsDirString()))
		print('{0:s}size                {1:s}'.format(prefix, self.GetSizeString()))
		print('{0:s}creation time       {1:s}'.format(prefix, self.GetCTimeString()))
		print('{0:s}access time         {1:s}'.format(prefix, self.GetATimeString()))
		print('{0:s}modification time   {1:s}'.format(prefix, self.GetMTimeString()))
		print('{0:s}checksum            {1:s}'.format(prefix, self.GetChecksumString()))



class NodeContainer:

	def PrintRecurse(self, nodes, depth):
		for n in nodes:
			n.Print(depth * '    ')
			#print((depth * '    ') + n.name)
			if not n.children == None:
				self.PrintRecurse(n.children, depth + 1)

	def Print(self):
		self.PrintRecurse(self, 0)



class NodeList(NodeContainer, list):
	pass



class NodeTree(NodeContainer):

	def __init__(self):
		self.__dictByID = {}
		self.__dictByName = {}

	def append(self, node):
		self.__dictByID[node.GetPythonID()] = node
		self.__dictByName[node.name] = node

	def __iter__(self):
		return self.__dictByID.itervalues()

	def __getitem__(self, key):
		return self.__dictByID.values().__getitem__(key)

	def clear(self):
		self.__dictByID.clear()
		self.__dictByName.clear()

	def GetByPythonID(self, pythonid):
		return self.__dictByID[pythonid]

	def GetByName(self, name):
		return self.__dictByName[name]



class Tree:

	def Reset(self):
		raise MyException('Not implemented.', 3)

	def GetRootNode(self):
		raise MyException('Not implemented.', 3)

	def Fetch(self, node):
		raise MyException('Not implemented.', 3)

	def GetChildren(self, node):
		raise MyException('Not implemented.', 3)

	def GetParent(self, node):
		raise MyException('Not implemented.', 3)

	def GetNodeByPath(self, path):
		raise MyException('Not implemented.', 3)

	def GetTreeRecurse(self, nodetree):
		for node in nodetree:
			if node.isdir:
				node.children = self.GetChildren(node)
				self.GetTreeRecurse(node.children)

	def GetTree(self):
		nodetree = NodeTree()
		nodetree.append(self.GetRootNode())
		self.GetTreeRecurse(nodetree)
		return nodetree



# --- SQL strings for database access ---
# Always keep in sync with Node and NodeInfo classes!
# Careful with changing spaces: some strings are auto-generated!
DatabaseCreateString = \
	'nodeid integer primary key,' + \
	'parent integer,' + \
	'name text,' + \
	'isdir boolean not null,' + \
	'size integer,' + \
	'ctime timestamp,' + \
	'atime timestamp,' + \
	'mtime timestamp,' + \
	'checksum blob'
DatabaseVarNames = [s.split(' ')[0] for s in DatabaseCreateString.split(',')]
DatabaseInsertVars = ','.join(DatabaseVarNames[1:])
DatabaseInsertQMarks = (len(DatabaseVarNames)-2) * '?,' + '?'
DatabaseSelectString = ','.join(DatabaseVarNames)
DatabaseUpdateString = '=?,'.join(DatabaseVarNames[1:]) + '=?'



class Database(Tree):

	def __init__(self, dbfile, sgfile):
		self.__dbFile = dbfile
		self.__sgFile = sgfile
		self.__dbcon = None

	def __del__(self):
		if self.IsOpen():
			self.CloseAndSecure()

	def Open(self):
		self.__dbcon = sqlite3.connect(self.__dbFile, \
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
		cs.Calculate(self.__dbFile)
		if not cs.IsValid(self.__sgFile):
			raise MyException('The internal database has been corrupted.', 3)
		self.Open()

	def Close(self):
		self.__dbcon.close()
		self.__dbcon = None

	def CloseAndSecure(self):
		self.Close()
		cs = Checksum()
		cs.Calculate(self.__dbFile)
		cs.WriteToFile(self.__sgFile)

	def IsOpen(self):
		return not self.__dbcon == None

	def Reset(self):
		# close if it was open
		wasOpen = self.IsOpen()
		if wasOpen:
			self.Close()
		# delete files if existing
		if os.path.exists(self.__dbFile):
			os.remove(self.__dbFile)
		if os.path.exists(self.__sgFile):
			os.remove(self.__sgFile)
		# create database
		self.Open()
		self.__dbcon.execute('create table nodes (' + DatabaseCreateString + ')')
		self.__dbcon.execute('create index checksumindex on nodes (checksum)')
		self.CloseAndSecure()
		# reopen if necessary
		if wasOpen:
			self.CheckAndOpen()

	def GetRootNode(self):
		node = Node()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent is null')
		self.Fetch(node, cursor.fetchone())
		node.path = ''
		cursor.close()
		return node

	def Fetch(self, node, row):
		node.nodeid = row[0]
		node.parentid = row[1]
		node.name = row[2]
		node.isdir = row[3]
		node.size = row[4]
		node.ctime = row[5]
		node.atime = row[6]
		node.mtime = row[7]
		if not node.isdir:
			node.checksum = Checksum()
			node.checksum.SetBinary(row[8])

	def GetChildren(self, node):
		result = NodeTree()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent=?', (node.nodeid,))
		for row in cursor:
			child = Node()
			self.Fetch(child, row)
			result.append(child)
		cursor.close()
		return result

	def GetParent(self, node):
		if node.parentid == None:
			return None
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where nodeid=?', (node.parentid,))
		parent = Node()
		self.Fetch(parent, cursor.fetchone())
		cursor.close()
		return parent

	def GetNodeByPath(self, path):
		if path == '':
			node = self.GetRootNode()
			node.path = ''
			return node
		# split path into list of names
		namelist = []
		p = path
		while not p == '':
			s = os.path.split(p)
			namelist.append(s[1])
			p = s[0]
		# traverse through tree until last but one entry
		cursor = self.__dbcon.cursor()
		cursor.execute('select nodeid from nodes where parent is null')
		nodeid = cursor.fetchone()[0]
		while len(namelist) > 1:
			cursor.execute('select nodeid from nodes where parent=? and name=?', \
				(nodeid, namelist.pop()))
			nodeid = cursor.fetchone()[0]
		# get last entry and fetch its information
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where parent=? and name=?', (nodeid, namelist.pop()))
		node = Node()
		self.Fetch(node, cursor.fetchone())
		node.path = path
		cursor.close()
		return node

	def GetPath(self, node):
		n = node
		namelist = []
		while True:
			if n == None:
				break
			else:
				namelist.append(n.name)
			n = self.GetParent(n)
		namelist.reverse()
		node.path = reduce(lambda x, y: os.path.join(x, y), namelist)

	def GetNodesWithSameChecksum(self, checksum):
		result = NodeList()
		cursor = self.__dbcon.cursor()
		cursor.execute('select ' + DatabaseSelectString + \
			' from nodes where checksum=X\'{0:s}\''.format(checksum.GetString()))
		for row in cursor:
			child = Node()
			self.Fetch(child, row)
			result.append(child)
		cursor.close()
		return result

	def InsertNode(self, node):
		if not node.nodeid == None:
			raise MyException('Node already contains a valid node id, ' + \
				'so maybe you want to update instead of insert?', 3)
		cursor = self.__dbcon.cursor()
		if node.checksum == None:
			checksum = None
		else:
			checksum = node.checksum.GetBinary()
		cursor.execute('insert into nodes (' + DatabaseInsertVars + \
			') values (' + DatabaseInsertQMarks + ')', \
			(node.parentid, node.name, node.isdir, node.size, \
			node.ctime, node.atime, node.mtime, checksum))
		node.nodeid = cursor.lastrowid
		cursor.close()

	def Commit(self):
		self.__dbcon.commit()
		self.__dbcon.execute('vacuum')



class Filesystem(Tree):

	def __init__(self, rootDir, metaDir):
		if not os.path.exists(rootDir):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(rootDir):
			raise MyException('Given root directory is not a directory.', 3)
		self.__rootDir = rootDir
		if not os.path.exists(metaDir):
			raise MyException('Given meta data directory does not exist.', 3)
		if not os.path.isdir(metaDir):
			raise MyException('Given meta data directory is not a directory.', 3)
		self.__metaDir = metaDir

	def Reset(self):
		if not os.path.exists(self.__metaDir):
			os.mkdir(self.__metaDir)

	def GetRootNode(self):
		node = Node()
		node.path = ''
		self.Fetch(node)
		return node

	def Fetch(self, node):
		fullpath = os.path.join(self.__rootDir, node.path)
		if not os.path.exists(fullpath):
			raise MyException('Cannot fetch data for non-existing path.', 3)
		node.name = os.path.split(node.path)[1]
		node.isdir = os.path.isdir(fullpath)
		node.size = os.path.getsize(fullpath)
		# this conversion from unix time stamp to local date/time might fail after year 2038...
		node.ctime = datetime.datetime.fromtimestamp(os.path.getctime(fullpath))
		node.atime = datetime.datetime.fromtimestamp(os.path.getatime(fullpath))
		node.mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))
		if not node.isdir:
			node.checksum = Checksum()
			node.checksum.Calculate(fullpath)

	def GetChildren(self, node):
		result = NodeTree()
		for childname in os.listdir(os.path.join(self.__rootDir, node.path)):
			childpath = os.path.join(node.path, childname)
			if os.path.samefile(os.path.join(self.__rootDir, childpath), self.__metaDir):
				continue
			child = Node()
			child.path = childpath
			child.parentid = node.nodeid # important when importing nodes into the db
			self.Fetch(child)
			result.append(child)
		return result

	def GetParent(self, node):
		if node.path == '':
			return None
		parent = Node()
		parent.path = os.path.split(node.path)[0]
		self.Fetch(parent)
		return parent

	def GetNodeByPath(self, path):
		if not os.path.join(self.__rootDir, path):
			return None
		node = Node()
		node.path = path
		self.Fetch(node)
		return node



class Instance:

	def __init__(self, rootDir):
		if not os.path.exists(rootDir):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(rootDir):
			raise MyException('Given root directory is not a directory.', 3)
		metaDir = os.path.join(rootDir, '.' + ProgramName)
		self.__fs = Filesystem(rootDir, metaDir)
		dbfile = os.path.join(metaDir, 'base.sqlite3')
		sgfile = os.path.join(metaDir, 'base.signature')
		self.__db = Database(dbfile, sgfile)

	def Reset(self):
		self.__fs.Reset()
		self.__db.Reset()

	def Open(self):
		self.__db.CheckAndOpen()

	def Close(self):
		self.__db.CloseAndSecure()

	def ImportRecurse(self, nodelist):
		for node in nodelist:
			self.__db.InsertNode(node)
			if node.isdir:
				self.ImportRecurse(self.__fs.GetChildren(node))

	def Import(self):
		nodelist = NodeTree()
		nodelist.append(self.__fs.GetRootNode())
		self.ImportRecurse(nodelist)
		self.__db.Commit()

	def Test(self):
		n = self.__fs.GetRootNode()
		return self.__fs.GetChildren(n)



###########################################
################### GUI ###################
###########################################



class ListControl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):

	def __init__(self, parent):
		wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT | wx.LC_SORT_ASCENDING)

		self.coldefs = \
			[ \
				('', 32), \
				('Name', 200), \
				('Dir', 32), \
				('Size', 130), \
				('CTime', 142), \
				('ATime', 142), \
				('MTime', 142), \
				('Checksum', 132)
			]

		index = 0
		for coldef in self.coldefs:
			self.InsertColumn(index, coldef[0])
			self.SetColumnWidth(index, coldef[1])
			index = index + 1

		listmix.ListCtrlAutoWidthMixin.__init__(self)
		self.setResizeColumn(2)

	def AppendNode(self, node):
		index = self.GetItemCount()
		self.InsertStringItem(index, 'OK')
		self.SetStringItem(index, 1, node.name)
		self.SetStringItem(index, 2, node.GetIsDirString())
		self.SetStringItem(index, 3, node.GetSizeString())
		self.SetStringItem(index, 4, node.GetCTimeString())
		self.SetStringItem(index, 5, node.GetATimeString())
		self.SetStringItem(index, 6, node.GetMTimeString())
		self.SetStringItem(index, 7, node.GetChecksumString())
		self.SetItemData(index, node.GetPythonID())



class ListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		self.list = ListControl(self)
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)

		self.nodetree = None

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

	def ShowNodeTree(self, nodetree):
		self.list.DeleteAllItems()
		self.nodetree = nodetree
		for node in self.nodetree:
			self.list.AppendNode(node)

	def OnItemSelected(self, event):
		index = event.m_itemIndex
		pythonid = self.list.GetItemData(index)
		node = self.nodetree.GetByPythonID(pythonid)
		print(node.name)



class MainFrame(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, title='dtint', size=(1024,768))

		# main menue definition
		fileMenu = wx.Menu()
		menuOpen = fileMenu.Append(wx.ID_OPEN, 'Open', 'Open Directory')
		self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
		fileMenu.AppendSeparator()
		menuExit = fileMenu.Append(wx.ID_EXIT, 'E&xit', 'Terminate Program')
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		helpMenu = wx.Menu()
		menuAbout = helpMenu.Append(wx.ID_ABOUT, 'About', 'Information about this program')
		self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
		# assemble menu
		menuBar = wx.MenuBar()
		menuBar.Append(fileMenu, '&File')
		menuBar.Append(helpMenu, 'Help')
		self.SetMenuBar(menuBar)

		# main window consists of address line and directory listing
		self.address = wx.TextCtrl(self, -1, style=wx.TE_READONLY)
		self.address.SetValue('/home/phil/Data')
		self.list = ListControlPanel(self)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.address, 0, wx.ALL | wx.EXPAND, 5)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

		self.CreateStatusBar()

		self.Show(True)

	def OnOpen(self, event):
		inst = Instance('../dtint-example')
		inst.Reset()
		inst.Open()
		inst.Import()
		n = inst.Test()
		self.list.ShowNodeTree(n)
		inst.Close()

	def OnExit(self, event):
		self.Close(True)

	def OnAbout(self, event):
		pass



if __name__ == '__main__':
	app = wx.App(False)
	frame = MainFrame(None)
	frame.Show()
	app.MainLoop()