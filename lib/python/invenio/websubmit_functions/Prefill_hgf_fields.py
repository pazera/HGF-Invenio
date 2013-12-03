import os, re
global sysno,rn
#,curdir
from pprint import pprint

from invenio.config import * #(local-conf)
from invenio.search_engine import get_record, perform_request_search
from invenio.websubmitadmin_dblayer import get_details_and_description_of_all_fields_on_submissionpage
from invenio.websubmit_functions.Websubmit_Helpers_hgf import write_json,\
							write_all_files, \
							write_file, \
							remove_file, \
							write_done_file, \
							read_file, \
							read_json, \
							check_field_exists, \
							wash_db_record_dict, \
							get_autosuggest_keys, \
							add_non_json_fields
							
							
try: import jsonge
except ImportError: import simplejson as json

def handle_url(curdir):
	if check_field_exists(curdir,"hgf_8564_"): 
		remove_file(curdir,"hgf_8564_u")
		
		jsondict_list = read_json(curdir,"hgf_8564_")
		#only one URL can be submitted/modified. bibedit urls die ;)
		for i in jsondict_list:
			if not i.has_key("u"): continue # no subfield u detected
			if CFG_SITE_URL in i["u"]: continue # skip internal file
			write_file(curdir,"hgf_8564_u",i["u"])
			remove_file(curdir,"hgf_8564_")
			return # write only one URL
	if check_field_exists(curdir,"hgf_8564_u"):
		text = read_file(curdir,"hgf_8564_u")
		if CFG_SITE_URL in text: remove_file(curdir,"hgf_8564_u") #skip internal file
		
def handle_date(curdir,fielddate,sdate,edate):
	"""preprocessing date into 245$f
	fielddate can be hgf_245__f, hgf_1112_d
	sdate: hgf_245__fs or hgf_1112_dcs
	edate: hgf_245__fe or hgf_1112_dce
	"""
	if not check_field_exists(curdir,fielddate): return
	date = read_file(curdir,fielddate)
	try: dat1,dat2 = date.split(" - ")
	except: return
	if dat1 != "": write_file(curdir,sdate,dat1)
	if dat2 != "": write_file(curdir,edate,dat2)
	  			

def write_mod_doctype(curdir):
	"""write mod_doctype file to automatically connect to modification page"""
	#TODOD: do we need this function ???
	doctype = read_file(curdir, 'doctype') # in inital dir, so avoid a global
	mod_doctype_path = os.path.join(curdir,"mod_"+doctype)
	mod_file = open(mod_doctype_path,"w")
	tuple_fields = get_details_and_description_of_all_fields_on_submissionpage(doctype, "SBI", 1)
	for _tuple in tuple_fields:
		field = _tuple[0]
		if field in ["hgf_start","hgf_end","hgf_master"]: continue
		mod_file.write( field + "\n")
	mod_file.close()

def prefill_vdb_relevant(curdir):
	if not check_field_exists(curdir,"hgf_980__"): return
	text = read_file(curdir,"hgf_980__")
	if (('VDBRELEVANT' in text) or ('"VDB"' in text) or ('VDBINPRINT' in text)): value = "yes"
	else: value = "no"
	write_file(curdir,"hgf_vdb",value)
	if 'MASSMEDIA' in text: #prefill Massmedia 
		write_file(curdir,"hgf_massmedia","yes")
		
		
def handle_institutes_for_modify(curdir):
	"""in case of non-vdb entry we do not have 9201_, but the institutes are stored in 980 as collections. so, prefill the 9201_ from 980"""
	_980 = read_json(curdir,"hgf_980__")
	jsondict_9201 = []
	if check_field_exists(curdir,"hgf_9201_"):
		jsondict_9201 = read_json(curdir,"hgf_9201_")
	if jsondict_9201 == []:
		
		inst_dict = {"9201_":[]}
		for _dict in _980: 
			if not "a" in _dict.keys(): continue
			if len(perform_request_search(p='id:"' + _dict["a"] +'"' ,cc='Institutes')) < 1 : continue #make sure institute exists
			inst_dict["9201_"].append({"0":_dict["a"]})
		write_json(curdir,"hgf_9201_",inst_dict["9201_"])					
		
