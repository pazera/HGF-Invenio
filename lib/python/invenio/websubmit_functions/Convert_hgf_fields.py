import os,re,datetime
from invenio.config import *
from invenio.websubmit_config import CFG_WEBSUBMIT_COPY_MAILS_TO_ADMIN
from invenio.websubmit_config import InvenioWebSubmitFunctionError
from invenio.websubmit_functions.Create_hgf_record_json import washJSONinput
from invenio.webgroup_dblayer import get_groups
from invenio.search_engine import get_fieldvalues,\
									perform_request_search, \
									print_record


from invenio.access_control_config import CFG_EXTERNAL_AUTH_DEFAULT
from invenio.mailutils import send_email

from invenio.websubmit_functions.Websubmit_Helpers_hgf import write_json,\
								read_json,\
								get_recordid,\
								write_file,\
								check_field_exists,\
								read_file, \
								get_usergroups, \
								clean_fields, \
								get_autosuggest_keys,\
								remove_file

### Always use simplejson here to make intersections of sets in
### insert_inst_into_980() work with Python 2.4 and Python 2.6

import simplejson as json



################# Helpfunctions ######################################


def handle_list_of_doctype_dict(doctype_dict,access=None,doctype=None,subtype=None):
	doctype_dict_list = []
	for dict in doctype_dict['I3367_']:
		d = dict
		if ((access == None) and (d["2"] != "PUB:(DE-HGF)")): continue #do not insert DINI-driver pof added doctypes
		try:
			if d['m'] == doctype:
				d['s'] = access
				d['b'] = doctype
				if subtype != '':
					d['x'] = subtype
		except:
			pass
		doctype_dict_list.append(d)
	return doctype_dict_list

def get_pubtype_info(doctype):
	"""call output format for publication types and return it as dictionary (json)"""
	# directly call the backend...
	query = '3367_:'+doctype
	res = perform_request_search(p=query, cc='PubTypes')

	# and return the first rec in JS for further processing
	if res == []: return {}
	
	text = print_record(res[0], 'js')

	jsontext = washJSONinput(text)
	jsondict = json.loads(jsontext, 'utf8')
	return jsondict

def add_reportdoctype(curdir,doctype, doctype_dict_list):
	"""adds a new 3367 doctype for internal report"""
	if not check_field_exists(curdir,"hgf_088__a"): return doctype_dict_list #no reportnumber
	if (doctype == "intrep" or doctype == "report"): return doctype_dict_list # we have already a report documenttype
	report_doctype_dict = get_pubtype_info("intrep")
	if report_doctype_dict == {}: return doctype_dict_list # no authority
	report_doctype_dict_list = handle_list_of_doctype_dict(report_doctype_dict)
	return doctype_dict_list + report_doctype_dict_list

def add_journaldoctype(curdir,doctype, doctype_dict_list):
	"""adds a new 3367 doctype for journal"""
	fields_set = set(["hgf_773__","hgf_773__t","hgf_440__","hgf_440__t"])
	files_set = set(os.listdir(curdir))
	intersection =  fields_set & files_set #only fields, which exists as files
	if len(intersection) == 0: return doctype_dict_list #no journal reference
	if ((doctype == "journal") or (doctype == "news")): return doctype_dict_list # we have already a journal documenttype or we have news, which should not gain an additional journal doctype
	report_doctype_dict = get_pubtype_info("journal")
	if report_doctype_dict == {}: return doctype_dict_list # no authority
	report_doctype_dict_list = handle_list_of_doctype_dict(report_doctype_dict)
	return doctype_dict_list + report_doctype_dict_list

def add_bookdoctype(curdir,doctype, doctype_dict_list):
	"""adds a new 3367 doctype for book"""
	if not check_field_exists(curdir,"hgf_29510a"): return doctype_dict_list #no book reference
	if (doctype == "book" or doctype == "contb" or doctype == "contrib"): return doctype_dict_list # we dont need additional book doctype
	report_doctype_dict = get_pubtype_info("book")
	if report_doctype_dict == {}: return doctype_dict_list # no authority
	report_doctype_dict_list = handle_list_of_doctype_dict(report_doctype_dict)
	return doctype_dict_list + report_doctype_dict_list

