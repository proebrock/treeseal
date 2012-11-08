#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os



class TestDir(object):

	def __init__(self, path):
		self.__path = path
		self.__testFileLength = 1024

	def createDefaultSet(self, suffix=''):
		if not suffix == '':
			suffix = '_' + suffix
		self.mkdir('DirMissing' + suffix)
		self.mkfile('FileMissing' + suffix)
		self.mkdir('DirOK' + suffix)
		self.mkfile('FileOK' + suffix)
		self.mkfile('FileWarning' + suffix)
		self.mkfile('FileError' + suffix)
		self.mkdir('DirContainsNewFile' + suffix)
		self.mkdir('DirContainsNewDir' + suffix)
		self.mkdir('DirContainsMissingFile' + suffix)
		self.mkfile(os.path.join('DirContainsMissingFile' + suffix, 'FileMissing'))
		self.mkdir('DirContainsMissingDir' + suffix)
		self.mkdir(os.path.join('DirContainsMissingDir' + suffix, 'DirMissing'))
		self.mkdir('DirContainsFileOK' + suffix)
		self.mkfile(os.path.join('DirContainsFileOK' + suffix, 'FileOk'))
		self.mkdir('DirContainsFileWarning' + suffix)
		self.mkfile(os.path.join('DirContainsFileWarning' + suffix, 'FileWarning'))
		self.mkdir('DirContainsFileError' + suffix)
		self.mkfile(os.path.join('DirContainsFileError' + suffix, 'FileError'))
		self.mkdir('DirContainsMultiple' + suffix)
		self.mkfile(os.path.join('DirContainsMultiple' + suffix, 'FileMissing'))

	def changeDefaultSet(self, suffix=''):
		if not suffix == '':
			suffix = '_' + suffix
		self.mkdir('DirNew' + suffix)
		self.mkfile('FileNew' + suffix)
		self.rmdir('DirMissing' + suffix)
		self.rmfile('FileMissing' + suffix)
		self.changefile('FileWarning' + suffix)
		self.changefile('FileError' + suffix, None, True)
		self.mkfile(os.path.join('DirContainsNewFile' + suffix, 'FileNew'))
		self.mkdir(os.path.join('DirContainsNewDir' + suffix, 'DirNew'))
		self.rmfile(os.path.join('DirContainsMissingFile' + suffix, 'FileMissing'))
		self.rmdir(os.path.join('DirContainsMissingDir' + suffix, 'DirMissing'))
		self.changefile(os.path.join('DirContainsFileWarning' + suffix, 'FileWarning'))
		self.changefile(os.path.join('DirContainsFileError' + suffix, 'FileError'), None, True)
		self.mkfile(os.path.join('DirContainsMultiple' + suffix, 'FileNew'))
		self.rmfile(os.path.join('DirContainsMultiple' + suffix, 'FileMissing'))

	def create(self):
		self.down('Status')
		self.createDefaultSet()
		self.up()

		self.down('FileDirChanges')
		self.mkdir('DirToFile')
		self.mkfile('FileToDir')
		self.up()

		self.down('ZeroSize')
		self.mkfile('AlwaysZeroSize', '')
		self.mkfile('HadZeroSize', '')
		self.mkfile('HasZeroSize'	)
		self.up()

		self.down('SpecialChars')
		self.createDefaultSet('With   Space')
		self.createDefaultSet('UmlauteÄÖÜäöü')
		self.up()

	def change(self):
		self.down('Status')
		self.changeDefaultSet()
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
		self.up()

		self.down('SpecialChars')
		self.changeDefaultSet('With   Space')
		self.changeDefaultSet('UmlauteÄÖÜäöü')
		self.up()

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