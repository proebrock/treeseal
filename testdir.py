import os



class TestDir(object):

	def __init__(self, path):
		self.__path = path
		self.__testFileLength = 1024

	def create(self):
		self.down('Status')
		self.mkdir('DirMissing')
		self.mkfile('FileOK')
		self.mkfile('FileMissing')
		self.mkfile('FileWarning')
		self.mkfile('FileError')
		self.up()

		self.down('StatusChildren')
		self.mkdir('DirOK')
		self.mkfile(os.path.join('DirOK', 'FileOK'))
		self.mkdir('DirNew')
		self.mkdir('DirMissing')
		self.mkfile(os.path.join('DirMissing', 'FileMissing'))
		self.mkdir('DirWarning')
		self.mkfile(os.path.join('DirWarning', 'FileWarning'))
		self.mkdir('DirError')
		self.mkfile(os.path.join('DirError', 'FileError'))
		self.up()

		self.down('FileDirChanges')
		self.mkdir('DirToFile')
		self.mkfile('FileToDir')
		self.up()

		self.down('ZeroSize')
		self.mkfile('HadZeroSize', '')
		self.mkfile('HasZeroSize'	)

	def change(self):
		self.down('Status')
		self.mkdir('DirNew')
		self.rmdir('DirMissing')
		self.mkfile('FileNew')
		self.rmfile('FileMissing')
		self.changefile('FileWarning')
		self.changefile('FileError', None, True)
		self.up()

		self.down('StatusChildren')
		self.mkfile(os.path.join('DirNew', 'FileNew'))
		self.rmfile(os.path.join('DirMissing', 'FileMissing'))
		self.changefile(os.path.join('DirWarning', 'FileWarning'))
		self.changefile(os.path.join('DirError', 'FileError'))
		self.up()

		self.down('FileDirChanges')
		self.rmdir('DirToFile')
		self.mkfile('DirToFile')
		self.rmfile('FileToDir')
		self.mkdir('FileToDir')
		self.up()

		self.down('ZeroSize')
		self.changefile('HadZeroSize')
		self.changefile('HasZeroSize', '')

	# directory

	def down(self, name):
		self.__path = os.path.join(self.__path, name)
		if not os.path.exists(self.__path):
			os.mkdir(self.__path)

	def up(self):
		self.__path = os.path.split(self.__path)[0]

	def mkdir(self, path):
		os.mkdir(os.path.join(self.__path, path))

	def rmdir(self, path):
		os.rmdir(os.path.join(self.__path, path))

	# file

	def mkfile(self, path, content=None):
		f = open(os.path.join(self.__path, path), 'w')
		if content is None:
			f.write(os.urandom(self.__testFileLength))
		else:
			f.write(content)
		f.close()

	def changefile(self, path, newcontent=None, keeptimes=False):
		fullpath = os.path.join(self.__path, path)
		st = os.stat(fullpath)
		f = open(fullpath, 'w')
		if newcontent is None:
			f.write(os.urandom(self.__testFileLength))
		else:
			f.write(newcontent)
		f.close()
		os.utime(fullpath, (st.st_atime, st.st_mtime))

	def rmfile(self, path):
		os.remove(os.path.join(self.__path, path))







#path = 'D:\\Projects\\dtint-example'
path = '/home/phil/Projects/dtint-example'
td = TestDir(path)
if not os.path.exists(os.path.join(path, '.dtint')):
	td.create()
else:
	td.change()