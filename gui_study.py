#!/usr/bin/env python


import wx


class MainWindow(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent, title='dtint', size=(800,600))
		self.Show(True)
		
app = wx.App(False)
frame = MainWindow(None)
app.MainLoop()
