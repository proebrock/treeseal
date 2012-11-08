#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
import wx.lib.mixins.listctrl as listmix



class SimpleListControl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):

	def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, \
		size=wx.DefaultSize, style=wx.LC_REPORT):
		wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
		listmix.ListCtrlAutoWidthMixin.__init__(self)

	def InitializeColumns(self, columndefs):
		# initialize columns and their sizes
		index = 0
		for coldef in columndefs:
			self.InsertColumn(index, coldef[0])
			if coldef[1] is None:
				# for listmix.ListCtrlAutoWidthMixin, auto extend name column
				self.SetColumnWidth(index, 100)
				self.setResizeColumn(index + 1)
			else:
				self.SetColumnWidth(index, coldef[1])
			index = index + 1