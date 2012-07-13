#!/usr/bin/env python


import wx


class MainWindow(wx.Frame):
	"""
	Constructor of MainWindow
	"""
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, title='dtint', size=(800,600))
		
		# main menue definition
		fileMenu = wx.Menu()
		#fileMenu.AppendSeparator()
		menuExit = fileMenu.Append(wx.ID_EXIT, 'E&xit', 'Terminate Program')
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		helpMenu = wx.Menu()
		menuAbout = helpMenu.Append(wx.ID_ABOUT, 'About', 'Information about this program')
		# assemble menu
		menuBar = wx.MenuBar()
		menuBar.Append(fileMenu, '&File')
		menuBar.Append(helpMenu, 'Help')
		self.SetMenuBar(menuBar)

		# main window consists of address line and directory listing
		self.address = wx.TextCtrl(self, -1, style=wx.TE_READONLY)
		self.address.SetValue('/home/phil/Data');
		self.list = wx.ListCtrl(self, style=wx.LC_REPORT)
		self.list.InsertColumn(0, 'Status')
		self.list.InsertColumn(1, 'Name')
		self.list.InsertColumn(2, 'IsDir')
		self.list.InsertColumn(3, 'Size')
		self.list.InsertColumn(4, 'CTime')
		self.list.InsertColumn(5, 'ATime')
		self.list.InsertColumn(6, 'MTime')
		self.list.InsertColumn(7, 'Checksum')

		self.list.InsertStringItem(0, 'OK')
		self.list.SetStringItem(0, 1, 'result.m')
		self.list.SetStringItem(0, 2, 'False')
		self.list.SetStringItem(0, 3, '23KB')
		self.list.SetStringItem(0, 4, '2012-05-06 10:23:11')
		self.list.SetStringItem(0, 5, '2012-05-06 10:23:12')
		self.list.SetStringItem(0, 6, '2012-05-06 10:23:13')
		self.list.SetStringItem(0, 7, '7c6a6523ac1238a9...')
		
		box = wx.BoxSizer(wx.VERTICAL)
		box.Add(self.address, 0, wx.EXPAND)
		box.AddSpacer((5,0))
		box.Add(self.list, 1, wx.EXPAND)
		self.SetSizer(box)
		
		self.CreateStatusBar()
		
		self.Show(True)

	"""
	Executed on program exit
	"""
	def OnExit(self, e):
		self.Close(True)
		
app = wx.App(False)
frame = MainWindow(None)
app.MainLoop()
