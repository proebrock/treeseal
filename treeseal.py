#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
import sys
import wx

from comparisondialog import NodeComparisonDialog
from dbtree import DatabaseTree
from fstree import FilesystemTree
import icons as Icons
from instance import Instance
from memtree import MemoryTree
from misc import Checksum, MyException
from node import Node, NodeStatus
from progressdialog import UserCancelledException, FileProcessingProgressDialog
from simplelistctrl import SimpleListControl

ProgramName = 'treeseal'
ProgramVersion = '3.0'



class UserConfig(object):

	def __init__(self):
		pass


###########################################
################### GUI ###################
###########################################

class StatusImageList(wx.ImageList):

	def __init__(self):
		# initialize base class
		wx.ImageList.__init__(self, 16, 16)
		# init mapping: node status -> icon list index
		self.__statusToIndex = {}
		# dir and file
		self.__statusToIndex[NodeStatus.Undefined] = self.Add(Icons.Undefined.GetBitmap())
		self.__statusToIndex[NodeStatus.New] = self.Add(Icons.New.GetBitmap())
		self.__statusToIndex[NodeStatus.Missing] = self.Add(Icons.Missing.GetBitmap())
		self.__statusToIndex[NodeStatus.Ok] = self.Add(Icons.Ok.GetBitmap())
		# file only
		self.__statusToIndex[NodeStatus.FileWarning] = self.Add(Icons.FileWarning.GetBitmap())
		self.__statusToIndex[NodeStatus.FileError] = self.Add(Icons.FileError.GetBitmap())
		# dir ony
		self.__statusToIndex[NodeStatus.DirContainsNew] = self.Add(Icons.DirContainsNew.GetBitmap())
		self.__statusToIndex[NodeStatus.DirContainsMissing] = self.Add(Icons.DirContainsMissing.GetBitmap())
		self.__statusToIndex[NodeStatus.DirContainsWarning] = self.Add(Icons.DirContainsWarning.GetBitmap())
		self.__statusToIndex[NodeStatus.DirContainsError] = self.Add(Icons.DirContainsError.GetBitmap())
		self.__statusToIndex[NodeStatus.DirContainsMulti] = self.Add(Icons.DirContainsMulti.GetBitmap())

	def GetIndexByStatus(self, status):
		if not status in self.__statusToIndex:
			raise MyException('Unknown node status {0:s}'.format(NodeStatus.toString(status), 3))
		else:
			return self.__statusToIndex[status]



class ListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		# setup listctrl and columns
		self.list = SimpleListControl(self)
		self.list.InitializeColumns([ \
				('', 22), \
				('', 22), \
				('', 22), \
				('Name', None), \
				('Size', 130), \
				('Modfication Time', 142), \
				('Checksum', 80), \
			])
		self.statusColumn = 0
		self.trashColumn = 1
		self.dirMarkerColumn = 2
		self.nameColumn = 3
		self.sizeColumn = 4
		self.mtimeColumn = 5
		self.csumColumn = 6

		# one pseudo boxer with the listctrl filling the whole panel
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.list, self.nameColumn-1, wx.EXPAND)
		self.SetSizer(sizer)

		# bind controls
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
		self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
		self.list.Bind(wx.EVT_COMMAND_RIGHT_CLICK, self.OnRightClick) # for wxMSW
		self.list.Bind(wx.EVT_RIGHT_UP, self.OnRightClick) # for wxGTK

		self.instance = None
		self.readonly = True

		# some constants
		self.__emptyNameString = '<empty>'
		self.__parentNameString = '..'
		self.__dirMarkerString = '>'

		# prepare image list
		self.__imagelist = StatusImageList()
		self.trashIconIndex = self.__imagelist.Add(Icons.Trash.GetBitmap())
		self.list.SetImageList(self.__imagelist, wx.IMAGE_LIST_SMALL)

	def AppendNode(self, node):
		# insert new line with icon
		index = self.list.InsertImageItem(sys.maxint, self.__imagelist.GetIndexByStatus(node.status))
		# fill in rest of information
		self.list.SetStringItem(index, self.nameColumn, node.name)
		if node.isDirectory():
			self.list.SetStringItem(index, self.dirMarkerColumn, self.__dirMarkerString)
		else:
			dol = self.instance.hasDangerOfLoss(node)
			if dol is not None and dol == True:
				self.list.SetItemColumnImage(index, self.trashColumn, self.trashIconIndex)
			self.list.SetStringItem(index, self.sizeColumn, node.info.getSizeString())
			self.list.SetStringItem(index, self.mtimeColumn, node.info.getMTimeString())
			self.list.SetStringItem(index, self.csumColumn, node.info.getChecksumString())

	def IndexToName(self, index):
		return self.list.GetItem(index, self.nameColumn).GetText()

	def IndexToNid(self, index):
		name = self.list.GetItem(index, self.nameColumn).GetText()
		isdir = self.list.GetItem(index, self.dirMarkerColumn).GetText() == self.__dirMarkerString
		return Node.constructNid(name, isdir)

	def getSelectedNodeNids(self):
		index = self.list.GetFirstSelected()
		if index == -1:
			# no listctrl entries selected
			return []
		result = []
		while not index == -1:
			nid = self.IndexToNid(index)
			result.append(nid)
			index = self.list.GetNextSelected(index)
		return result

	def RefreshTree(self):
		# clear old contents
		self.Clear()
		if not self.instance.isRoot():
			# for directories other than root show entry to go back to parent
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, self.nameColumn, self.__parentNameString)
		for node in self.instance:
			self.AppendNode(node)
		if self.list.GetItemCount() == 0:
			# for an empty list show a special string
			index = self.list.InsertStringItem(sys.maxint, '')
			self.list.SetStringItem(index, self.nameColumn, self.__emptyNameString)
		# set address line
		self.GetParent().SetAddressLine(self.instance.getPath())

	def Clear(self):
		self.list.DeleteAllItems()

	def ClearInstance(self):
		if self.instance is not None:
			self.instance.close()
			self.instance = None

	def SetInstance(self, instance):
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
		name = self.IndexToName(index)
		# navigate to parent directory
		if name == self.__parentNameString:
			self.instance.up()
			self.RefreshTree()
			return
		nid = self.IndexToNid(index)
		node = self.instance.getNodeByNid(nid)
		# navigate to child/sub directory
		if node.isDirectory():
			self.instance.down(node)
			self.RefreshTree()
		# show comparison dialog
		else:
			comparisonDialog = NodeComparisonDialog(self, node, self.instance)
			comparisonDialog.Show()

	def OnRightClick(self, event):
		nids = self.getSelectedNodeNids()
		if len(nids) == 0:
			event.Skip()
			return

		# only do this part the first time so the events are only bound once
		if not hasattr(self, "popupID1"):
			menu = wx.Menu()

			if len(nids) == 1:
				if self.instance.getNodeByNid(nids[0]).isDirectory():
					self.popupIdChangeTo = wx.NewId()
					self.Bind(wx.EVT_MENU, self.OnPopupChangeTo, id=self.popupIdChangeTo)
					menu.Append(self.popupIdChangeTo, "Change to")

				self.popupIdInfo = wx.NewId()
				self.Bind(wx.EVT_MENU, self.OnPopupInfo, id=self.popupIdInfo)
				menu.Append(self.popupIdInfo, "Info")

			if len(nids) == 1 and not self.readonly:
				menu.AppendSeparator()

			if not self.readonly:
				self.popupIdIgnore = wx.NewId()
				self.Bind(wx.EVT_MENU, self.OnPopupIgnore, id=self.popupIdIgnore)
				menu.Append(self.popupIdIgnore, "Ignore")

				self.popupIdAccept = wx.NewId()
				self.Bind(wx.EVT_MENU, self.OnPopupAccept, id=self.popupIdAccept)
				menu.Append(self.popupIdAccept, "Accept")

				self.popupIdDelete = wx.NewId()
				self.Bind(wx.EVT_MENU, self.OnPopupDelete, id=self.popupIdDelete)
				menu.Append(self.popupIdDelete, "Delete")

			# Popup the menu.  If an item is selected then its handler
			# will be called before PopupMenu returns.
			self.PopupMenu(menu)
			menu.Destroy()

	def OnPopupChangeTo(self, event):
		nids = self.getSelectedNodeNids()
		if len(nids) != 1:
			raise MyException('Operation only possible for single selection.', 3)
		node = self.instance.getNodeByNid(nids[0])
		if not node.isDirectory():
			raise MyException('Cannot change to file.', 3)
		self.instance.down(node)
		self.RefreshTree()

	def OnPopupInfo(self, event):
		nids = self.getSelectedNodeNids()
		if len(nids) != 1:
			raise MyException('Operation only possible for single selection.', 3)
		node = self.instance.getNodeByNid(nids[0])
		comparisonDialog = NodeComparisonDialog(self, node, self.instance)
		comparisonDialog.Show()

	def OnPopupIgnore(self, event):
		nids = self.getSelectedNodeNids()
		self.instance.ignore(nids)
		self.RefreshTree()
		self.GetParent().SetStatusBarText('Ignored {0:d} entries'.format(len(nids)))

	def OnPopupAccept(self, event):
		nids = self.getSelectedNodeNids()
		self.instance.fix(nids)
		self.RefreshTree()
		self.GetParent().SetStatusBarText('Accepted {0:d} entries'.format(len(nids)))

	def OnPopupDelete(self, event):
		nids = self.getSelectedNodeNids()
		dial = wx.MessageBox('You are about to recursively delete {0:d} entries from this directory.\n\nDo you still want to continue?'.format(len(nids)), \
			'Warning', wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT)
		if not dial == wx.YES:
			return
		self.instance.delete(nids)
		self.RefreshTree()
		self.GetParent().SetStatusBarText('Deleted {0:d} entries'.format(len(nids)))