def prefill_245(curdir):
	"""prefill 245__a and 245__f as simple input fields. only 245__h (publication form) into 245__"""
	jsonlist = read_json(curdir,"hgf_245__")
	pubforms = []
	for jsondict in jsonlist:
		if jsondict.has_key("h"): 
			pubformnames = jsondict["h"].split(",") #split multiple pubforms
			for i,pubform in enumerate(pubformnames): pubforms.append({"h":pubform,"x":i}) 
		for key in jsondict.keys(): #we have some Input fields
			filename = "hgf_245__" + key
			# encode jsondict[key] to utf-8 to handle utf-chars.
			# TODO Tomek, why does it seem that we need this only here and
			# not for any other field?
			write_file(curdir,filename,jsondict[key].encode('utf-8'))
	write_json(curdir,"hgf_245__",pubforms)
	
def prefill_0247(curdir):
	"""prefill URN, Patent"""
	if check_field_exists(curdir,"hgf_0247_"): #json structure
		jsonlist = read_json(curdir,"hgf_0247_")
		for jsondict in jsonlist:
			if not jsondict.has_key("2"): continue
			if jsondict["2"] == "Patent":
				write_file(curdir,"hgf_0247_a2pat",jsondict["a"])
			elif jsondict["2"] == "URN":	
				write_file(curdir,"hgf_0247_a2urn",jsondict["a"])
	
	if check_field_exists(curdir,"hgf_0247_2"):
		if check_field_exists(curdir,"hgf_0247_a"):
			subfield_2 = read_file(curdir,"hgf_0247_2")
			subfield_a = read_file(curdir,"hgf_0247_a")
			if subfield_2 == "Patent":
				write_file(curdir,"hgf_0247_a2pat",subfield_a)
			elif subfield_2 == "URN":
				write_file(curdir,"hgf_0247_a2urn",subfield_a)	
	
def prefill_gender(curdir):
	"""prefill gender. normally the radio,checkboxes are prefilled by the Create_modify_interface_hgf, but that field is part of hgf_1001_ technical field, which is by default not a checkbox or radio botton"""
	if not check_field_exists(curdir,"hgf_1001_"): return # no author
	jsonlist = read_json(curdir,"hgf_1001_")
	
	for jsondict in jsonlist: # there can be only one first author --> len(jsonlist ==1)
		if not jsondict.has_key("g"): continue
		write_file(curdir,"hgf_1001_g",jsondict["g"])
		
		#delete gender information from technical field and store info in 1001_g
		del jsondict["g"]
		write_json(curdir,"hgf_1001_",[jsondict])
		
def Prefill_hgf_fields(parameters, curdir, form, user_info=None):
	"""extract all information from DB-record as json dict and write files into curdir"""
	# record_dict = get_record(sysno) #get record
	record_dict = get_record(read_file(curdir, 'SN')) #get record
	json_dict = wash_db_record_dict(record_dict) #create nice json dictionary
	json_dict = add_non_json_fields(json_dict) #add single input fields
	write_all_files(curdir,json_dict) # write all values to files
	write_done_file(curdir) #write done file--> cheat invenio
	prefill_245(curdir)
	prefill_0247(curdir)
	prefill_gender(curdir)
	handle_url(curdir)
	handle_date(curdir,"hgf_245__f","hgf_245__fs","hgf_245__fe")
	handle_date(curdir,"hgf_1112_d","hgf_1112_dcs","hgf_1112_dce")
	write_mod_doctype(curdir)
	prefill_vdb_relevant(curdir)
	handle_institutes_for_modify(curdir)
	#os.system("cp %s/hgf_9201_ %s/out" %(curdir,curdir))
	
if __name__ == "__main__":
	pass
	curdir = os.getcwd()
	doctype = "journal"
	record_dict = get_record("110") #get record
	#pprint(record_dict)
	json_dict = wash_db_record_dict(record_dict) #create nice json dictionary
	json_dict = add_non_json_fields(json_dict)
	#pprint(json_dict)
	write_all_files(curdir,json_dict) # write all values to files
	stop
	#prefill_245()
	#prefill_0247()
	#delete_for_autosuggest_fields()
	#write_done_file() #write done file--> cheat invenio
	#handle_url()
	#handle_date()
	#write_mod_doctype()
