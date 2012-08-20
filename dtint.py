#!/usr/bin/env python

import os
import sys
import wx
import wx.lib.mixins.listctrl as listmix

from icons import IconError, IconMissing, IconNew, IconOk, IconUnknown, IconWarning
from misc import MyException
from node import NodeStatus
from tree import Database, Filesystem
from progressdialog import UserCancelledException, FileProcessingProgressDialog

ProgramName = 'dtint'
ProgramVersion = '3.0'



class Instance:

	METADIRNAME = '.' + ProgramName

	def __init__(self, path):
		# check if specified root dir exists
		if not os.path.exists(path):
			raise MyException('Given root directory does not exist.', 3)
		if not os.path.isdir(path):
			raise MyException('Given root directory is not a directory.', 3)
		# get rootdir (full path) and metadir
		self.__rootDir = path
		self.__metaDir = os.path.join(self.__rootDir, Instance.METADIRNAME)
		# initialize two Trees, the filesystem and the database
		self.__fs = Filesystem(self.__rootDir, self.__metaDir)
		self.__db = Database(self.__rootDir, self.__metaDir)
		#self.__fs = Database(self.__rootDir, self.__metaDir)
		#self.__db = Filesystem(self.__rootDir, self.__metaDir)

	@staticmethod
	def isRootDir(path):
		return os.path.exists(os.path.join(path, Instance.METADIRNAME))

	def getRootDir(self):
		return self.__rootDir

	def open(self):
		self.__fs.open()
		self.__db.open()

	def close(self):
		self.__fs.close()
		self.__db.close()

	def reset(self):
		self.__fs.reset()
		self.__db.reset()

	def importTree(self, signalNewFile=None, signalBytesDone=None):
		self.__fs.registerHandlers(signalNewFile, signalBytesDone)
		if True:
			# fast and memory saving alternative
			self.__fs.copyNodeTree(self.__db)
		else:
			# slower more memory consuming alternative: first the whole tree is read into memory, then it is written
			tree = self.__fs.getNodeTree()
			tree.insert(self.__db)
		self.__fs.registerHandlers(None, None)

	def getStatistics(self):
		return self.__fs.getStatistics(self.__fs.getRootNode())

	def getFilesystemTree(self, signalNewFile=None, signalBytesDone=None):
		self.__fs.registerHandlers(signalNewFile, signalBytesDone)
		tree = self.__fs.getNodeTree()
		self.__fs.registerHandlers(None, None)
		return tree

	def getDatabaseTree(self, signalNewFile=None, signalBytesDone=None):
		self.__db.registerHandlers(signalNewFile, signalBytesDone)
		tree = self.__db.getNodeTree()
		self.__db.registerHandlers(None, None)
		return tree

	def getDiffTree(self, signalNewFile=None, signalBytesDone=None):
		# careful when testing: handlers have to fit to statistics
		# determined in getStatistics!
		self.__fs.registerHandlers(signalNewFile, signalBytesDone)
		tree = self.__fs.recursiveGetDiffTree(self.__db)
		self.__fs.registerHandlers(None, None)
		return tree

	def resolveDiffTree(self, node):
		pass



###########################################
################### GUI ###################
###########################################

class ListControl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):

	def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, \
		size=wx.DefaultSize, style=0):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		listmix.ListCtrlAutoWidthMixin.__init__(self)



class ListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		# setup listctrl and columns
		self.list = self.list = ListControl(self, size=(-1,100), style=wx.LC_REPORT)
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
		self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
		self.list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.OnRightClick) # for wxMSW
		self.list.Bind(wx.EVT_RIGHT_UP, self.OnRightClick) # for wxGTK
		self.coldefs = \
			[ \
				('', 22), \
				('', 22), \
				('Name', 150), \
				('Size', 130), \
				('CTime', 142), \
				('ATime', 142), \
				('MTime', 142), \
				('Checksum', 80)
			]
		index = 0
		for coldef in self.coldefs:
			self.list.InsertColumn(index, coldef[0])
			self.list.SetColumnWidth(index, coldef[1])
			index = index + 1

		# for listmix.ListCtrlAutoWidthMixin, auto extend name column
		self.list.setResizeColumn(3)

		# start with empty node tree
		self.nodestack = []
		self.namestack = []

		# some constants
		self.__emptyNameString = '<empty>'
		self.__parentNameString = '..'

		# one pseudo boxer with the listctrl filling the whole panel
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

		# prepare image list
		self.imagelist = wx.ImageList(16, 16)
		self.iconError = self.imagelist.Add(IconError.GetBitmap())
		self.iconMissing = self.imagelist.Add(IconMissing.GetBitmap())
		self.iconNew = self.imagelist.Add(IconNew.GetBitmap())
		self.iconOk = self.imagelist.Add(IconOk.GetBitmap())
		self.iconUnknown = self.imagelist.Add(IconUnknown.GetBitmap())
		self.iconWarning = self.imagelist.Add(IconWarning.GetBitmap())
		self.list.SetImageList(self.imagelist, wx.IMAGE_LIST_SMALL)

	def AppendNode(self, node):
		# insert new line with icon
		if node.status is None or node.status == NodeStatus.Undefined:
			index = self.list.InsertStringItem(sys.maxint, '')
		elif node.status == NodeStatus.Unknown:
			index = self.list.InsertImageItem(sys.maxint, self.iconUnknown)
		elif node.status == NodeStatus.OK:
			index = self.list.InsertImageItem(sys.maxint, self.iconOk)
		elif node.status == NodeStatus.New:
			index = self.list.InsertImageItem(sys.maxint, self.iconNew)
		elif node.status == NodeStatus.Missing:
			index = self.list.InsertImageItem(sys.maxint, self.iconMissing)
		elif node.status == NodeStatus.Warn:
			index = self.list.InsertImageItem(sys.maxint, self.iconWarning)
		elif node.status == NodeStatus.Error:
			index = self.list.InsertImageItem(sys.maxint, self.iconError)
		else:
			raise Exception('Unknown node status {0:d}'.format(node.status))
		# fill in rest of information
		self.list.SetStringItem(index, 2, node.name)
		if node.isDirectory():
			self.list.SetStringItem(index, 1, '>')
		else:
			self.list.SetStringItem(index, 3, node.info.getSizeString())
			self.list.SetStringItem(index, 4, node.info.getCTimeString())
			self.list.SetStringItem(index, 5, node.info.getATimeString())
			self.list.SetStringItem(index, 6, node.info.getMTimeString())
			self.list.SetStringItem(index, 7, node.info.getChecksumString())
		# assign python id with entry
		self.list.SetItemData(index, node.pythonid)

	def IsRoot(self):
		return len(self.nodestack) <= 1

	def Clear(self):
		self.list.DeleteAllItems()

	def RefreshTree(self):
		# clear old contents
		self.Clear()
		if not self.IsRoot():
			# for directories other than root show entry to go back to parent
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, 2, self.__parentNameString)
		if len(self.nodestack) == 0:
			# for an empty list show a special string
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, 2, self.__emptyNameString)
		else:
			# otherwise just append all nodes
			for node in self.nodestack[-1]:
				self.AppendNode(node)
		# set address line
		path = reduce(lambda x, y: os.path.join(x, y), self.namestack)
		self.GetParent().SetAddressLine(path)

	def ShowNodeTree(self, nodetree):
		self.list.SetFocus()
		self.nodestack = []
		if len(nodetree[0].children) > 0:
			self.nodestack.append(nodetree[0].children)
		self.namestack = []
		self.namestack.append('')
		self.RefreshTree()

	def OnItemSelected(self, event):
		index = event.m_itemIndex
		namecol = self.list.GetItem(index, 2).GetText()
		# prevent user from selecting parent dir entry or empty name string
		if namecol == self.__parentNameString or namecol == self.__emptyNameString:
			self.list.SetItemState(index, 0, wx.LIST_STATE_SELECTED)
		event.Skip()

	def OnItemActivated(self, event):
		index = event.m_itemIndex
		namecol = self.list.GetItem(index, 2).GetText()
		# navigate to parent directory
		if namecol == self.__parentNameString:
			self.nodestack.pop()
			self.namestack.pop()
			self.RefreshTree()
			return
		pythonid = self.list.GetItemData(index)
		node = self.nodestack[-1].getByPythonID(pythonid)
		# navigate to child/sub directory
		if node.isDirectory():
			self.nodestack.append(node.children)
			self.namestack.append(node.name)
			self.RefreshTree()

	def OnRightClick(self, event):
		index = self.list.GetFirstSelected()
		if index == -1:
			event.Skip()
			return

		# only do this part the first time so the events are only bound once
		if not hasattr(self, "popupID1"):
			self.popupIdIgnore = wx.NewId()
			self.popupIdUpdateDB = wx.NewId()

			self.Bind(wx.EVT_MENU, self.OnPopupIgnore, id=self.popupIdIgnore)
			self.Bind(wx.EVT_MENU, self.OnPopupUpdateDB, id=self.popupIdUpdateDB)

			menu = wx.Menu()
			menu.Append(self.popupIdIgnore, "Ignore")
			menu.Append(self.popupIdUpdateDB, "Update DB")

			# Popup the menu.  If an item is selected then its handler
			# will be called before PopupMenu returns.
			self.PopupMenu(menu)
			menu.Destroy()

	def OnPopupIgnore(self, event):
		index = self.list.GetFirstSelected()
		while not index == -1:
			pythonid = self.list.GetItemData(index)
			self.nodestack[-1].delByPythonID(pythonid)
			index = self.list.GetNextSelected(index)
		self.RefreshTree()

	def OnPopupUpdateDB(self, event):
		index = self.list.GetFirstSelected()
		while not index == -1:
			pythonid = self.list.GetItemData(index)
			#node = self.nodestack[-1].getByPythonID(pythonid)
			#instance.resolveDiffTree(node)
			self.nodestack[-1].delByPythonID(pythonid)
			index = self.list.GetNextSelected(index)