def add_procdoctype(curdir,doctype, doctype_dict_list):
	"""adds a new 3367 doctype for proc"""
	if not check_field_exists(curdir,"hgf_1112_a"): return doctype_dict_list #no proc reference
	if doctype == "proc": return doctype_dict_list # we have already a proc documenttype
	# we have a book + a conference entry,
	# this makes us a proceedings volume
	if doctype == "book":
		report_doctype_dict = get_pubtype_info("proc")
		if report_doctype_dict == {}: return doctype_dict_list # no authority
		report_doctype_dict_list = handle_list_of_doctype_dict(report_doctype_dict)
		return doctype_dict_list + report_doctype_dict_list
	return doctype_dict_list

def set_restriction(new_dict):
	"""set restriction into 5060_f depending on CFG_PUBLIC_COLLECTIONS"""
	# TODO cleanup!!!!
	if not "CFG_PUBLIC_COLLECTIONS" in globals(): return new_dict
	unrestricted_collections = CFG_PUBLIC_COLLECTIONS.strip().split(",") #institutes public collections
	if {"a":"UNRESTRICTED"} in new_dict: return new_dict #already in 980
	for entry in new_dict:
		if not entry.has_key("a"): continue
		if entry["a"] in unrestricted_collections:
			new_dict.append({"a":"UNRESTRICTED"})
			return new_dict
	return new_dict

#################### END Help functions ################################


#################### Main functions ##################################
def insert_email(curdir):
	"""read SuE (emails of submitter) file and store it in 8560_f"""
	if not check_field_exists(curdir,"SuE"): return
	email = read_file(curdir,"SuE")
	write_file(curdir,"hgf_8560_f",email)

def insert_date(curdir,fielddate,sdate,edate):
	"""preprocessing date into 245$f
	fielddate can be hgf_245__f, hgf_1112_d
	sdate: hgf_245__fs or hgf_1112_dcs
	edate: hgf_245__fe or hgf_1112_dce
	"""
	if check_field_exists(curdir,sdate):
		hgf_sdate = read_file(curdir,sdate)
	else: hgf_sdate = ""
	if check_field_exists(curdir,edate):
		hgf_edate = read_file(curdir,edate)
	else: hgf_edate = ""
	if (hgf_sdate == "" and hgf_edate == "" ): return ""
	else: datestring = hgf_sdate + " - " + hgf_edate
	write_file(curdir,fielddate,datestring)
	remove_file(curdir, sdate)
	remove_file(curdir, edate)

def insert_reportnr(curdir):
	"""preprocessing of reportnumber"""
	rn = read_file(curdir,"rn")
	write_file(curdir,"hgf_037__a",rn)

def insert_webyear(curdir):
	"""set web year (Wissenschaftlicher Ergebnis Berichtsjahr)
	This function has to be called after insert_date function"""
	try:
		recid = int(get_recordid(curdir))
	except:
		return #when do we get this exception???
	orig_record_980 = get_fieldvalues(recid,'980__a') #create_hgf_collection was alreay active at this step and changed 980-field, so we have to get the original collections of the record from database
	if "VDB" in orig_record_980: return # do not change web_year after it was released by library (collection tag VDB)
	web_year = None
	current_year = str(datetime.datetime.now().year)
	if check_field_exists(curdir,"hgf_260__c"): # publication_year exists
		pub_year = read_file(curdir,"hgf_260__c")
		if pub_year == current_year: web_year = pub_year # publication year is current system year --> set web-year
	else:
		if check_field_exists(curdir,"hgf_245__f"): # check thesis end_date
			date = read_file(curdir,"hgf_245__f") #insert_date function has already been executed
			sdate,edate = date.split(" - ")
			if ((current_year in edate) or (current_year in sdate)): web_year = current_year # ending year of thesis is current system year --> set web-year
		if check_field_exists(curdir,"hgf_1112_d"): # check conf end_date
			date = read_file(curdir,"hgf_1112_d")
			sdate,edate = date.split(" - ")
			if ((current_year in edate) or (current_year in sdate)): web_year = current_year # ending year of conference is current system year --> set web-year

	if web_year: #write web_year
		write_file(curdir,"hgf_9141_y",web_year)


