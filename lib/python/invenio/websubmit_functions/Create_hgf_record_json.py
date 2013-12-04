from configobj import ConfigObj             #module for reading config-file
from invenio.config import * #(local-conf)
import os, sys, re
#try: import json
#except ImportError: import simplejson as json
import simplejson as json

from invenio.websubmit_functions.Websubmit_Helpers_hgf import read_file,\
								read_json,\
								get_hgf_files,\
								get_recordid,\
								check_hgf_field,\
								backup_file,\
								washJSONinput

############## Classes #################################
class Create_json_hgf_record:
	"""build hgf_record as json-structure"""
	def __init__(self,curdir):
		self.data = {}
		self.curdir = curdir

  	def add_jsondict(self,fieldname):
		"""add field structure (json structure)"""
		marcfield = fieldname.replace("hgf_","")
		jsondict = {marcfield:read_json(self.curdir,fieldname)}
		for key in jsondict.keys():
			#  TODO Check if this code is really obsolete
			# Should be solved by our new initial ordering of the fields.
			#
			#if key in self.data.keys():
				#datafield already exists
			#	if isinstance(jsondict[key],list):
			#		if len(jsondict[key]) != 1: # repeatable field
			#			self.data[key] = jsondict[key]

			#			return # jsondict has repeatable field, but we cannot add a single field to repeatable fields --> we delete the single input field and override it with json-structure
			#		else:  #non repeatable
			#			if len(self.data[key]) != 1: #we have repeatable non-json field-->override with json structure
			#				self.data[key] = jsondict[key]
			#			else:
			#				jsondict[key][0].update(self.data[key][0]) #merge non-json with json structure
			#				self.data[key] = jsondict[key][0] # add all fields to dictionary
			#else:
				if isinstance(jsondict[key],list): self.data[key] = jsondict[key] #value is already a list
				elif isinstance(jsondict[key],str): #value is string
					dta =  eval(jsondict[key]) #TODO: eval is evil!
					if isinstance(dta,list): self.data[key] = dta #value is a list in a string
					else: self.data[key] = [dta] #value is just a string
				else: return

	def add_one_field(self,marcfield,subfield,value):
		"""add field, no json structure
		This function expects that technical fields are processed first
		"""
		if marcfield in self.data.keys():
			if self.data[marcfield] == []: # empty list in case of postpone. i.e no 1001_
				self.data[marcfield] = [{subfield:value}]
			else:
				self.data[marcfield][0][subfield] = value
		else: self.data[marcfield] = [{subfield:value}]

	def add_field(self,fieldname):
		"""add a field  (no json structure) to dictionary
		This function builds a structured field in self.data if we have several subfields as individual files.
		"""
		text = read_file(self.curdir,fieldname)
		fieldname = fieldname.replace("hgf_", "")
		marcfield = fieldname[0:5]
		subfield = fieldname[5]
		self.add_one_field(marcfield,subfield,text)

	def write_json(self,fieldname="hgf_record",):
		"""write python dictionary as json-file"""
		fw = open(os.path.join(self.curdir,fieldname), "w")
		json.dump(self.data, fw, sort_keys=True, indent=2)
		fw.close()

	def add_key_value(self,key,value): self.data[key] = value

	def transform_values_into_list(self):
		"""convert values of keys into lists for Make_HGF_Record"""
		for key in self.data.keys():
			if isinstance(self.data[key],list): continue
			self.data[key] = [self.data[key]]

	def process_master(self,fieldname):
		"""write python dictionary as json-file for field hgf_master"""
		master = Create_json_hgf_record(self.curdir)
		master.add_jsondict(fieldname)
		master.write_json(fieldname)

	def print_values(self):	print self.data

############# End Classes #################################

############# Functions ###################################

def Create_hgf_record_json(parameters,curdir, form, user_info=None):
	"""run over all hgf_fields and create hgf_record in json-format"""
	# sort the files by name. This results in getting all structured
	# fields FIRST and then (in case they exist) individual subfields.
	hgf_files = sorted(get_hgf_files(curdir))
	hgf_rec = Create_json_hgf_record(curdir)
	for fieldname in hgf_files:
		flag, ident = check_hgf_field(fieldname)
		if not flag: continue # no standard marc-field (e.g. hgf_vdb)
		if ident == "json": hgf_rec.add_jsondict(fieldname) #add json structure
		elif ident == "asci": hgf_rec.add_field(fieldname) #add non json structure
		elif ident == "master":
			backup_file(curdir,fieldname)
			hgf_rec.process_master(fieldname) #process master record
		else: continue
	recid = get_recordid(curdir)
	hgf_rec.transform_values_into_list() #convert values into lists for Make_HGF_Record
	hgf_rec.add_key_value("001",recid) #add recid to json-dict
	hgf_rec.write_json()
	#hgf_rec.print_values()

if __name__ == "__main__":
	curdir = os.getcwd()
	Create_hgf_record_json("",curdir,"")
