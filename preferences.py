#!/usr/bin/env python
# -*- coding: utf-8 -*-



import copy
import platform
import simplejson as json



class Preferences:

	def __init__(self):
		self.setDefaults()

	def __str__(self):
		return json.dumps({ \
			'includes' : self.includes, \
			'excludes' : self.excludes, \
			}, indent='\t')

	def __eq__(self, other):
		if other is None:
			return False
		else:
			return self.includes == other.includes and \
				self.excludes == other.excludes

	def __ne__(self, other):
		return not self.__eq__(other)

	def __copy__(self):
		result = Preferences()
		result.includes = self.includes
		result.excludes = self.excludes
		return result

	def __deepcopy__(self, memo):
		result = Preferences()
		result.includes = copy.deepcopy(self.includes, memo)
		result.excludes = copy.deepcopy(self.excludes, memo)
		return result

	def setDefaults(self):
		self.includes = None
		self.excludes = [
			'Thumbs.db', \
			]
		if platform.system() == 'Windows':
			self.excludes.extend([\
				'\\System Volume Information', \
				'\\$RECYCLE.BIN', \
				])

	def save(self, filename):
		f = open(filename, 'w')
		f.write(self.__str__())
		f.close()

	def load(self, filename):
		# read preferences file
		f = open(filename, 'r')
		pdict = json.load(f)
		f.close()
		# set default values
		self.setDefaults()
		# assign values specified in preferences file
		if 'includes' in pdict:
			self.includes = pdict['includes']
		if 'excludes' in pdict:
			self.excludes = pdict['excludes']
