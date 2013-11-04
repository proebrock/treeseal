#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import  wx.gizmos as gizmos

from preferences import Preferences



class PreferencesDialog(wx.Dialog):

	def __init__(self, parent, preferences):

		wx.Dialog.__init__(self, parent, title='Preferences', size=(400,500), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		self.preferences = preferences

		border = 5

		includeBox = wx.StaticBox(self, -1, 'Include')
		includeSizer = wx.StaticBoxSizer(includeBox, wx.VERTICAL)
		self.includeElb = gizmos.EditableListBox(self, -1, 'Files')
		includeSizer.Add(self.includeElb, 1, wx.EXPAND|wx.ALL, border)

		excludeBox = wx.StaticBox(self, -1, 'Exclude')
		excludeSizer = wx.StaticBoxSizer(excludeBox, wx.VERTICAL)
		self.excludeElb = gizmos.EditableListBox(self, -1, 'Files and Dirs')
		excludeSizer.Add(self.excludeElb, 1, wx.EXPAND|wx.ALL, border)

		# buttons
		okButton = wx.Button(self, label='OK')
		self.Bind(wx.EVT_BUTTON, self.OkClick, okButton)
		cancelButton = wx.Button(self, label='Cancel')
		self.Bind(wx.EVT_BUTTON, self.CancelClick, cancelButton)
		cancelButton.SetFocus()
		buttonsSizer = wx.BoxSizer(wx.HORIZONTAL)
		buttonsSizer.Add(okButton, 0, wx.ALL | wx.ALIGN_CENTRE, border)
		buttonsSizer.Add(cancelButton, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		# create and fill global sizer
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(includeSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(excludeSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(buttonsSizer, 0, wx.ALL | wx.ALIGN_CENTER, border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

		self.SetPreferences()

	def SetPreferences(self):
		if self.preferences is not None:
			if self.preferences.includes is not None:
				self.excludeElb.SetStrings(self.preferences.includes)
			if self.preferences.excludes is not None:
				self.excludeElb.SetStrings(self.preferences.excludes)

	def OkClick(self, event):
		self.Destroy()

	def CancelClick(self, event):
		self.Destroy()