def insert_3367(curdir):
	"""get doctype from authorities and create 3367 and set our ddoctypes into 980 """
	doctype = read_file(curdir,"doctype")
	access = read_file(curdir,"access") #submission id
	subtype = ''
	try:
		# Check if we have a refinement of the doctype. Usually we have
		# this only for talks which could be "Invited" or whatever. If so,
		# add it to 3367_$x
		subtype = read_file(curdir,"hgf_3367_x")
	except:
	  # Usually, we do not have refinements.
		pass
	doctype_dict = get_pubtype_info(doctype)
	if doctype_dict == {}: 
		doctype_dict_list = [{"m":doctype}]   #no authority
	# Run over the dictionary and build up a list of all document types.
	# Note that not all document types have to be hgf-types, they may as
	# well stem from other vocabularies (DINI/DRIVER...)
	else:
		doctype_dict_list = handle_list_of_doctype_dict(doctype_dict,access,doctype,subtype)
		doctype_dict_list = add_reportdoctype(curdir,doctype, doctype_dict_list) #add intrep doctype
		doctype_dict_list = add_journaldoctype(curdir,doctype, doctype_dict_list) #add journal doctype
		doctype_dict_list = add_bookdoctype(curdir,doctype, doctype_dict_list) #add book doctype
		doctype_dict_list = add_procdoctype(curdir,doctype, doctype_dict_list) #add proc doctype
	if check_field_exists(curdir,"hgf_980__"):
		list_980 = read_json(curdir,"hgf_980__")

	else: list_980 = []
	# Only add our own doctypes to 980 (ie collections and not DINI/DRIVER)
	for dict in doctype_dict_list:
		try:
			if {"a":dict["m"]} in list_980: continue
			list_980.append({"a":dict["m"]})
		except:
			pass
	write_json(curdir,"hgf_980__",list_980)
	write_json(curdir,"hgf_3367_",doctype_dict_list)


def handle_245(curdir):
	"""245__a: title and 245__f:date  -->text input fields
	 245__h:publication form --> autosuggest
	 We need to read in 245__ (if exists) and add 245__a and 245__f in json format
	"""
	date,title = "",""
	# Title is special: we have non-structured input fields by default
	# where $f (date) needs a special handling plus we have a structured
	# input field from the possible token input of media type (AC's
	# request) => we have to assemble the structured field from it's
	# parts, and then re-store it as structure to a file, then the
	# follwoing workflow can transparently handle it as if it was passed
	# by a structure in the first place.


	# Get unstructured stuff
	if check_field_exists(curdir,"hgf_245__a"): title = read_file(curdir,"hgf_245__a")
	if check_field_exists(curdir,"hgf_245__f"): date = read_file(curdir,"hgf_245__f")

	# Initialize the structure
	jsondict = {}
	jsondict['245__'] = {}
	dict = {}
	# Try to get what we have already in the structure as such
	if check_field_exists(curdir,"hgf_245__"):
		jsondict = read_json(curdir,"hgf_245__")
	# in case of multiple publication forms (???, should be non repeatable, but just in case: create seperated comma string)
	pubforms = []
	for pubform in jsondict:
		if 'h' in pubform:
			pubforms.append(pubform["h"])
	pubstring = ", ".join(pubforms)
	if pubstring == "": jsondict = {}
	else: jsondict = {"h":pubstring}
	# Add unstructured fields, if they exist
	if not title == "": jsondict["a"] = title
	if not date  == "": jsondict["f"] = date
	# Write the full structured file
	write_json(curdir,"hgf_245__",jsondict)

