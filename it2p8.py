#!/usr/bin/python3

### This Source Code Form is subject to the terms of the Mozilla Public
### License, v. 2.0. If a copy of the MPL was not distributed with this
### file, You can obtain one at http://mozilla.org/MPL/2.0/.

# by maple syrup <maple@maple.pet>

import sys
import os
import struct
import pprint

# loads impulsetracker module information
class ImpulseTracker:
	# takes filename, passes it to parser
	def read_file(self, filename):
		# check if file exists?
		if(not os.path.exists(filename)):
			print("File not found: ", filename)
			return -1
		
		# parse file
		with open(filename, 'rb') as f:
			data = f.read()
			return self.parse_it(data)

	# takes binary content, fills self values
	def parse_it(self, data):
		# reference: https://github.com/schismtracker/schismtracker/wiki/ITTECH.TXT

		# check header
		header = struct.unpack_from("4s", data)
		if(header[0] != b'IMPM'):
			print("Not an Impulse Tracker module")
			return -1

		(OrdNum, InsNum, SmpNum, PatNum, Special) = struct.unpack_from("4H6xH", data, offset=0x20)
		(Speed, Tempo) = struct.unpack_from("2B", data, offset=0x32)
		self.speed = Speed
		self.tempo = Tempo

		# if there's a song message:
		if(Special & 0b1):
			# for some reason this wasn't working as a single unpack line with format "HI"
			(MsgLength,) = struct.unpack_from("H", data, offset=0x36)
			(MsgOffset,) = struct.unpack_from("I", data, offset=0x38)
			(message,) = struct.unpack_from("{}s".format(MsgLength), data, offset=MsgOffset)
			message = message.replace(b'\r',b'\n')
			self.message = message.decode("ascii")

		# read orderlist
		Orderlist = struct.unpack_from("{}B".format(OrdNum), data, offset=0xC0)
		# filter to valid pattern numbers 0<=x<=199
		self.orderlist = list(filter(lambda x: x >= 0 and x <= 199, Orderlist))

		# patterns start at offset = int at 00C0h+OrdNum+InsNum*4+SmpNum*4
		PatOffset = struct.unpack_from("{}I".format(PatNum), data, offset=0xC0+OrdNum+InsNum*4+SmpNum*4)

		# read each pattern
		for o in PatOffset:
			(Length, Rows) = struct.unpack_from("2H", data, offset=o)
			(PatData,) = struct.unpack_from("{}s".format(Length), data, offset=o+8)
			Pattern = self.parse_pattern(PatData, Rows)
			self.pattern.append(Pattern)

		return 0

	def parse_pattern(self, data, rows):
		Pattern = []
		offset = 0

		prevmskvar = {}
		prevnote = {}
		previnst = {}
		prevvol = {}
		prevcmd = {}
	
		row = {}

		while offset < len(data):
			# chvar = channel variable
			chnvar = data[offset]
			offset += 1
			if(chnvar == 0):
				# end of row
				Pattern.append(row)
				row = {}
				continue
			Chn = (chnvar-1) & 63

			note = None
			inst = None
			volp = None
			cmd = [None, None]
			
			# mskvar = mask variable
			if(chnvar & 128):
				mskvar = data[offset]
				prevmskvar[Chn] = mskvar
				offset += 1
			else:
				mskvar = prevmskvar[Chn]

			if(mskvar & 1):
				# read note
				note = data[offset]
				if(note > 119):
					note = None
				offset += 1
				prevnote[Chn] = note
			
			if(mskvar & 2):
				# read instrument
				inst = data[offset]
				offset += 1
				previnst[Chn] = inst
			
			if(mskvar & 4):
				# read vol/pan
				volp = data[offset]
				offset += 1
				prevvol[Chn] = volp
			
			if(mskvar & 8):
				# read command & value
				cmd = [data[offset], data[offset+1]]
				offset += 2
				prevcmd[Chn] = cmd

			if(mskvar & 16):
				note = prevnote[Chn]
			if(mskvar & 32):
				inst = previnst[Chn]
			if(mskvar & 64):
				volp = prevvol[Chn]
			if(mskvar & 128):
				cmd = prevcmd[Chn]

			if(note or inst or volp or cmd != [None, None]):
				row[Chn] = (note, inst, volp, cmd)

		return Pattern

	def __init__(self, filename=None):
		pass
		# initialize
		self.orderlist = []
		self.pattern = []
		self.comment = ""
		self.speed = None
		self.tempo = None

		if(filename != None):
			self.read_file(filename)

