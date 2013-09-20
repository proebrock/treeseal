#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import wx

from simplegrid import SimpleGrid
from simplelistctrl import SimpleListControl



class ContentListControlPanel(wx.Panel):

	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

		# setup listctrl and columns
		self.list = self.list = SimpleListControl(self)
		self.list.InitializeColumns([ \
				('Path', None), \
				('Where', 60), \
			])

		# one pseudo boxer with the listctrl filling the whole panel
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.list, 1, wx.EXPAND)
		self.SetSizer(sizer)



class NodeComparisonDialog(wx.Dialog):

	def __init__(self, parent, node, instance):

		height = 210 # node header
		if node.isFile():
			height += 190 # node info for files
			if instance.isQueryByChecksumPossible():
				if (node.otherinfo is not None) and \
					(not node.info.checksum == node.otherinfo.checksum):
					height += 400 # diff content view
				else:
					height += 200 # single content view

		wx.Dialog.__init__(self, parent, title='Node information', size=(560,height), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		self.border = 5

		# header information
		rowlabels = [ \
			'Name', \
			'IsDir', \
			'Database Key', \
			'Status', \
			]
		entries = [ \
			[node.getNameString()], \
			[node.getIsDirString()], \
			[node.getDbKeyString()], \
			[node.getStatusString()], \
			]
		headerGrid = SimpleGrid(self, entries, rowlabels)
		# static box with contents
		headerBox = wx.StaticBox(self, -1, 'General Information')
		headerBoxSizer = wx.StaticBoxSizer(headerBox, wx.VERTICAL)
		headerBoxSizer.Add(headerGrid, 1, wx.ALL | wx.EXPAND, self.border)

		if node.isFile():
			# static box with contents
			if node.otherinfo is not None:
				diffGrid = self.GetDiffGrid([node.otherinfo, node.info])
				diffBox = wx.StaticBox(self, -1, 'Differences')
			else:
				diffGrid = self.GetDiffGrid([node.info])
				diffBox = wx.StaticBox(self, -1, 'Details')
			diffBoxSizer = wx.StaticBoxSizer(diffBox, wx.VERTICAL)
			diffBoxSizer.Add(diffGrid, 0, wx.ALL | wx.EXPAND, self.border)

			if instance.isQueryByChecksumPossible():
				if (node.otherinfo is not None) and \
					(not node.info.checksum == node.otherinfo.checksum):
					contentBoxSizerOther = self.ContentBox(node.otherinfo.checksum, instance, 'Old content')
					contentBoxSizer = self.ContentBox(node.info.checksum, instance, 'New content')
				else:
					contentBoxSizerOther = None
					contentBoxSizer = self.ContentBox(node.info.checksum, instance)

		# button
		button = wx.Button(self, label='OK')
		button.SetFocus()
		self.Bind(wx.EVT_BUTTON, self.OnClick, button)

		# create and fill global sizer
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(headerBoxSizer, 0, wx.ALL | wx.EXPAND, self.border)
		if node.isFile():
			sizer.Add(diffBoxSizer, 0, wx.ALL | wx.EXPAND, self.border)
			if instance.isQueryByChecksumPossible():
				if (node.otherinfo is not None) and \
					(not node.info.checksum == node.otherinfo.checksum):
					sizer.Add(contentBoxSizerOther, 1, wx.ALL | wx.EXPAND, self.border)
					sizer.Add(contentBoxSizer, 1, wx.ALL | wx.EXPAND, self.border)
				else:
					sizer.Add(contentBoxSizer, 1, wx.ALL | wx.EXPAND, self.border)
		sizer.Add(button, 0, wx.ALL | wx.ALIGN_CENTER, self.border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

	def GetDiffGrid(self, infos):
		entries = []
		entries.append([ info.getSizeString(False) for info in infos ])
		entries.append([ info.getCTimeString(False) for info in infos ])
		entries.append([ info.getATimeString(False) for info in infos ])
		entries.append([ info.getMTimeString(False) for info in infos ])
		entries.append([ info.getChecksumString() for info in infos ])
		rowlabels = [ \
			'Size', \
			'Creation time', \
			'Access time', \
			'Modification time', \
			'Checksum', \
			]
		if len(infos) == 1:
			collabels = None
			markers = None
		else:
			collabels = ['Database', 'Filesystem']
			markers = []
			for i in range(len(entries)):
				if not entries[i][0] == entries[i][1]:
					markers.append([ 'Yellow', 'Yellow' ])
				else:
					markers.append([ None, None ])
		return SimpleGrid(self, entries, rowlabels, collabels, markers)

	def ContentBox(self, checksum, instance, comment=None):
		# showing number of instances
		[ dbpaths, fspaths ] = instance.getPathsByChecksum(checksum.getString())
		if dbpaths is None or fspaths is None:
			return None
		instancesGrid = SimpleGrid(self, \
			[ ['{0:d}'.format(len(dbpaths)), '{0:d}'.format(len(fspaths))] ], \
			['Number of occurrences'], ['Database', 'Filesystem'], \
			[ [ None,  'Red' if len(fspaths)==0 else None ] ])
		# show list control with list of files
		contentList = ContentListControlPanel(self)
		paths = sorted(list(dbpaths | fspaths))
		for path in paths:
			index = contentList.list.InsertStringItem(sys.maxint, path)
			if path in dbpaths:
				if path in fspaths:
					wherestr = 'both'
				else:
					wherestr = 'db'
			elif path in fspaths:
				wherestr = 'fs'
			contentList.list.SetStringItem(index, 1, wherestr)
		# static box with contents
		boxlabel = 'File content \'' + checksum.getString(True) + '\''
		if comment is not None:
			boxlabel += ' (' + comment + ')'
		contentBox = wx.StaticBox(self, -1, boxlabel)
		contentBoxSizer = wx.StaticBoxSizer(contentBox, wx.VERTICAL)
		contentBoxSizer.Add(instancesGrid, 0, wx.ALL | wx.EXPAND, self.border)
		contentBoxSizer.Add(contentList, 1, wx.ALL | wx.EXPAND, self.border)
		return contentBoxSizer

	def OnClick(self, event):
		self.Destroy()