class MainFrame(wx.Frame):
	def __init__(self, parent):
		self.baseTitle = ProgramName + ' ' + ProgramVersion
		wx.Frame.__init__(self, parent, title=self.baseTitle, size=(1024,300))

		# main menue definition
		fileMenu = wx.Menu()
		menuImport = fileMenu.Append(wx.ID_FILE1, 'Import', 'Import Directory')
		self.Bind(wx.EVT_MENU, self.OnImport, menuImport)
		menuCheck = fileMenu.Append(wx.ID_FILE2, 'Check', 'Check Directory')
		self.Bind(wx.EVT_MENU, self.OnCheck, menuCheck)
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
		self.list = ListControlPanel(self)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.address, 0, wx.ALL | wx.EXPAND, 5)
		sizer.Add(self.list, 1, wx.ALL | wx.EXPAND, 5)
		self.SetSizer(sizer)

		self.CreateStatusBar()

		self.Show(True)

	def SetAddressLine(self, path):
		self.address.SetValue(path)

	def OnImport(self, event):
		# get a valid path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for import:", \
			style=wx.DD_DEFAULT_STYLE)
		dirDialog.SetPath('../dtint-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			userPath = dirDialog.GetPath()
		else:
			return
		if Instance.isRootDir(userPath):
			dial = wx.MessageBox('Path "' + userPath + '" is already a valid root dir.\n\nDo you still want to continue?', \
				'Warning', wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT)
			if not dial == wx.YES:
				return
		self.Title = self.baseTitle + ' - ' + userPath

		# create and reset instance
		instance = Instance(userPath)
		instance.reset()
		instance.open()

		# create progress dialog
		progressDialog = FileProcessingProgressDialog(self, 'Importing ' + userPath)
		progressDialog.Show()
		stats = instance.getStatistics()
		progressDialog.Init(stats.getNodeCount(), stats.getNodeSize())

		# execute task
		try:
			instance.importTree(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
		except UserCancelledException:
			self.list.Clear()
			progressDialog.SignalFinished()
			return
		except MyException as e:
			progressDialog.Destroy()
			e.showDialog('Importing ' + userPath)
			return

		# signal that we have returned from calculation, either
		# after it is done or after progressDialog signalled that the
		# user stopped the calcuation using the cancel button
		progressDialog.SignalFinished()

		tree = instance.getDatabaseTree()
		tree.setStatus(NodeStatus.OK)
		self.list.ShowNodeTree(tree)

		instance.close()

	def OnCheck(self, event):
		# get a valid path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for check:", \
			style=wx.DD_DEFAULT_STYLE)
		dirDialog.SetPath('../dtint-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			userPath = dirDialog.GetPath()
		else:
			return
		if not Instance.isRootDir(userPath):
			wx.MessageBox('Path "' + userPath + '" is no valid root dir.', \
				'Error', wx.OK | wx.ICON_ERROR)
			return
		self.Title = self.baseTitle + ' - ' + userPath

		# create and reset instance
		instance = Instance(userPath)
		instance.open()

		# create progress dialog
		progressDialog = FileProcessingProgressDialog(self, 'Checking ' + userPath)
		progressDialog.Show()
		stats = instance.getStatistics()
		progressDialog.Init(stats.getNodeCount(), stats.getNodeSize())

		# execute task
		try:
			tree = instance.getDiffTree(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
		except UserCancelledException:
			self.list.Clear()
			progressDialog.SignalFinished()
			return
		except MyException as e:
			progressDialog.Destroy()
			e.showDialog('Checking ' + userPath)
			return

		# signal that we have returned from calculation, either
		# after it is done or after progressDialog signalled that the
		# user stopped the calcuation using the cancel button
		progressDialog.SignalFinished()

		self.list.ShowNodeTree(tree)

		instance.close()


	def OnExit(self, event):
		self.Close(True)

	def OnAbout(self, event):
		pass



if __name__ == '__main__':
	app = wx.App(False)
	frame = MainFrame(None)
	frame.Show()
	app.MainLoop()