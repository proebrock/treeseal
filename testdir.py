#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
		self.mkdir('EmptyDir')
		self.mkdir('DirNew')
		self.mkdir('DirMissing')
		self.mkdir(os.path.join('DirMissing', 'DirMissing'))
		self.mkdir('FileOK')
		self.mkfile(os.path.join('FileOK', 'FileOK'))
		self.mkdir('FileNew')
		self.mkdir('FileMissing')
		self.mkfile(os.path.join('FileMissing', 'FileMissing'))
		self.mkdir('FileWarning')
		self.mkfile(os.path.join('FileWarning', 'FileWarning'))
		self.mkdir('FileError')
		self.mkfile(os.path.join('FileError', 'FileError'))

		self.up()

		self.down('FileDirChanges')
		self.mkdir('DirToFile')
		self.mkfile('FileToDir')
		self.up()

		self.down('ZeroSize')
		self.mkfile('AlwaysZeroSize', '')
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
		self.mkdir(os.path.join('DirNew', 'DirNew'))
		self.rmdir(os.path.join('DirMissing', 'DirMissing'))
		self.mkfile(os.path.join('FileNew', 'FileNew'))
		self.rmfile(os.path.join('FileMissing', 'FileMissing'))
		self.changefile(os.path.join('FileWarning', 'FileWarning'))
		self.changefile(os.path.join('FileError', 'FileError'), None, True)
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
		if keeptimes:
			st = os.stat(fullpath)
		f = open(fullpath, 'w')
		if newcontent is None:
			f.write(os.urandom(self.__testFileLength))
		else:
			f.write(newcontent)
		f.close()
		if keeptimes:
			os.utime(fullpath, (st.st_atime, st.st_mtime))

	def rmfile(self, path):
		os.remove(os.path.join(self.__path, path))







#path = 'D:\\Projects\\dtint-example'
path = '/home/phil/Projects/dtint-example'
td = TestDir(path)
if not os.path.exists(os.path.join(path, '.dtint')):
	print('creating initial version of testdir ...')
	td.create()
else:
	print('creating modified version of testdir ...')
	td.change()