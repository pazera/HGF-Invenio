import os, re
import datetime
import simplejson as json
from invenio.websubmitadmin_dblayer import get_docid_docname_alldoctypes
from invenio.webgroup_dblayer import get_groups
from invenio.search_engine import perform_request_search


from invenio.websubmit_functions.Websubmit_Helpers_hgf import write_json,\
							 	read_json,\
								washJSONinput,\
								write_file,\
								read_file,\
								check_field_exists,\
								get_technical_collections,\
								get_user


def write_980(curdir,collection_list):
	write_json(curdir,"hgf_980__",collection_list)

def filter_980(curdir):
	if not check_field_exists(curdir,"hgf_980__"): return []
	coll_list = read_json(curdir,"hgf_980__")
	doctype_tuples = get_docid_docname_alldoctypes()
	doctype_collections = []
	[doctype_collections.append(tup[0]) for tup in doctype_tuples]
	filter_collections = doctype_collections + get_technical_collections()
	json_filter_collections = [{"a":collection} for collection in filter_collections]
	old_collections = []
	for coll in coll_list:
		if not coll.has_key("a"): continue #drop all "foreign" collections
		if coll in json_filter_collections: continue #drop workflow collections
		if len(perform_request_search(p='id:"' + coll["a"] +'"' ,cc='Institutes')) >0: continue #drop institutes
		old_collections.append(coll)
	return old_collections


def check_vdb_relevant(curdir,fieldname):
	if check_field_exists(curdir,fieldname): pass
	else: return None
	text = read_file(curdir,"hgf_vdb")
	if "yes" in text: return True
	else: return None

def is_user_released(user,tag_release,tag_vdb,collection_list):
	if ((user == "USER") and tag_release):
		collection_list.append({"a":"USER"})
		if tag_vdb: collection_list.append({"a":"VDBRELEVANT"})
	return collection_list

def is_user_not_released(user,tag_release,tag_vdb,collection_list):
	if ((user == "USER") and  not tag_release):
		collection_list.append({"a":"TEMPENTRY"})
		if tag_vdb: collection_list.append({"a":"VDBRELEVANT"})
	return collection_list

def is_editor_released(user,tag_release,tag_vdb,collection_list):
	if ((user == "EDITORS") and tag_release):
		collection_list.append({"a":"EDITORS"})
		if tag_vdb: collection_list.append({"a":"VDBINPRINT"})
	return collection_list

def is_editor_not_released(user,tag_release,tag_vdb,collection_list):
	if ((user == "EDITORS") and not tag_release):
		collection_list.append({"a":"EDITORS"})
		collection_list.append({"a":"TEMPENTRY"})
		if tag_vdb: collection_list.append({"a":"VDBRELEVANT"})
	return collection_list

def is_staff_released(user,tag_release,tag_vdb,collection_list):
	if ((user == "STAFF") and tag_release):
		if tag_vdb: collection_list.append({"a":"VDB"})
	return collection_list

def is_staff_not_released(user,tag_release,tag_vdb,collection_list):
	if ((user == "STAFF") and not tag_release):
		## collection_list.append({"a":"EDITORS"})
		## collection_list.append({"a":"TEMPENTRY"})
		## if tag_vdb: collection_list.append({"a":"VDBINPRINT"})
    # 
    # Staff presses Postpone button with the intention to send the
    # recrod back to the respecitve EDITORS ("there is something
    # wrong, have a look at it")
    # => 'Fake' a users submission, so this record shows up in the
    # usual revision list.
    #
		collection_list.append({"a":"USER"})
		if tag_vdb: collection_list.append({"a":"VDBRELEVANT"})
	return collection_list

def set_timestamp(curdir,uid):
	"""manage timestamp"""
	timestamp = datetime.datetime.now().isoformat()
	user = get_user(uid)
	if not check_field_exists(curdir,"hgf_961__x"): write_file(curdir,"hgf_961__x",str(timestamp)) # only in submit
	if user == "EDITORS": write_file(curdir,"hgf_961__i",str(timestamp)) # only if Editors finish & release
	if user == "STAFF": write_file(curdir,"hgf_961__z",str(timestamp)) # only if stuff finish & release
	write_file(curdir,"hgf_961__c",str(timestamp)) # in submit and modify
	os.system("cp %s/SuE %s/hgf_961__a" %(curdir,curdir)) #only in submit

def Create_hgf_collection(parameters, curdir, form, user_info=None):
	"""process collections by access role of the user
	This function is used in submit and modify!
	"""
	global uid
	userid = ''
	if user_info:
		userid = user_info['uid'] # don't mess with the globals
		user   = get_user(userid)
	else:
		userid = uid
		user = get_user(userid) # workflow collections belonging to user

	tag_release = check_field_exists(curdir,"hgf_release")# in case of no tag_release we have postpone
	tag_vdb = check_vdb_relevant(curdir,"hgf_vdb")	# vdb
	collection_list = []
	#the following functions can be matched only ones
	collection_list = is_user_released(user,tag_release,tag_vdb,collection_list)
	collection_list = is_user_not_released(user,tag_release,tag_vdb,collection_list)
	collection_list = is_editor_released(user,tag_release,tag_vdb,collection_list)
	collection_list = is_editor_not_released(user,tag_release,tag_vdb,collection_list)
	collection_list = is_staff_released(user,tag_release,tag_vdb,collection_list)
	collection_list = is_staff_not_released(user,tag_release,tag_vdb,collection_list)

	old_collections = filter_980(curdir)
	collection_list += old_collections
	if check_field_exists(curdir,"hgf_massmedia"): collection_list.append({"a":"MASSMEDIA"})
	write_980(curdir,collection_list)
	set_timestamp(curdir,userid)
#if __name__ == "__main__":