def handle_0247(curdir):
	""" Handle persistend identifiers in 0247_. This implies to set $2
	to source and $a to value. only in case of user input

	Note: if we get new PIDs that should be handled we need to adopt
	this function!"""

	if check_field_exists(curdir,"hgf_0247_"):
		listdict_ = read_json(curdir,"hgf_0247_")

	else: listdict_ = []

	if check_field_exists(curdir,"hgf_0247_a2pat"): # Patent
		text = read_file(curdir,"hgf_0247_a2pat")
		listdict_.append({"2":"Patent","a":text})
	if check_field_exists(curdir,"hgf_0247_a2urn"): # URN
		text = read_file(curdir,"hgf_0247_a2urn")
		listdict_.append({"2":"URN","a":text})
	if check_field_exists(curdir,"hgf_773__a"):     # store DOI in both 773__ and in 0247, this is an input field
		text = read_file(curdir,"hgf_773__a")
		listdict_.append({"2":"doi","a":text})
	if (not check_field_exists(curdir,"hgf_773__a") and check_field_exists(curdir,"hgf_773__")): # doi can be stored in 773__ as json array
		dict_773 = read_json(curdir,"hgf_773__")
		for ent in dict_773: #more then 1 DOI
			if not "a" in ent.keys(): continue
			listdict_.append({"2":"doi","a":ent["a"]})

	if listdict_ == []: return

	new_listdict = []
	for dict in listdict_:
		if dict in new_listdict: continue # remove double entries
		new_listdict.append(dict)
	write_json(curdir,"hgf_0247_",new_listdict)

	#Insert DOI into 773__a only in case no 773__a or 773 json array exist
	if check_field_exists(curdir,"773__a"):     return #we have a 773__a

	if check_field_exists(curdir,"773__"):
		listdict_773 = read_json(curdir,"773__")
		for ent in listdict_773:
			if ent.has_key("a"): return # we have a 773__a

	for ent in new_listdict:
		if not ent.has_key("2"):     continue
		if not (ent["2"] == "doi"):  continue
		# map doi into 773__a

		# write DOI in 773__a if we do not yet have one.
		# in case of multiple DOIs the first one will win <--> we cannot
		# write the 773__ because we do not know if other 773__* fields
		# has been inputted and to which belongs the DOI. TODO!
		write_file(curdir,"hgf_773__a",ent["a"])

	return

def handle_1001(curdir):
	"""add gender to 1001_ technical field:
		1001_ contains a list of a single dict with the name of the first
		author. gender should be applied to that one (we use gender only
		for phd-like entries), so we add it to the end of the dict.

		NOTE: for further processing the newly written technical field
		must not contain a real JSON structure, but again only this list
		of a single hash.
	"""
	if not check_field_exists(curdir,"hgf_1001_g"): return  # no gender set

	if check_field_exists(curdir,"hgf_1001_"):
		jsondict = read_json(curdir,"hgf_1001_")
		gender = read_file(curdir,"hgf_1001_g")
		jsondict[0]["g"] = gender            # 100 contains only one person
		write_json(curdir,"hgf_1001_",jsondict)

def extract_user_institutes(dict_key,user_groups):
	"""extract institutes of user"""
	user_insts = []
	for ugroup in user_groups:
	#TODO check multiple authorization methods
		inst_id = ugroup.replace(' ['+CFG_EXTERNAL_AUTH_DEFAULT+']', '')
		if not len(perform_request_search(p='id:"' + inst_id +'"' ,cc='Institutes')) >0 : continue #make sure institute exists
		if {dict_key: inst_id} in user_insts: continue #prevent double entry
		user_insts.append({dict_key:inst_id})
	return user_insts

def insert_inst_into_980(curdir,uid):
	"""collection handling for institutes"""
	user_groups = get_usergroups(uid)
	if check_field_exists(curdir,"hgf_9201_"):
		if read_file(curdir,"hgf_9201_") == "[]": remove_file(curdir,"hgf_9201_") # delete file in case of empty sequence! TODO: this should not happen and has to be fixed in hgfInstitutes.js

	if not check_field_exists(curdir,"hgf_9201_"): #make sure that we have at least one institute
		if str(uid) == "1": return #do not add institutes for admin
		user_insts = extract_user_institutes("0",user_groups)
		if user_insts == []:
			email_txt = "%s is not assigned to any institute. This email was generated from Covert_hgf_fields and function insert_inst_into_980" %get_recordid(curdir)
			send_email(CFG_SITE_ADMIN_EMAIL, CFG_SITE_ADMIN_EMAIL, "ERROR: no institute assigned", email_txt,header="",html_header="")
			return #this should not happen!
		jsondict = user_insts   #add institute even if no institute chosen to be inserted into 980
	else:
		jsondict = read_json(curdir,"hgf_9201_")
	inst_list = []
	list_980 = read_json(curdir,"hgf_980__")
	
	for inst in jsondict:
		if {"a":inst["0"]} in list_980: continue
		inst_list.append({"a":inst["0"]})
	if inst_list == []: return
	list_980 += inst_list

	#check if users institut in 980, if not take it from user_info
	if str(uid) == "1": pass # no adding of institutes into 980  for admin
	else:
		str_list_980 = [str(i) for i in list_980] #convert list with dicts into list with str(dicts), because python sets use list with strings
		intersection_groups = set(str_list_980) & set(user_groups) # user institute not in 980 yet
		intersection_vdb = set(["{'a': 'VDB'}", "{'a': 'VDBRELEVANT'}","{'a': 'VDBINPRINT'}"]) & set(str_list_980) # not vdb_relevant

		if intersection_groups == set([]) and  intersection_vdb == set([]): # # prevent submitting vdb irrelevant stuff for another institute
			list_980 += extract_user_institutes("a",user_groups)
	write_json(curdir,"hgf_980__",list_980)


