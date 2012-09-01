import wx
import wx.grid as gridlib



class SimpleGrid(gridlib.Grid):

	def __init__(self, parent, rowlabels, collabels, entries):

		gridlib.Grid.__init__(self, parent, -1)

		# set grid size
		self.CreateGrid(len(entries), len(entries[0]))

		# set labels
		if not rowlabels is None:
			for i in range(len(rowlabels)):
				self.SetRowLabelValue(i, rowlabels[i])
		else:
			self.SetRowLabelSize(0)
		if not collabels is None:
			for i in range(len(collabels)):
				self.SetColLabelValue(i, rowlabels[i])
		else:
			self.SetColLabelSize(0)

		# set contents
		for i in range(len(entries)):
			for j in range(len(entries[i])):
				self.SetCellValue(i, j, entries[i][j])
				self.SetReadOnly(i, j, True)

		self.AutoSize()




class NodeComparisonDialog(wx.Dialog):

	def __init__(self, parent, node):
		wx.Dialog.__init__(self, parent, title='Compare', size=(500,350), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		border = 5

		self.headergrid = SimpleGrid(self, \
			['path', 'id', 'status'], \
			None,
			[[node.getPathString()], [node.getNodeIDString()], [node.getStatusString()]])

		self.dbOccurences = wx.ListBox(self)
		self.fsOccurences = wx.ListBox(self)

		button = wx.Button(self, label='OK')
		button.SetFocus()
		self.Bind(wx.EVT_BUTTON, self.OnClick, button)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.headergrid, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.dbOccurences, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.fsOccurences, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(button, 0, wx.ALL | wx.ALIGN_CENTER, border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

	def OnClick(self, event):
		self.Destroy()