class MainFrame(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, size=(800,600))
		self.SetWindowTitle()

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

		self.config = UserConfig()

		self.statusbar = self.CreateStatusBar()
		self.statusbar.SetFieldsCount(1)

		self.Show(True)

	def SetWindowTitle(self, text=''):
		baseTitle = ProgramName + ' ' + ProgramVersion
		if text == '':
			self.Title = baseTitle
		else:
			self.Title = baseTitle + ' - ' + text

	def SetAddressLine(self, path=''):
		self.address.SetValue(path)

	def SetStatusBarText(self, text=''):
		self.statusbar.SetStatusText(text)

	def OnImport(self, event):
		# get a valid path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for import:", \
			style=wx.DD_DEFAULT_STYLE)
		#dirDialog.SetPath('D:\\Projects\\treeseal-example') # TESTING
		dirDialog.SetPath('/home/phil/Projects/treeseal-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			rootdir = dirDialog.GetPath()
			metadir = os.path.join(rootdir, '.' + ProgramName)
			dbfile = os.path.join(metadir, 'base.sqlite3')
			sigfile = os.path.join(metadir, 'base.signature')
		else:
			return
		# check pre-conditions
		if os.path.exists(metadir):
			dial = wx.MessageBox('Path "' + rootdir + '" is already a valid root dir.\n\nDo you still want to continue?', \
				'Warning', wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT)
			if not dial == wx.YES:
				return

		# close eventually existing previous instance
		self.list.ClearInstance()
		self.SetWindowTitle()
		self.SetStatusBarText()

		# do not care about previous content: reset meta directory and database files
		if os.path.exists(metadir):
			if os.path.exists(dbfile):
				os.remove(dbfile)
			if os.path.exists(sigfile):
				os.remove(sigfile)
		else:
			os.mkdir(metadir)
			if platform.system() == 'Windows':
				# if on windows platform, hide directory
				os.system('attrib +h "' + metadir + '"')

		try:
			# create trees
			fstree = FilesystemTree(rootdir, metadir)
			fstree.open()
			dbtree = DatabaseTree(dbfile, sigfile)
			dbtree.open()
		except MyException as e:
			e.showDialog('Importing ' + rootdir)
			return

		try:
			# create progress dialog
			progressDialog = FileProcessingProgressDialog(self, 'Importing ' + rootdir)
			progressDialog.Show()
			stats = fstree.getNodeStatistics()
			progressDialog.Init(stats.getNodeCount(), stats.getNodeSize())

			# execute task
			fstree.registerHandlers(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
			fstree.copyTo(dbtree)
			dbtree.commit()
			fstree.unRegisterHandlers()
		except UserCancelledException:
			progressDialog.SignalFinished()
			return
		except MyException as e:
			progressDialog.Destroy()
			e.showDialog('Importing ' + rootdir)
			return

		# signal that we have returned from calculation, either
		# after it is done or after progressDialog signalled that the
		# user stopped the calcuation using the cancel button
		progressDialog.SignalFinished()

		self.list.SetInstance(Instance(self.config, dbtree, None, None))
		fstree.close()
		self.list.readonly = True

		self.SetWindowTitle(rootdir)
		self.SetStatusBarText('Imported ' + str(stats))

	def OnCheck(self, event):
		# get a valid path from user
		dirDialog = wx.DirDialog(self, "Choose a directory for check:", \
			style=wx.DD_DEFAULT_STYLE)
		#dirDialog.SetPath('D:\\Projects\\treeseal-example') # TESTING
		dirDialog.SetPath('/home/phil/Projects/treeseal-example') # TESTING
		if dirDialog.ShowModal() == wx.ID_OK:
			rootdir = dirDialog.GetPath()
			metadir = os.path.join(rootdir, '.' + ProgramName)
			dbfile = os.path.join(metadir, 'base.sqlite3')
			sigfile = os.path.join(metadir, 'base.signature')
		else:
			return
		# check pre-conditions
		if not os.path.exists(metadir):
			wx.MessageBox('Path "' + rootdir + '" is no valid root dir.', \
				'Error', wx.OK | wx.ICON_ERROR)
			return

		# close eventually existing previous instance
		self.list.ClearInstance()
		self.SetWindowTitle()
		self.SetStatusBarText()

		# check more pre-conditions
		if not os.path.exists(dbfile):
			wx.MessageBox('Cannot find database file "' + dbfile + '".', \
				'Error', wx.OK | wx.ICON_ERROR)
			return
		if not os.path.exists(dbfile):
			wx.MessageBox('Cannot find database file "' + dbfile + '".', \
				'Error', wx.OK | wx.ICON_ERROR)
			return
		if not os.path.exists(sigfile):
			dial = wx.MessageBox('Cannot find database signature file "' + sigfile + '".\n\nUse database without verification?', \
				'Warning', wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT)
			if not dial == wx.YES:
				return
		else:
			cs = Checksum()
			cs.calculateForFile(dbfile)
			if not cs.isValidUsingSavedFile(sigfile):
				dial = wx.MessageBox('Database or database signature file have been corrupted.\n\nUse database without verification?', \
					'Warning', wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT)
				if not dial == wx.YES:
					return

		try:
			# create trees
			fstree = FilesystemTree(rootdir, metadir)
			fstree.open()
			dbtree = DatabaseTree(dbfile, sigfile)
			dbtree.open()
			memtree = MemoryTree()
			memtree.open()
		except MyException as e:
			e.showDialog('Checking ' + rootdir)
			return

		try:
			# create progress dialog
			progressDialog = FileProcessingProgressDialog(self, 'Checking ' + rootdir)
			progressDialog.Show()
			stats = fstree.getNodeStatistics()
			progressDialog.Init(stats.getNodeCount(), stats.getNodeSize())

			# execute task
			fstree.registerHandlers(progressDialog.SignalNewFile, \
				progressDialog.SignalBytesDone)
			fstree.diff(dbtree, memtree)
			memtree.commit()
			fstree.unRegisterHandlers()
		except UserCancelledException:
			progressDialog.SignalFinished()
			return
		except MyException as e:
			progressDialog.Destroy()
			e.showDialog('Checking ' + rootdir)
			return

		# signal that we have returned from calculation, either
		# after it is done or after progressDialog signalled that the
		# user stopped the calcuation using the cancel button
		progressDialog.SignalFinished()

		self.list.SetInstance(Instance(self.config, memtree, dbtree, fstree))
		self.list.readonly = False

		self.SetWindowTitle(rootdir)
		self.SetStatusBarText('Checked ' + str(stats))

	def OnExit(self, event):
		self.Close(True)

	def OnAbout(self, event):
		pass



if __name__ == '__main__':
	app = wx.App(False)
	frame = MainFrame(None)
	frame.Show()
	app.MainLoop()