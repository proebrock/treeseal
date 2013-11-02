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
			'excludes' : self.excludes, \
			}, indent='\t')

	def __eq__(self, other):
		if other is None:
			return False
		else:
			return self.excludes == other.excludes

	def __ne__(self, other):
		return not self.__eq__(other)

	def __copy__(self):
		result = Preferences()
		result.excludes = self.excludes
		return result

	def __deepcopy__(self, memo):
		result = Preferences()
		result.excludes = copy.deepcopy(self.excludes, memo)
		return result

	def setDefaults(self):
		self.excludes = [
			'Thumbs.db', \
			]
		if platform.system() == 'Windows':
			self.excludes.extend([\
				'[a-zA-Z]:\\\\System Volume Information', \
				'[a-zA-Z]:\\\\\$RECYCLE.BIN', \
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
		if 'excludes' in pdict:
			self.excludes = pdict['excludes']
