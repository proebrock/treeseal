import binascii
import hashlib
import os
import wx



def sizeToString(size):
	if size < 1000:
		sizestr = '{0:d} '.format(size)
	elif size < 1000**2:
		sizestr = '{0:.1f} K'.format(size/1000)
	elif size < 1000**3:
		sizestr = '{0:.1f} M'.format(size/1000**2)
	elif size < 1000**4:
		sizestr = '{0:.1f} G'.format(size/1000**3)
	elif size < 1000**5:
		sizestr = '{0:.1f} T'.format(size/1000**4)
	elif size < 1000**6:
		sizestr = '{0:.1f} P'.format(size/1000**5)
	else:
		sizestr = '{0:.1f} E'.format(size/1000**6)
	return sizestr + 'B'



class MyException(Exception):

	def __init__(self, message, level):
		super(MyException, self).__init__(message)
		self.__message = message
		self.__level = level

	def __str__(self):
		return self.__getPrefix() + ': ' + self.__message

	def __getPrefix(self):
		if self.__level == 0:
			return 'Info'
		elif self.__level == 1:
			return 'Warning'
		elif self.__level == 2:
			return 'Error'
		elif self.__level == 3:
			return '### Fatal Error'
		else:
			raise Exception('Unknown log level {0:d}'.format(self.__level))

	def __getIcon(self):
		if self.__level == 0:
			return wx.ICON_INFORMATION
		elif self.__level == 1:
			return wx.ICON_WARNING
		elif self.__level == 2:
			return wx.ICON_ERROR
		elif self.__level == 3:
			return wx.ICON_STOP
		else:
			raise Exception('Unknown log level {0:d}'.format(self.__level))

	def showDialog(self, headerMessage=''):
		wx.MessageBox(self.__getPrefix() + ': ' + self.__message, \
			headerMessage, wx.OK | self.__getIcon())



class Checksum(object):

	def __init__(self):
		self.__checksum = None # is of type 'buffer'
		self.__checksumbits = 256

	def __str__(self):
		return self.getString()

	def __eq__(self, other):
		if other is None:
			return False
		else:
			return self.getString() == other.getString()

	def __ne__(self, other):
		return not self.__eq__(other)

	def __copy__(self):
		result = Checksum()
		result.__checksum = self.__checksum
		return result

	def __deepcopy__(self, memo):
		result = Checksum()
		result.__checksum = self.__checksum[:]
		return result

	def setBinary(self, checksum):
		if not len(checksum) == self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = checksum

	def getBinary(self):
		return self.__checksum

	def setString(self, checksum):
		if not len(checksum) == 2*self.__checksumbits/8:
			raise MyException('Wrong checksum size.', 3)
		self.__checksum = binascii.unhexlify(checksum)

	def getString(self, abbreviate=False):
		if self.__checksum is None:
			return '<none>'
		else:
			if abbreviate:
				return unicode(binascii.hexlify(self.__checksum[0:4]))
			else:
				return unicode(binascii.hexlify(self.__checksum))

	def calculateForFile(self, path, signalBytesDone=None):
		checksum = hashlib.sha256()
		buffersize = 2**24
		if not os.path.exists(path):
			raise MyException('Unable to open signature file \'' + path + '\'.', 3)
		f = open(path,'rb')
		while True:
			data = f.read(buffersize)
			if not data:
				break
			if signalBytesDone is not None:
				signalBytesDone(len(data))
			checksum.update(data)
		f.close()
		self.__checksum = buffer(checksum.digest())

	def saveToFile(self, path):
		f = open(path, 'w')
		f.write(self.getString())
		f.close()

	def isValidUsingSavedFile(self, path):
		f = open(path, 'r')
		csum = f.read()
		f.close()
		return csum == self.getString()