def handle_980(curdir):
	new_list = []
	list_980 = read_json(curdir,"hgf_980__")
	doctype = read_file(curdir,"doctype")

	old_index = list_980.index({"a":doctype})

	list_980.insert(0, list_980.pop(old_index)) #move original doctype to be first entry in 980 list, needed by invenio (more likely a bug)
	#remove double entries
	for _dict in list_980:
		if _dict in new_list: continue # remove double entries
		new_list.append(_dict)

	if check_field_exists(curdir,"hgf_delete"): new_list.append({"c":"DELETED"}) # user wants to delete this record
	new_list = set_restriction(new_list) # #set UNRESTRICTED if 980 collection appears in CFG_PUBLIC_COLLECTIONS
	write_json(curdir,"hgf_980__",new_list)

def add_FFT(curdir):
	"""
	!!!move_files_to_storage, move files to done have to be deleted from websubmit function!!!
	add FFT tag into record
	if this function is used: the functions stamp_uploaded_files should not be used in the websubmit anymore
	"""
	if not check_field_exists(curdir,"hgf_file"): return None # no file submitted
	fulltext_filename = read_file(curdir,"hgf_file")
	fulltext_path = os.path.join(curdir,"files","hgf_file",fulltext_filename)
	if not os.path.exists(fulltext_path): return None # no file named in hgf_file in files directory. something is wrong..
	if os.path.getsize(fulltext_path) == 0: #check file size
		#send email
		#first get the url record link
		if not check_field_exists(curdir,"SN"): return None # no recid-->something is wrong..
		recid = get_recordid(curdir)
		rec_url = CFG_SITE_URL + "/record/" + recid
		#create email
		email_txt = 'Dear Sir or Madam, \n\nAn empty file has been submitted for the record: %s\n\nProbably it was caused, because the file has been deleted from its directory before final submission into %s !!!\nIt is possible, that the record itself is not available, when this email was sent, but it should be processed within minutes. Once this is finished you may add the fulltext by accessing %s and using "modify record" link \n\n' %(rec_url,CFG_SITE_NAME,rec_url)
		email_subject = 'File submission incomplete!!!'
		#email check
		if check_field_exists(curdir,"SuE"): email_to = read_file(curdir,"SuE") # get email from submitter
		else: email_to = CFG_SITE_ADMIN_EMAIL # in case somehow no email of submitter exists, send email to admin

		send_email(CFG_SITE_ADMIN_EMAIL, email_to, email_subject, email_txt,copy_to_admin=CFG_WEBSUBMIT_COPY_MAILS_TO_ADMIN,header="",html_header="")
		return None #cancel file submission (the submitter has already been informed via email), the original submission will be processed.


	inst_dict_list = read_json(curdir,"hgf_9201_") #read in institutes
	inst_list = []
	restriction = "firerole: allow groups 'STAFF'" # staff is always
	# add the institutes id and append the external auth info as this
	# builds the actual group name we need to allow here.
	for inst in inst_dict_list:	restriction += ",'" + inst["0"] + ' ['+CFG_EXTERNAL_AUTH_DEFAULT+']' + "'"  # TODO: multiple authentifications
	filename = read_file(curdir,"hgf_file")
	file_path = os.path.join(curdir,"files","hgf_file",filename)
	if not check_field_exists(curdir,"rn"): return
	rn = read_file(curdir,"rn")

	#fill subfields for FFT
	fft_dict = {}
	fft_dict["a"] = file_path
	fft_dict["n"] = rn
	fft_dict["r"] = restriction
	write_json(curdir,"hgf_FFT__",fft_dict)