def interpol(value, leftMin, leftMax, rightMin, rightMax):
	# Figure out how 'wide' each range is
	leftSpan = leftMax - leftMin
	rightSpan = rightMax - rightMin

	# Convert the left range into a 0-1 range (float)
	valueScaled = float(value - leftMin) / float(leftSpan)

	# Convert the 0-1 range into a value in the right range.
	return rightMin + (valueScaled * rightSpan)

def it_to_p8(it):
	output = """\
pico-8 cartridge http://www.pico-8.com
version 16
__lua__

__sfx__
"""

	# objective:
	# convert each channel into sfx string
	# reorganize orderlist into p8 __music__

	sfxs = []
	music = []
	effectmap = {7: 1, 8: 2, 5: 3}

	# load custom sfx instruments
	if(it.message):
		sfxs= it.message.split("\n")

	for p in it.orderlist:
		# p is a pattern index in the .it orderlist

		pat = it.pattern[p]
		curpat = []

		for ch in range(0,4):
			# IT speed: 2.5 sec / tempo * speed per note
			# P8 speed: 1/128 sec * speed per note
			speed = int(((2.5 / it.tempo) * it.speed) / (1/128))

			cursfx = "01{:02x}0000".format(speed)
			prevnote = 0
			previnst = 0
			prevvol = 0
			preveffect = 0

			rowno = 0
			# turn channel into sfx
			for row in pat:
				rowno += 1
				try:
					data = row[ch]
					
					try:
						if(data[0] <= 119):
							note = data[0]-36
					except TypeError:
						# note = NoneType
						note = prevnote

					try:
						inst = data[1]-1
					except TypeError:
						inst = previnst

					if(data[0] != None and data[0] >= 254):
						# note cut or note
						vol = 0
					else:
						vol = data[2]
						if(vol == None):
							if(data[0] == None):
								if(preveffect == 5): # fade out
									vol = 0
								else:
									# this is dumb bc prevvol is in p8 range and it gets re-converted into p8 range a few lintes down but i got lazy sorry
									vol = int(interpol(prevvol,0,7,0,64))
							else:
								vol = 64
						vol = int(interpol(vol,0,64,0,7))

					effect = 0
					iteffect = data[3]
					if(iteffect[0] in effectmap):
						effect = effectmap[iteffect[0]]
					if(iteffect[0] == 4):
						if(iteffect[1] & 0x0F):
							# fade out
							effect = 5
						if(iteffect[1] & 0xF0):
							# fade in
							effect = 4

					# pico8 needs sfx retrigger
					if(inst > 7 and previnst == inst and effect == 0):
						effect = 3

					prevnote = note
					previnst = inst
					prevvol = vol
					preveffect = effect
				
				except KeyError:
					# empty row
					note = prevnote
					inst = previnst
					if(preveffect == 5): # note faded out
						vol = 0
						prevvol = 0
					else:
						vol = prevvol
					effect = 0
					preveffect = 0

				rowstr = "{:02x}{:1x}{:1x}{:1x}".format(note, inst, vol, effect)
				cursfx += rowstr
			
			# if sfx is blank, just add turned off channel to music and continue loop
			if(cursfx[8:] == "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"):
				curpat.append(64)
			else:
				# check if sfx exists
				try:
					index = sfxs.index(cursfx)
					# if yes, add index of match to music
					curpat.append(index)
				except:
					# if not, increase sfx counter, add sfx to list, add index to music
					curpat.append(len(sfxs))
					sfxs.append(cursfx)

		music.append("{:02x}{:02x}{:02x}{:02x}".format(curpat[0],curpat[1],curpat[2],curpat[3]))

	# make it so there are loop markers around first and last patterns
	# this isn't pretty.
	output += "\n".join(sfxs)
	output += "\n\n__music__"
	output += "\n01 {}\n00 ".format(music[0])
	output += "\n00 ".join(music[1:-1])
	output += "\n02 {}".format(music[-1])

	return output

if __name__ == "__main__":
	# check if sys.argv length is right
	if(len(sys.argv) < 2):
		print("usage: {} input.it [output.p8]".format(sys.argv[0]))
		sys.exit()

	try:
		output = sys.argv[2]
	except IndexError:
		filename = os.path.splitext(os.path.basename(sys.argv[1]))
		output = "{}.p8".format(filename[0])

	# take sys.argv[1] into read_file and do stuff
	it = ImpulseTracker(sys.argv[1])
	out = it_to_p8(it)

	with open(output, "w+") as f:
		f.write(out)