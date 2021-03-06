#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import shutil

from misc import MyException, Checksum
from node import NodeInfo, Node
from tree import Tree
from filefilter import FileFilter



class FilesystemTree(Tree):

	def __init__(self, rootdir, includes, excludes):
		super(FilesystemTree, self).__init__()
		self.__rootDir = rootdir

		self.__filter = FileFilter(includes, excludes)

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
			if self.__filter.EntryAccepted(self.__rootDir, self.getPath(), name):
				shutil.rmtree()
		self.__checksumToPathsMap = {}
		self.gotoRoot()

	def getDepth(self):
		return len(self.__parentNameStack) - 1

	def getPath(self, node=None):
		path = reduce(lambda x, y: os.path.join(x, y), self.__parentNameStack)
		if node is None:
			return path
		else:
			return os.path.join(path, node.name)

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
		if node.isFile():
			raise MyException('\'down\' on file \'' + node.name + '\' is not possible.', 3)
		self.__parentNameStack.append(node.name)
		self.readCurrentDir()

	def numChildren(self, node):
		if node.isFile():
			return 0
		else:
			count = 0
			for name in os.listdir(self.getFullPath()):
				node = self.__fetch(name)
				if node is not None:
					count += 1
			return count

	def insert(self, node):
		pass

	def update(self, node):
		pass

	def delete(self, node):
		if not self.isChildless(node):
			raise MyException('Deleting the non-empty directory \'' + node.name + '\'.', 1)
		nid = node.getNid()
		if not self.exists(nid):
			raise MyException('Node does not exist for deletion.', 1)
		# remove on disk
		fullpath = self.getFullPath(node.name)
		if os.path.isdir(fullpath):
			os.rmdir(fullpath)
		else:
			os.remove(fullpath)
		# remove node from checksum buffer
		if node.isFile():
			if node.info.checksum is None:
				# this is a problem: for deletion we have to be able to update
				# the checksum buffer; if the caller provides us with a node
				# object, that contains no checksum, we are lost because
				# checksums are very expensive to calculate in the Filesystem
				# implementation so we cannot do that here
				raise MyException('Node that should be deleted has no checksum.', 3)
			csumstr = node.info.checksum.getString()
			self.__checksumToPathsMap[csumstr].remove(self.getPath(node))
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
				self.signalNewFile(self.getPath(node), 0)
		else:
			if self.signalNewFile is not None:
				self.signalNewFile(self.getPath(node), node.info.size)
			fullpath = self.getFullPath(node.name)
			# calculate checksum
			node.info.checksum = Checksum()
			#print('### expensive calculation for node \'' + self.getPath(node) + '\' ...')
			node.info.checksum.calculateForFile(fullpath, self.signalBytesDone)
			# buffering of checksums
			csumstr = node.info.checksum.getString()
			if not csumstr in self.__checksumToPathsMap:
				self.__checksumToPathsMap[csumstr] = set()
			self.__checksumToPathsMap[csumstr].add(self.getPath(node))
			# determine file timestamps AFTER calculating the checksum, otherwise opening
			# the file might change the access time (OS dependent)
			stat = os.stat(fullpath)
			node.info.ctime = datetime.datetime.fromtimestamp(stat.st_ctime)
			node.info.atime = datetime.datetime.fromtimestamp(stat.st_atime)
			node.info.mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

	def globalChecksumExists(self, checksumString):
		return checksumString in self.__checksumToPathsMap

	def globalChecksumNumberOfOccurrences(self, checksumString):
		return len(self.globalGetPathsByChecksum(checksumString))

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
		# filter files
		if not self.__filter.EntryAccepted(self.__rootDir, self.getPath(), name):
			return None
		# fetch node information
		fullpath = self.getFullPath(name)
		node = Node(name)
		if not os.path.isdir(fullpath):
			node.info = NodeInfo()
			node.info.size = os.path.getsize(fullpath)
		return node
