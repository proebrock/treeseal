#!/usr/bin/env python

import os
import sys
import wx

from dbtree import DatabaseTree
from fstree import FilesystemTree
from icons import IconError, IconMissing, IconNew, IconOk, IconUnknown, IconWarning
from memtree import MemoryTree
from misc import MyException
from node import NodeStatus
from progressdialog import UserCancelledException, FileProcessingProgressDialog
from comparisondialog import NodeComparisonDialog
from simplelistctrl import SimpleListControl

ProgramName = 'dtint'
ProgramVersion = '3.0'



class Instance:

	def __init__(self, view, old, new):
		self.__view = view
		self.__old = old
		self.__new = new

	def __str__(self):
		result = '('
		result += '<view> depth={0:d} path=\'{1:s}\'' \
			.format(self.__view.getDepth(), self.__view.getPath())
		if self.__old is not None:
			result += ', <old> depth={0:d} path=\'{1:s}\'' \
				.format(self.__old.getDepth(), self.__old.getPath())
		if self.__new is not None:
			result += ', <new> depth={0:d} path=\'{1:s}\'' \
				.format(self.__new.getDepth(), self.__new.getPath())
		return result + ')'

	def isRoot(self):
		return self.__view.isRoot()

	def getDepth(self):
		return self.__view.getDepth()

	def getPath(self):
		return self.__view.getPath()

	def getStatistics(self):
		return self.__view.getStatistics()

	def up(self):
		if self.__old is not None:
			if self.__old.getDepth() == self.__view.getDepth():
				self.__old.up()
		if self.__new is not None:
			if self.__new.getDepth() == self.__view.getDepth():
				self.__new.up()
		self.__view.up()

	def down(self, node):
		self.__view.down(node)
		if self.__old is not None:
			if not node.status == NodeStatus.New:
				self.__old.down(self.__old.getNodeByName(node.name))
		if self.__new is not None:
			if not node.status == NodeStatus.Missing:
				self.__new.down(self.__new.getNodeByName(node.name))

	def getNodeByName(self, name):
		return self.__view.getNodeByName(name)

	def __iter__(self):
		for node in self.__view:
			yield node

	def ignore(self, nodes):
		pass

	def accept(self, nodes):
		pass

#	def sync(self, nodes):
#		nodelists = nodes.splitByStatus()
#		for i in range(NodeStatus.NumStatuses):
#			if len(nodelists[i]) == 0 or i == NodeStatus.OK:
#				continue
#			elif i == NodeStatus.New:
#				nodelists[i].deviceInsert(self.__db)
#			elif i == NodeStatus.Missing:
#				nodelists[i].deviceDelete(self.__db)
#			elif i == NodeStatus.Warn or i == NodeStatus.Error:
#				nodelists[i].deviceUpdate(self.__db)
#			else:
#				raise Exception('Unable to update database for node container with {0:d} entries and status {1:s}'.format( \
#					len(nodelists[i]), NodeStatus.toString(i)))



###########################################
################### GUI ###################
###########################################

class ListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		# setup listctrl and columns
		self.list = SimpleListControl(self)
		self.list.InitializeColumns([ \
				('', 22), \
				('', 22), \
				('Name', None), \
				('Size', 130), \
				('CTime', 142), \
				('ATime', 142), \
				('MTime', 142), \
				('Checksum', 80), \
			])

		# one pseudo boxer with the listctrl filling the whole panel
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.list, 1, wx.EXPAND)
		self.SetSizer(sizer)

		# bind controls
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
		self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
		self.list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.OnRightClick) # for wxMSW
		self.list.Bind(wx.EVT_RIGHT_UP, self.OnRightClick) # for wxGTK

		self.instance = None

		# some constants
		self.__emptyNameString = '<empty>'
		self.__parentNameString = '..'

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

	def IndexToName(self, index):
		return self.list.GetItem(index, 2).GetText()

	def getSelectedNodeNames(self):
		result = []
		index = self.list.GetFirstSelected()
		while not index == -1:
			name = self.IndexToName(index)
			result.append(name)
			index = self.list.GetNextSelected(index)
		return result

	def RefreshTree(self):
		# clear old contents
		self.Clear()
		if not self.instance.isRoot():
			# for directories other than root show entry to go back to parent
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, 2, self.__parentNameString)
		for node in self.instance:
			self.AppendNode(node)
		if self.list.GetItemCount() == 0:
			# for an empty list show a special string
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, 2, self.__emptyNameString)
		# set address line
		self.GetParent().SetAddressLine(self.instance.getPath())

	def Clear(self):
		self.list.DeleteAllItems()

	def ClearInstance(self):
		self.instance = None

	def ShowNodeTree(self, instance):
		self.list.SetFocus()
		self.instance = instance
		self.RefreshTree()

	def OnItemSelected(self, event):
		index = event.m_itemIndex
		name = self.IndexToName(index)
		# prevent user from selecting parent dir entry or empty name string
		if name == self.__parentNameString or name == self.__emptyNameString:
			self.list.SetItemState(index, 0, wx.LIST_STATE_SELECTED)
		event.Skip()

	def OnItemActivated(self, event):
		index = event.m_itemIndex
		name = self.list.GetItem(index, 2).GetText()
		# navigate to parent directory
		if name == self.__parentNameString:
			self.instance.up()
			self.RefreshTree()
			return
		node = self.instance.getNodeByName(name)
		# navigate to child/sub directory
		if node.isDirectory():
			self.instance.down(node)
			self.RefreshTree()
		# show comparison dialog
		else:
			comparisonDialog = NodeComparisonDialog(self, node, self.instance)
			comparisonDialog.Show()

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
		name = self.getSelectedNodeNames()
		#for node in nodes:
		#	self.nodestack[-1].delByPythonID(node.pythonid)
		self.RefreshTree()

	def OnPopupUpdateDB(self, event):
		names = self.getSelectedNodeNames()
		#self.instance.updateDB(nodes)
		#for node in nodes:
		#	self.nodestack[-1].delByPythonID(node.pythonid)
		self.RefreshTree()



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
		#dirDialog.SetPath('D:\\Projects\\dtint-example') # TESTING
		dirDialog.SetPath('/home/phil/Projects/dtint-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			userPath = dirDialog.GetPath()
		else:
			return
		if os.path.exists(os.path.join(userPath, '.dtint')):
			dial = wx.MessageBox('Path "' + userPath + '" is already a valid root dir.\n\nDo you still want to continue?', \
				'Warning', wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT)
			if not dial == wx.YES:
				return
		self.Title = self.baseTitle + ' - ' + userPath

		# create trees
		fstree = FilesystemTree(userPath)
		fstree.reset()
		dbtree = DatabaseTree(userPath)
		dbtree.reset()

		# create progress dialog
		progressDialog = FileProcessingProgressDialog(self, 'Importing ' + userPath)
		progressDialog.Show()
		stats = fstree.getStatistics()
		progressDialog.Init(stats.getNodeCount(), stats.getNodeSize())

		# execute task
		try:
			fstree.registerHandlers(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
			fstree.copyTo(dbtree)
			dbtree.commit()
			fstree.unRegisterHandlers()
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

		self.list.ClearInstance()
		self.list.ShowNodeTree(Instance(dbtree, None, None))

	def OnCheck(self, event):
		# get a valid path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for check:", \
			style=wx.DD_DEFAULT_STYLE)
		#dirDialog.SetPath('D:\\Projects\\dtint-example') # TESTING
		dirDialog.SetPath('/home/phil/Projects/dtint-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			userPath = dirDialog.GetPath()
		else:
			return
		if not os.path.exists(os.path.join(userPath, '.dtint')):
			wx.MessageBox('Path "' + userPath + '" is no valid root dir.', \
				'Error', wx.OK | wx.ICON_ERROR)
			return
		self.Title = self.baseTitle + ' - ' + userPath

		# create trees
		fstree = FilesystemTree(userPath)
		dbtree = DatabaseTree(userPath)
		memtree = MemoryTree()

		# create progress dialog
		progressDialog = FileProcessingProgressDialog(self, 'Checking ' + userPath)
		progressDialog.Show()
		stats = fstree.getStatistics()
		progressDialog.Init(stats.getNodeCount(), stats.getNodeSize())

		# execute task
		try:
			fstree.registerHandlers(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
			dbtree.compare(fstree, memtree)
			fstree.unRegisterHandlers()
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

		self.list.ClearInstance()
		self.list.ShowNodeTree(Instance(memtree, dbtree, fstree))

	def OnExit(self, event):
		self.Close(True)

	def OnAbout(self, event):
		pass



if __name__ == '__main__':
	app = wx.App(False)
	frame = MainFrame(None)
	frame.Show()
	app.MainLoop()