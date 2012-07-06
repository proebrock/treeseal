#!/usr/bin/env python


import wx


class MainWindow(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, title='dtint', size=(800,600))
		
		self.CreateStatusBar()
		
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
		
		self.Show(True)
		
	def OnExit(self, e):
		self.Close(True)
		
app = wx.App(False)
frame = MainWindow(None)
app.MainLoop()
