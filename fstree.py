#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import platform
import re
import shutil

from misc import MyException, Checksum
from node import NodeInfo, Node
from tree import Tree



class FilesystemTree(Tree):

	def __init__(self, rootdir, metadir):
		super(FilesystemTree, self).__init__()
		self.__rootDir = rootdir
		self.__metaDir = metadir

		self.__winForbiddenDirs = [ \
			re.compile('[a-zA-Z]:\\\\System Volume Information'), \
			re.compile('[a-zA-Z]:\\\\\$RECYCLE.BIN'), \
			]

		self.__checksumToPathsMap = {}

		self.gotoRoot()

	def __str__(self):
		result = '('
		result += 'FilesystemTree: '
		result += 'depth=\'' + str(self.getDepth()) + '\''
		result += ', path=\'' + self.getPath() + '\''
		return result + ')'

	### implementation of base class methods, please keep order

	def open(self):
		self.__isOpen = True

	def close(self):
		self.__isOpen = False

	def isOpen(self):
		return self.__isOpen

	def clear(self):
		for name in os.listdir(self.__rootDir):
			fullpath = os.path.join(self.__rootDir, name)
			if fullpath == self.__metaDir:
				continue
			shutil.rmtree()
		self.__checksumToPathsMap = {}
		self.gotoRoot()

	def getDepth(self):
		return len(self.__parentNameStack) - 1

	def getPath(self, filename=None):
		path = reduce(lambda x, y: os.path.join(x, y), self.__parentNameStack)
		if filename is None:
			return path
		else:
			return os.path.join(path, filename)

	def gotoRoot(self):
		self.__parentNameStack = [ '' ]
		self.readCurrentDir()

	def up(self):
		if self.isRoot():
			raise MyException('\'up\' on root node is not possible.', 3)
		name = self.__parentNameStack.pop()
		self.readCurrentDir()
		return name

	def down(self, node):
		if not node.isDirectory():
			raise MyException('\'down\' on file \'' + node.name + '\' is not possible.', 3)
		self.__parentNameStack.append(node.name)
		self.readCurrentDir()

	def insert(self, node):
		pass

	def update(self, node):
		pass

	def delete(self, nid):
		if not self.exists(nid):
			raise MyException('Node does not exist for deletion.', 1)
		# remove on disk
		fullpath = self.getFullPath(Node.nid2Name(nid))
		if os.path.isdir(fullpath):
			os.rmdir(fullpath)
		else:
			os.remove(fullpath)
		# remove node from checksum buffer
		node = self.__buffer[nid]
		if not node.isDirectory():
			csumstr = node.info.checksum.getString()
			self.__checksumToPathsMap[csumstr].remove(self.getPath(node.name))
			if len(self.__checksumToPathsMap[csumstr]) == 0:
				del self.__checksumToPathsMap[csumstr]
		# remove node from buffer
		del self.__buffer[nid]

	def commit(self):
		pass

	def exists(self, nid):
		return nid in self.__buffer

	def getNodeByNid(self, nid):
		if not self.exists(nid):
			return None
		else:
			return self.__buffer[nid]

	def __iter__(self):
		for nid in sorted(self.__buffer.keys()):
			yield self.__buffer[nid]

	def calculate(self, node):
		if node.isDirectory():
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node.name), node.info.size)
			fullpath = self.getFullPath(node.name)
			# calculate checksum
			node.info.checksum = Checksum()
			#print('### expensive calculation for node \'' + self.getPath(node.name) + '\' ...')
			node.info.checksum.calculateForFile(fullpath, self.signalBytesDone)
			# buffering of checksums
			csumstr = node.info.checksum.getString()
			if not csumstr in self.__checksumToPathsMap:
				self.__checksumToPathsMap[csumstr] = set()
			self.__checksumToPathsMap[csumstr].add(self.getPath(node.name))
			# determine file timestamps AFTER calculating the checksum, otherwise opening
			# the file might change the access time (OS dependent)
			stat = os.stat(fullpath)
			node.info.ctime = datetime.datetime.fromtimestamp(stat.st_ctime)
			node.info.atime = datetime.datetime.fromtimestamp(stat.st_atime)
			node.info.mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

	def globalChecksumExists(self, checksumString):
		return checksumString in self.__checksumToPathsMap

	def globalGetPathsByChecksum(self, checksumString):
		if checksumString in self.__checksumToPathsMap:
			return self.__checksumToPathsMap[checksumString]
		else:
			return set()

	### the following methods are not implementations of base class methods

	def readCurrentDir(self):
		self.__buffer = {}
		for name in os.listdir(self.getFullPath()):
			node = self.__fetch(name)
			if node is not None:
				self.__buffer[node.getNid()] = node

	def getFullPath(self, name=''):
		return os.path.join(self.__rootDir, self.getPath(), name)

	def __fetch(self, name):
		fullpath = self.getFullPath(name)
		# check blacklists
		if fullpath == self.__metaDir:
			return None
		if platform.system() == 'Windows':
			apath = os.path.abspath(fullpath)
			for regex in self.__winForbiddenDirs:
				if regex.match(apath):
					return None
		# fetch node information
		node = Node(name)
		if not os.path.isdir(fullpath):
			node.info = NodeInfo()
			node.info.size = os.path.getsize(fullpath)
		return node