def check_9201(curdir):
	"""deleting 9201_* if  set in 980"""
	if not check_field_exists(curdir,"hgf_vdb"): return
	vdb_tag = read_file(curdir,"hgf_vdb")
	if vdb_tag == "no": os.system("rm -f %s/hgf_9201_*" %curdir)
	else: pass


def insert_thesis_note(curdir):
	"""insert 502__a --> thesis note:
	syntax: 'University, Doctype, Granted Year'
	insert 502__b (if possible)
	insert 655_7
	"""
	doctype = read_file(curdir,"doctype")
	jsondict = get_pubtype_info(doctype)
	if "I502__b" in jsondict.keys(): write_file(curdir,"hgf_502__b",jsondict["I502__b"])

	all_fields = True
	if check_field_exists(curdir,"hgf_502__c") and (check_field_exists(curdir,"hgf_260__c") or check_field_exists(curdir,"hgf_502__d")): pass
	else: all_fields = None

	if not "I502__a" in jsondict.keys(): all_fields = None
	if not all_fields: return #if some field is missing, do not create thesis_note
	norm_doctype = jsondict["I502__a"]
	if check_field_exists(curdir,"hgf_502__d"):
		thesis_note = read_file(curdir,"hgf_502__c") + ", " + norm_doctype + ", " + read_file(curdir,"hgf_502__d") # uese granted year
	else: thesis_note = read_file(curdir,"hgf_502__c") + ", " + norm_doctype + ", " + read_file(curdir,"hgf_260__c") #use publication year

	if "I650_7a" in jsondict.keys(): write_file(curdir,"hgf_650_7a",jsondict["I650_7a"].encode('utf-8'))
	if "I650_72" in jsondict.keys(): write_file(curdir,"hgf_650_72",jsondict["I650_72"])
	if "I650_70" in jsondict.keys(): write_file(curdir,"hgf_650_70",jsondict["I650_70"])

	write_file(curdir,"hgf_650_7x",norm_doctype)
	write_file(curdir,"hgf_502__a",thesis_note)


################ End main functions #############################################


def Convert_hgf_fields(parameters,curdir, form, user_info=None):
	"""converts institutional Fields (inserting of doctypes and collection tags(MAIL,EDITOR....)
	This function is used in modify and submit!!!"""
	global uid
	global uid
	userid = ''
	if user_info:
		userid = user_info['uid'] # don't mess with the globals
	else:
		userid = uid
	insert_email(curdir) # add email
	insert_date(curdir,"hgf_245__f","hgf_245__fs","hgf_245__fe") # convert date
	insert_date(curdir,"hgf_1112_d","hgf_1112_dcs","hgf_1112_dce") # convert conf date
	insert_reportnr(curdir) #insert reportnumber
	insert_webyear(curdir) #set web-year (Wissenschaftlicher Ergebnis Bericht)
	insert_3367(curdir) # insert doctype from authorities
	handle_245(curdir)  # take care of 245__a(text), 245__f(text), 245__h(autosuggest)
	handle_0247(curdir)
	handle_1001(curdir) # handle the $g subfield which is passed on as second input
                # do this /before/ cleaning the 1001_ field!

	surviving_fields = get_autosuggest_keys()
	# delete files from curdir--> hgf_9201_?*, only hgf_9201_ will survive
	for field in surviving_fields:
		clean_fields(curdir,"hgf_"+field)
	#following main functions have to be executed after clean_fields
	insert_inst_into_980(curdir,userid)
	handle_980(curdir) # make a nice json
	add_FFT(curdir) # add FFT tag for inserting fulltext files with restrictions
	check_9201(curdir)
	insert_thesis_note(curdir)

if __name__ == "__main__":
	curdir = os.getcwd()
	global uid
	uid=47
	Convert_hgf_fields(None, curdir, None, user_info=None)
    #add_FFT()
#	insert_email() # add email
#	insert_reportnr() #insert reportnumber
#	insert_3367() #insert doctype from authorities
#	handle_245()
#	clean_fields("hgf_9201_") #delete files from curdir--> hgf_9201_?*, only hgf_9201_ will survive
#	clean_fields("hgf_980__") #delete files from curdir

#	insert_inst_into_980()
#	handle_980()
#	check_9201()
#	handle_0247()
#	insert_thesis_note()

