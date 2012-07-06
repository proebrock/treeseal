#!/usr/bin/env python


import wx


class MainWindow(wx.Frame):
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
		self.listing = wx.TextCtrl(self, -1, 'Listbox (TODO)', style=wx.TE_READONLY)
		
		box = wx.BoxSizer(wx.VERTICAL)
		box.Add(self.address, 0, wx.EXPAND)
		box.AddSpacer((5,0))
		box.Add(self.listing, 1, wx.EXPAND)
		self.SetSizer(box)
		
		self.CreateStatusBar()
		
		self.Show(True)
		
	def OnExit(self, e):
		self.Close(True)
		
app = wx.App(False)
frame = MainWindow(None)
app.MainLoop()
