import wx



class SimpleGrid(wx.FlexGridSizer):

	def __init__(self, parent, rowlabels, collabels, entries):
		numRows = len(entries)
		if rowlabels is None:
			haveRowLabels = 0
		else:
			haveRowLabels = 1
			if not len(rowlabels) == numRows:
				raise Exception('Number of row labels must match number of rows.')
		numCols = len(entries[0])
		if collabels is None:
			haveColLabels = 0
		else:
			haveColLabels = 1
			if not len(collabels) == numCols:
				raise Exception('Number of column labels must match number of columns.')

		border = 5

		wx.FlexGridSizer.__init__(self, numRows + haveColLabels, numCols + haveRowLabels, border, border)

		firstColAlign = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT
		otherColAlign = wx.EXPAND

		# if we have row and column labels, we need an empty element in top left corner
		if (rowlabels is not None) and (collabels is not None):
			self.Add(wx.StaticText(parent, label=''), 0, firstColAlign, border)
		# if we have column labels, print a row of column labels
		if collabels is not None:
			for l in collabels:
				self.Add(wx.StaticText(parent, label=l), 0, otherColAlign, border)
		for i in range(numRows):
			# if we have row labels, print label of current row first
			if rowlabels is not None:
				self.Add(wx.StaticText(parent, label=rowlabels[i]), 0, firstColAlign, border)
			# print entries itself
			for j in range(numCols):
				self.Add(wx.TextCtrl(parent, -1, entries[i][j], style=wx.TE_READONLY), 0, otherColAlign, border)

		# make all columns growable (except first one if we have row labels)
		for i in range(haveRowLabels, haveRowLabels + numCols):
			self.AddGrowableCol(i)



class NodeComparisonDialog(wx.Dialog):

	def __init__(self, parent, node):
		wx.Dialog.__init__(self, parent, title='Node Diff', size=(500,500), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		border = 5

		# header information
		headerGrid = SimpleGrid(self, ['path', 'id', 'status'], None, \
			[[node.getPathString()], [node.getNodeIDString()], [node.getStatusString()]])
		# static box with contents
		headerBox = wx.StaticBox(self, -1, 'General Information')
		headerBoxSizer = wx.StaticBoxSizer(headerBox, wx.VERTICAL)
		headerBoxSizer.Add(headerGrid, 1, wx.ALL | wx.EXPAND, border)

		# diff information


		# list box with database occurrences
		dbOccurencesList = wx.ListBox(self)
		# static box with contents
		dbOccurencesBox = wx.StaticBox(self, -1, 'Occurrences in database')
		dbOccurencesBoxSizer = wx.StaticBoxSizer(dbOccurencesBox, wx.VERTICAL)
		dbOccurencesBoxSizer.Add(dbOccurencesList, 1, wx.ALL | wx.EXPAND, border)

		# list box with filesystem occurrences
		fsOccurencesList = wx.ListBox(self)
		# static box with contents
		fsOccurencesBox = wx.StaticBox(self, -1, 'Occurrences in filesystem')
		fsOccurencesBoxSizer = wx.StaticBoxSizer(fsOccurencesBox, wx.VERTICAL)
		fsOccurencesBoxSizer.Add(fsOccurencesList, 1, wx.ALL | wx.EXPAND, border)

		button = wx.Button(self, label='OK')
		button.SetFocus()
		self.Bind(wx.EVT_BUTTON, self.OnClick, button)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(headerBoxSizer, 0, wx.ALL | wx.EXPAND, border)
		sizer.Add(dbOccurencesBoxSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(fsOccurencesBoxSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(button, 0, wx.ALL | wx.ALIGN_CENTER, border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

	def OnClick(self, event):
		self.Destroy()
