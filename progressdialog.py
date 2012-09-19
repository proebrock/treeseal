import wx

from misc import sizeToString, MyException



class UserCancelledException(Exception):
	def __init_(self):
		super(UserCancelledException, self).__init__('UserCancelledException')

	def __str__(self):
		return 'UserCancelledException'



class FileProcessingProgressDialog(wx.Dialog):

	def __init__(self, parent, title):
		wx.Dialog.__init__(self, parent, title=title, size=(500,380), \
			style=wx.CAPTION | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

		self.currentBytesDone = None
		self.currentBytesAll = None
		self.totalFilesDone = None
		self.totalFilesAll = None
		self.totalBytesDone = None
		self.totalBytesAll = None
		self.cancelRequest = False

		border = 5

		self.processingText = wx.StaticText(self, label='Initializing ...')
		self.currentPathText = wx.StaticText(self, label='')
		processingSizer = wx.BoxSizer(wx.VERTICAL)
		processingSizer.Add(self.processingText, 0, wx.ALL | wx.EXPAND, border)
		processingSizer.Add(self.currentPathText, 0, wx.BOTTOM | wx.EXPAND, border+25)

		self.currentBytesHeader = wx.StaticText(self)
		self.currentBytesGauge = wx.Gauge(self)
		self.currentBytesGaugeText = wx.StaticText(self, size=(40,-1))
		currentBytesSizer = wx.BoxSizer(wx.HORIZONTAL)
		currentBytesSizer.Add(self.currentBytesGauge, 1, wx.ALL | wx.EXPAND, border)
		currentBytesSizer.Add(self.currentBytesGaugeText, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		self.totalFilesHeader = wx.StaticText(self)
		self.totalFilesGauge = wx.Gauge(self)
		self.totalFilesGaugeText = wx.StaticText(self, size=(40,-1))
		totalFilesSizer = wx.BoxSizer(wx.HORIZONTAL)
		totalFilesSizer.Add(self.totalFilesGauge, 1, wx.ALL | wx.EXPAND, border)
		totalFilesSizer.Add(self.totalFilesGaugeText, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		self.totalBytesHeader = wx.StaticText(self)
		self.totalBytesGauge = wx.Gauge(self)
		self.totalBytesGaugeText = wx.StaticText(self, size=(40,-1))
		totalBytesSizer = wx.BoxSizer(wx.HORIZONTAL)
		totalBytesSizer.Add(self.totalBytesGauge, 1, wx.ALL | wx.EXPAND, border)
		totalBytesSizer.Add(self.totalBytesGaugeText, 0, wx.ALL | wx.ALIGN_CENTRE, border)

		self.button = wx.Button(self, label='Cancel')
		self.button.SetFocus()
		self.Bind(wx.EVT_BUTTON, self.OnClick, self.button)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(processingSizer, 0, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.currentBytesHeader, 0, wx.ALL | wx.EXPAND, border)
		sizer.Add(currentBytesSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.totalFilesHeader, 0, wx.ALL | wx.EXPAND, border)
		sizer.Add(totalFilesSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.totalBytesHeader, 0, wx.ALL | wx.EXPAND, border)
		sizer.Add(totalBytesSizer, 1, wx.ALL | wx.EXPAND, border)
		sizer.Add(self.button, 0, wx.ALL | wx.ALIGN_CENTER, border)
		self.SetSizer(sizer)
		self.CenterOnScreen()

		self.OnPaint()

	def OnClick(self, event):
		if self.button.GetLabel() == 'OK':
			self.Destroy()
		else:
			self.cancelRequest = True

	def Init(self, totalFiles, totalSize):
		#print('init for {0:d} files and {1:d} bytes'.format(totalFiles, totalSize))

		# the gauge control accepts a range of integer type, but the sizes
		# (and maybe number of files) exceed the integer range of 2/4 GB;
		# we do not do any scaling is size/number is smaller than this factor;
		# scaling is just used for the gauges, other variables contain the
		# correct sizes!
		self.gaugeScalingFactor = 1e6

		self.totalFilesDone = 0
		if totalFiles <= self.gaugeScalingFactor:
			self.totalFilesFactor = 1
		else:
			self.totalFilesFactor = totalFiles / self.gaugeScalingFactor
		self.totalFilesAll = totalFiles
		self.totalFilesGauge.SetRange(totalFiles / self.totalFilesFactor)

		self.totalBytesDone = 0
		if totalSize <= self.gaugeScalingFactor:
			self.totalBytesFactor = 1
		else:
			self.totalBytesFactor = totalSize / self.gaugeScalingFactor
		self.totalBytesAll = totalSize
		self.totalBytesGauge.SetRange(totalSize / self.totalBytesFactor)

		self.OnPaint()

	def SignalNewFile(self, path, size):
		#print('signal new file "{0:s}", size {1:d}'.format(path, size))
		if not self.currentBytesDone == self.currentBytesAll:
			raise MyException('Signaled a new file but the old one is not done yet.', 3)
		if self.totalBytesDone == 0:
			self.processingText.SetLabel('Processing ...')
		if path is None:
			self.currentPathText.SetLabel('<No known path>')
		else:
			self.currentPathText.SetLabel(path)
		self.currentBytesDone = 0
		if size <= self.gaugeScalingFactor:
			self.currentBytesFactor = 1
		else:
			self.currentBytesFactor = size / self.gaugeScalingFactor
		self.currentBytesAll = size
		self.currentBytesGauge.SetRange(size / self.currentBytesFactor)
		if size == 0:
			self.totalFilesDone += 1
		self.OnPaint()
		if self.cancelRequest:
			raise UserCancelledException()

	def SignalBytesDone(self, bytesDone):
		#print('signal {0:d} bytes done, current is {1:d}/{2:d}'.format( \
		#	bytesDone, self.currentBytesDone, self.currentBytesAll))
		# ignore zero byte changes
		if bytesDone == 0:
			return
		# update current bytes
		self.currentBytesDone += bytesDone
		if self.currentBytesDone > self.currentBytesAll:
			raise MyException('Signaled current size larger than full size.', 3)
		elif self.currentBytesDone == self.currentBytesAll:
			# file is complete
			self.totalFilesDone += 1
			if self.totalFilesDone > self.totalFilesAll:
				raise MyException('Signaled number of files larger than full size.', 3)
		# update total bytes
		self.totalBytesDone += bytesDone
		if self.totalBytesDone > self.totalBytesAll:
			raise MyException('Signaled total size larger than full size.', 3)
		self.OnPaint()
		if self.cancelRequest:
			raise UserCancelledException()

	def SignalFinished(self):
		#print('signal finished, cancel request is {0:b}'.format(self.cancelRequest))
		self.button.SetLabel('OK')
		if self.cancelRequest:
			self.processingText.SetLabel('Canceled by user.')
		else:
			self.processingText.SetLabel('All files successfully processed.')
		self.currentPathText.SetLabel('')
		self.ShowModal()

	def OnPaint(self):
		# size of current file
		if self.currentBytesDone is not None and self.currentBytesAll is not None:
			self.currentBytesHeader.SetLabel('Current File {0:s}/{1:s}'.format( \
				sizeToString(self.currentBytesDone), sizeToString(self.currentBytesAll)))
			if self.currentBytesAll == 0:
				self.currentBytesGauge.SetRange(1)
				self.currentBytesGauge.SetValue(1)
				self.currentBytesGaugeText.SetLabel('100 %')
			else:
				self.currentBytesGauge.SetValue(self.currentBytesDone / self.currentBytesFactor)
				self.currentBytesGaugeText.SetLabel('{0:d} %'.format( \
				(100 * self.currentBytesDone) / self.currentBytesAll))
		else:
			self.currentBytesHeader.SetLabel('Current File -/-')
			self.currentBytesGauge.SetValue(0)
			self.currentBytesGaugeText.SetLabel('--- %')
		# total number of files
		if self.totalFilesDone is not None and self.totalFilesAll is not None:
			self.totalFilesHeader.SetLabel('Total Number of Files {0:d}/{1:d}'.format( \
				self.totalFilesDone, self.totalFilesAll))
			if self.totalFilesAll == 0:
				self.totalFilesGauge.SetRange(1)
				self.totalFilesGauge.SetValue(1)
				self.totalFilesGaugeText.SetLabel('100 %')
			else:
				self.totalFilesGauge.SetValue(self.totalFilesDone / self.totalFilesFactor)
				self.totalFilesGaugeText.SetLabel('{0:d} %'.format( \
				(100 * self.totalFilesDone) / self.totalFilesAll))
		else:
			self.totalFilesHeader.SetLabel('Total Number of Files -/-')
			self.totalFilesGauge.SetValue(0)
			self.totalFilesGaugeText.SetLabel('--- %')
		# total size of all files
		if self.totalBytesDone is not None and self.totalBytesAll is not None:
			self.totalBytesHeader.SetLabel('Total Size {0:s}/{1:s}'.format( \
				sizeToString(self.totalBytesDone), sizeToString(self.totalBytesAll)))
			if self.totalBytesAll == 0:
				self.totalBytesGauge.SetRange(1)
				self.totalBytesGauge.SetValue(1)
				self.totalBytesGaugeText.SetLabel('100 %')
			else:
				self.totalBytesGauge.SetValue(self.totalBytesDone / self.totalBytesFactor)
				self.totalBytesGaugeText.SetLabel('{0:d} %'.format( \
				(100 * self.totalBytesDone) / self.totalBytesAll))
		else:
			self.totalBytesHeader.SetLabel('Total Size -/-')
			self.totalBytesGauge.SetValue(0)
			self.totalBytesGaugeText.SetLabel('--- %')
		# force a repaint of the dialog
		self.Update()
		# allow wx to process events like for the cancel button
		wx.YieldIfNeeded()



