import wx



class SimpleGrid(wx.FlexGridSizer):

	def __init__(self, parent, entries, rowlabels=None, collabels=None, markers=None):
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
				entry = wx.TextCtrl(parent, -1, entries[i][j], style=wx.TE_READONLY)
				if markers is not None:
					if markers[i][j]:
						entry.SetBackgroundColour('Yellow')
				self.Add(entry, 0, otherColAlign, border)

		# make all columns growable (except first one if we have row labels)
		for i in range(haveRowLabels, haveRowLabels + numCols):
			self.AddGrowableCol(i)



class NodeComparisonDialog(wx.Dialog):

	def __init__(self, parent, node):
		wx.Dialog.__init__(self, parent, title='Node information', size=(500,600), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		border = 5

		# header information
		entries = [ \
			[node.getPathString()], \
			[node.getNodeIDString()], \
			[node.getParentIDString()], \
			[node.getStatusString()], \
			]
		rowlabels = ['Path', 'ID', 'Parent ID', 'Status']
		headerGrid = SimpleGrid(self, entries, rowlabels)
		# static box with contents
		headerBox = wx.StaticBox(self, -1, 'General')
		headerBoxSizer = wx.StaticBoxSizer(headerBox, wx.VERTICAL)
		headerBoxSizer.Add(headerGrid, 1, wx.ALL | wx.EXPAND, border)

		if not node.isDirectory():
			# diff information
			rowlabels = ['Size','Creation time', 'Access time', 'Modification time', 'Checksum']
			entries = [ \
					[node.info.getSizeString()], \
					[node.info.getCTimeString()], \
					[node.info.getATimeString()], \
					[node.info.getMTimeString()], \
					[node.info.getChecksumString()], \
					]
			if node.other is None:
				boxstring = 'Details'
				collabels = None
				markers = None
			else:
				boxstring = 'Differences'
				collabels = ['Database', 'Filesystem']
				otherstr = [\
						[node.other.info.getSizeString()], \
						[node.other.info.getCTimeString()], \
						[node.other.info.getATimeString()], \
						[node.other.info.getMTimeString()], \
						[node.other.info.getChecksumString()], \
						]
				markers = []
				for i in range(len(entries)):
					entries[i].append(otherstr[i][0])
					if not entries[i][0] == otherstr[i][0]:
						markers.append([ True, True ])
					else:
						markers.append([ False, False ])

			diffGrid = SimpleGrid(self, entries, rowlabels, collabels, markers)
			# static box with contents
			diffBox = wx.StaticBox(self, -1, boxstring)
			diffBoxSizer = wx.StaticBoxSizer(diffBox, wx.VERTICAL)
			diffBoxSizer.Add(diffGrid, 1, wx.ALL | wx.EXPAND, border)

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
		if not node.isDirectory():
			sizer.Add(diffBoxSizer, 0, wx.ALL | wx.EXPAND, border)
			sizer.Add(dbOccurencesBoxSizer, 1, wx.ALL | wx.EXPAND, border)
			sizer.Add(fsOccurencesBoxSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(button, 0, wx.ALL | wx.ALIGN_CENTER, border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

	def OnClick(self, event):
		self.Destroy()
