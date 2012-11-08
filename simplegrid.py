#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx



class SimpleGrid(wx.FlexGridSizer):

	def __init__(self, parent, entries, rowlabels=None, collabels=None, colors=None):
		numRows = len(entries)
		if rowlabels is None:
			haveRowLabels = 0
		else:
			haveRowLabels = 1
			if not len(rowlabels) == numRows:
				raise Exception('Number of row labels ({0:d}) must match number of rows ({1:d}).'.format(len(rowlabels), numRows))
		numCols = len(entries[0])
		if collabels is None:
			haveColLabels = 0
		else:
			haveColLabels = 1
			if not len(collabels) == numCols:
				raise Exception('Number of column labels ({0:d}) must match number of columns ({1:d}).'.format(len(collabels), numCols))

		self.border = 5

		wx.FlexGridSizer.__init__(self, numRows + haveColLabels, numCols + haveRowLabels, self.border, self.border)

		firstColAlign = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT
		otherColAlign = wx.EXPAND

		# if we have row and column labels, we need an empty element in top left corner
		if (rowlabels is not None) and (collabels is not None):
			self.Add(wx.StaticText(parent, label=''), 0, firstColAlign, self.border)
		# if we have column labels, print a row of column labels
		if collabels is not None:
			for l in collabels:
				self.Add(wx.StaticText(parent, label=l), 0, otherColAlign, self.border)
		for i in range(numRows):
			# if we have row labels, print label of current row first
			if rowlabels is not None:
				self.Add(wx.StaticText(parent, label=rowlabels[i]), 0, firstColAlign, self.border)
			# print entries itself
			for j in range(numCols):
				entry = wx.TextCtrl(parent, -1, entries[i][j], style=wx.TE_READONLY)
				if colors is not None:
					if colors[i][j] is not None:
						entry.SetBackgroundColour(colors[i][j])
				self.Add(entry, 0, otherColAlign, self.border)

		# make all columns growable (except first one if we have row labels)
		for i in range(haveRowLabels, haveRowLabels + numCols):
			self.AddGrowableCol(i)
