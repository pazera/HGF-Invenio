#!/usr/bin/python
# Prerequists: 
#	Module configobj
# 	python version >= 2.3
# Creating submission and modification forms for hgf-institutes.
# All fields and collections are defined in the 'config.cfg'.
# 
# CFG_WEBSTYLE_TEMPLATE_SKIN has to be set (i.e. desy, gsi or fzj --> same name as in config.cfg. If not set --> take the default )
# 
# Execute:
# 	python process_confobj.py arg config.cfg
#
#	arg =  	-c	create all submission forms 
#		-d	delete all submission forms
#
from invenio.websubmitadmin_dblayer import *        #functions for inserting into database
from configobj import ConfigObj             #module for reading config-file
from invenio.config import * #(local-conf)
import os, sys, re

global arg 
global fieldlabels
arg = "" # delete (-d) / create(-c)
fieldlabels= [] # initialize list for fieldlables for css
	
##### Arguments and correct syntax ###
def check_args():
	"""check arguments"""
	args = sys.argv
	if len(args) != 3: 
		print "\nSyntax incorrect.\nCorrect Syntax: python process_confobj.py argument conffilename\n\nargument:\n  -d delete all created sbmcollections and submission forms\n  -c create sbmcollections and submission forms\n"
		return ""
	confilepath = args[2] #config-file
	global arg
	arg = args[1] # delete / create
	fieldlabels = [] # initialize list for fieldlables for css
	return confilepath 
######################################

################# config functions ##############
def read_conf(confilepath):
	"""read config-file and return config-dictionary"""
	if os.path.exists(confilepath): 
		config = ConfigObj(confilepath) 
		return config
	sys.exit("Confile: |%s| does not exist" %(confilepath))
	
def get_hgf_institute(config):
	"""get Variable cfg_hgf_institut from invenio-local.conf, if not set return default"""
	global inst	
	if ("CFG_WEBSTYLE_TEMPLATE_SKIN" in globals()):
		if arg == "-c": print "Creating websubmission masks for the Institute: %s" %(CFG_WEBSTYLE_TEMPLATE_SKIN)
		elif arg == "-d": print "Deleting websubmission masks for the Institute: %s" %(CFG_WEBSTYLE_TEMPLATE_SKIN)
		inst = CFG_WEBSTYLE_TEMPLATE_SKIN.lower()
		if inst in config.keys(): #inst_variable set in config.cfg
			if config[inst] == {}: # 
				warning("Only Variable %s is set in config.cfg. --> creating default masks!" %(inst))
				inst = "default"
		else:
			warning("no %s changes, because Variable %s not set in config.cfg --> creating default masks!" %(inst,inst))
			inst = "default"	#if global institutional variable set in local-conf, but not in config.cfg
	else:
		if arg == "-c":	warning("Variable CFG_WEBSTYLE_TEMPLATE_SKIN not found in invenio.local-conf. Creating default submission masks!")
		if arg == "-d":	warning("Variable CFG_WEBSTYLE_TEMPLATE_SKIN not found in invenio.local-conf. Deleting default submission masks!")
		inst = "default"
	return inst
	
def get_docname_from_schema(doctype,config):
	"""return pretty docname for doctype"""
	for coll in config["schema"].keys():
		for doc in config["schema"][coll].keys():
			if doctype == doc: return config["schema"][coll][doc]

def get_marccode(config,fieldname):
	"""return marccode of a specific field"""
	if fieldname in config["fielddesc"].keys(): 
		if  config["fielddesc"][fieldname][1] == "": return False 
		else: return config["fielddesc"][fieldname][1]
	else: return False
 	
def get_hidden_fields(config):
	"""return all hidden fields but not 980"""
	hidden_fields = []
	for field in config["fielddesc"].keys():
		if config["fielddesc"][field][1] == "980__a": continue
		if config["fielddesc"][field][2].lower() == "h": hidden_fields.append(field)
	return hidden_fields
	
def sort_hgf_fields(config,doctype,inst):
	"""order hgf_fields by config.cfg, but take institutional changes in order into account
	aware of: 
	in the config file we have 3 possibilioties to set the order
	1. config['order']
	2. config['default_form']
	3. institutional changes (i.e. config['fzj'])
	
	we have to take that 3 possibilities into account, when generating the order
	"""
	order = config["order"] # get all field defined under config['order'] (1.)
	order_index = 2
	default_set = config["default_form"]
	default_order = {} # dict with fields from default_form and proper order (2.)
	for k in (default_set.keys()):
		if k in order.keys(): #field in config["order"]
			default_order[k] = order[k]
		if k in default_set.keys() and default_set[k][order_index] !="-" : #field in config["default_form"] and not "-"
			default_order[k] = default_set[k][order_index] 
		
	if doctype in config[inst].keys(): #get the institutional changes (3.)
		inst_changes = config[inst][doctype]
	else:
		inst_changes = {}
	
	
	inst_order = {}
	for key in inst_changes.keys():
		if inst_changes[key] == "None":
			if key in default_order.keys(): #delete fields from institutional changes which are set "None" and in default_form
				del default_order[key]
			continue
		if inst_changes[key][order_index] == "-": #we take the default
			if key in default_order.keys(): pass #already assigned by default_order
			else: 
				if key in order.keys(): #get the order from config['order']
					inst_order[key] = order[key]
				else: warning("Please define the order (config['order']) for field %s in doctype: %s" %(key,doctype))
			continue
		inst_order[key] = inst_changes[key][order_index] #institutional changes			
		
	final_order = {}
	#get institutional changes in order
	max_score = max(map(int,default_order.values() + inst_order.values())) #get all order values as string, convert strings to int and get the max value
	for k in (default_order.keys() + inst_changes.keys()): 	
		if k in inst_changes.keys():
			if inst_changes[k] == "None": 
				continue
			if inst_changes[k][order_index] == "-":
				if k in default_order.keys():  #take the default_order
					final_order[k] = default_order[k]
				else: 
					if k in order.keys():
						final_order[k] = order[k]
					else:  #no default. sort this field to the end
						warning("The field %s in doctype: %s  is sorted to the end of the form" %(k,doctype))
						final_order[k] = max_score
						max_score +=1
			else: final_order[k] = inst_changes[k][order_index] #take order from institutional changes
			
		else: 
			final_order[k] = default_order[k] # take order from default_form
	
	final_order["hgf_end"] = max_score
	
	new_order = sorted(final_order.items(),key=lambda x: int(x[1])) #create list with tuples sorted by value
	hidden_fields = get_hidden_fields(config) #get hidden fields
	
	sorted_hgf_fields = []		
	for i in new_order:
		sorted_hgf_fields.append(i[0])
	
	# add all hidden fields
	for i in hidden_fields:
		if i in sorted_hgf_fields: continue
		sorted_hgf_fields.append(i)
	return sorted_hgf_fields	
################# End config functions ##############

################# Database help functions ################

def get_id_of_collection_name(collection_name):
	qstr = """SELECT id FROM sbmCOLLECTION """ \
	"""WHERE name=%s """ \
	"""LIMIT 1"""
	qres = run_sql(qstr, (collection_name,))
	try: return int(qres[0][0])
	except (TypeError, IndexError):return None

		
def get_fields_from_sbmfield(doctype):
	"""returns list of sbi-fields for doctype"""
	q = """SELECT fidesc FROM sbmFIELD where subname='SBI%s'""" %(doctype)
	return run_sql(q)		
	
def get_eltype_from_sbmfielddesc(hgf_field):
	"""returns element type for a specific fielddescriptor"""
	q = """SELECT type FROM sbmFIELDDESC where name='%s'""" %(hgf_field)
	return run_sql(q)[0][0]		

def get_field_from_sbmfielddesc(hgf_field):
	"""returns field for a specific fielddescriptor"""
	q = """SELECT * FROM sbmFIELDDESC where name='%s'""" %(hgf_field)
	return run_sql(q)[0]


def update_eltype_in_sbmfielddesc(hgf_field,eltype,modification_text,fidesc):
	q = """UPDATE sbmFIELDDESC SET type='%s',modifytext='%s',fidesc='%s' where name='%s' """ %(eltype,modification_text,fidesc,hgf_field)
	run_sql(q)		
			
				
def insert_parameters(doctype,inst):
	""" inserting parameters into sbmPARAMETER
	Warning: Do NOT clone parameters from DEMO-form!
	"""
	#TODO: do we need all following parameters (i.e. bibconvert templates)??
	params = {"authorfile":"hgf_1001_a","edsrn":"rn","emailFile":"SuE","fieldnameMBI":"mod_%s" %(doctype),"newrnin":"","status":"ADDED","titleFile":"hgf_245__a","createTemplate":"genecreate.tpl","sourceTemplate":"gene.tpl","modifyTemplate":"genemodify.tpl","documenttype":"fulltext","iconsize":"180>,700>","paths_and_suffixes":'{"hgf_file":""}',"rename":"<PA>file:rn</PA>","autorngen":"Y","counterpath":"lastid_%s_<PA>yy</PA>" %(inst),"rnformat":"%s-<PA>yy</PA>" %(inst.upper()),"nblength":"5","rnin":"combo%s" %(inst),"yeargen":"AUTO","files_to_be_stamped":"hgf_file","latex_template":"demo-stamp-left.tex","latex_template_vars":"{'REPORTNUMBER':'FILE:rn' ,'DATE':'FILE:hgf_245__f'}","stamp":"first"}
	for key in params.keys(): insert_parameter_doctype(doctype, key, params[key])
						
def insert_repnr_fielddesc(inst):
	"""rn_doctype #insert modification reportnumber for doctype into sbmFIELDDESC"""
	elname = "rn"
	elmarccode = "037__a"
	eltype = "I"
	elsize = "30"
	elrows = ""
	elcols = ""
	elmaxlength = ""
	elval = "%s-<YYYY>-?????" %(inst.upper())
	elfidesc = "" 
	elmodifytext = ""
	insert_element_details(elname, elmarccode, eltype, elsize, elrows, elcols, elmaxlength, elval, elfidesc, elmodifytext) # insert into sbmFIELDDESCR	
	
def insert_fielddesc(element, hgf_field):
	"""insert marc-fields into table sbmFIELDDESC
	@elements: list of all values of a field
	alephcode,marccode,type,size,rows,cols,maxlength,val,fidesc,cd,md,modifytext,fddfi2,cookie
	"""
	elname = hgf_field
	elmarccode = element[1]
	eltype = element[2]
	elsize = element[3]
	elrows = element[4]
	elcols = element[5]
	elmaxlength = element[6]
	elval = element[7]
	elfidesc = element[8]
	elmodifytext = element[11]
	insert_element_details(elname, elmarccode, eltype, elsize, elrows, elcols, elmaxlength, elval, elfidesc, elmodifytext) # insert into sbmFIELDDESCR
		
def delete_field_from_submissionpage(doctype, action, pagenum):
	q = """DELETE FROM sbmFIELD WHERE subname=%s AND pagenb=%s"""
	run_sql(q, ("""%s%s""" % (action, doctype), pagenum))	
	
def delete_mbifielddescr(doctype):
	q = """DELETE FROM sbmFIELDDESC WHERE name='mod_%s'""" %(doctype)
	run_sql(q)
	q = """DELETE FROM sbmFIELDDESC WHERE name='rn_%s'""" %(doctype)
	run_sql(q)	
	q = """DELETE FROM sbmFIELDDESC WHERE name='mrn_%s'""" %(doctype)
	run_sql(q)	
		
def delete_collection_from_fielddesc(doctype):
	q = """DELETE FROM sbmFIELDDESC WHERE name='col_%s'""" %(doctype)
	run_sql(q)	


def delete_hgf_field_from_fielddesc(hgf_field):
	q = """DELETE FROM sbmFIELDDESC WHERE name='%s'""" %(hgf_field)
	run_sql(q)	
################### End database help functions ############
		
################### help functions #########################

def debug(a):
	print "debug:", a

def warning(a):
	print "*****WARNING: ", a
		
def replace_null(a):
	if a == "NULL": return ""
	else: return a
 
def merge_sbmfield(doctype,config,inst,field,order_index):
	"""make institutianl changes in fields"""
	sbmfield = [field]
	field_parts = config[inst][doctype][field]
	for i in range(len(field_parts)): #length should be 4
		if field_parts[i] == "-":
			if i==2: #order
				part = order_index
			else:
				if field in config["default_form"].keys():
					if i >= len(config["default_form"][field]): part = "" #reffering to a default_form field, which is not defined 
					else: part = config["default_form"][field][i] #take the default if "-"
				else: part = ""
				if part == "-": 
					part = "" #should not happen
					warning("field: %s is not defined in default_form and refers to '-'" %field)
		else: part = field_parts[i]
		sbmfield.append(part)
	return sbmfield
		
def generate_css(fieldlabels,inst):
	"""create and write a list with all classes defined in the html representation of the fields.
	fieldlabels: list with all span-fieldlabels"""
	classes_unique = []
	for fieldlabel in fieldlabels:
		if not "class" in fieldlabel: continue
		class_lists = re.findall(r'class=\"([^\"]*)\"',fieldlabel)
		for cl in class_lists:
			classes = cl.split()
			for clas in classes:
				if clas in classes_unique:
					continue
				classes_unique.append(clas)
	classes_unique.sort()
	write_css(classes_unique,inst)
	
def write_css(css_classes,inst):
	"""write css-stylesheet file"""
	cssfile = os.path.join(os.getcwd(),"css_file_" + inst)
	classtring = ""
	for clas in css_classes: classtring += "." + clas + "{}\n"
	wd = open(cssfile,"w")
	wd.write(classtring)
	wd.close()
	
def read_javascript_includes():
	"""return javascript includes for autosuggest as text"""
	if "CFG_PREFIX" in globals(): 
		js_filepath = os.path.join(CFG_PREFIX,"var/www/js/jquery/jquery-lib.html")
		if os.path.exists(js_filepath):
			f = open(js_filepath,"r")
			js_text = f.read()
			f.close()
			return js_text
		else: 	
			warning("no javascipt file included %s" %js_filepath)
			return None
	else: 	
		warning("CFG_PREFIX not set. no javascript includes")
		return None
		
def get_groupclass(fieldlevel):
	"""fieldlevel can be now m1,m2,m3, this changed due to handle mandatory field groups. """
	if len(fieldlevel) > 1: return fieldlevel.upper()
	else: return "" 
			
###################End help functions #####################


################### main functions #########################

def build_or_remove_fielddesc(config):
	"""build or delete fielddescriptors"""
	for hgf_field in config["fielddesc"].keys():
		if arg == "-d": delete_hgf_field_from_fielddesc(hgf_field)
		if arg == "-c":
			values = config["fielddesc"][hgf_field]
			values = map(replace_null, values) #replace NULL by ""
			insert_fielddesc(values, hgf_field)
			
def build_or_remove_schema(config):
	"""Build or delete submission-collections"""
	sbmcollections = config["schema"].keys()
	for sbmcoll in sbmcollections:
		#if not sbmcoll == "Thesis": continue
		if arg == "-d": #deleting
			collection_id = get_id_of_collection_name(sbmcoll)
			delete_submission_collection_details(collection_id) #sbmCOLLECTION
			delete_submission_collection_from_submission_tree(collection_id)#sbmCOLLECTION_sbmCOLLECTION
			
		if arg == "-c": #creating
			id_son = insert_submission_collection(sbmcoll) #sbmCOLLECTION
			## get the maximum catalogue score of the existing collection children:
			max_child_score = \
			get_maximum_catalogue_score_of_collection_children_of_submission_collection(0) # 0: highest collection 
			## add it to the collection, at a higher score than the others have:
			new_score = max_child_score + 1
			insert_collection_child_for_submission_collection(0, id_son, new_score) #sbmCOLLECTION_sbmCOLLECTION
			collection_id = get_id_of_collection_name(sbmcoll)
		doctypes = config["schema"][sbmcoll]
		for doctype in doctypes:
			if arg == "-c":
				## insert the submission-collection/doctype link:
				## get the maximum catalogue score of the existing doctype children:
				max_child_score = get_maximum_catalogue_score_of_doctype_children_of_submission_collection(collection_id)
				## add it to the new doctype, at a higher score than the others have:
				new_score = max_child_score + 1
				insert_doctype_child_for_submission_collection(collection_id, doctype, new_score) #sbmCOLLECTION_sbmDOCTYPE 
			elif arg == "-d": delete_doctype_children_from_submission_collection(collection_id) #sbmCOLLECTION_sbmDOCTYPE
		
		
def build_or_remove_doctypes(config,inst):
	"""build doctypes for submission collection"""
	doctypes = config[inst].keys() #reading in config file, if Variable hgf_institute --> take defined doctypes by institute, else take the default
	b1 = set(doctypes) #all inst_doctypes
	b2 = set(config["default"].keys()) #all default_doctypes
	diff = b2.difference(b1) # doctypes which are in default but not in institutional changes 
	if not diff == []: doctypes = doctypes + list(diff) # loop default doctypes at the end	
	for doctype in doctypes:
		if doctype == "specialfields":continue
		docname = get_docname_from_schema(doctype,config)
		doctypedescr = "This is a %s submission form." %(docname)
		if arg == "-d":
			print "deleting Doctype: %s" %(doctype)
			delete_all_functions_foraction_doctype(doctype, "SBI") #sbmFUNCTIONS
			delete_all_functions_foraction_doctype(doctype, "MBI") #sbmFUNCTIONS
			delete_doctype(doctype) #sbmDOCTYPE
			delete_all_submissions_doctype(doctype) #sbmIMPLEMENT
			delete_all_parameters_doctype(doctype) #sbmPARAMETERS
			delete_field_from_submissionpage(doctype, "SBI", "1") #sbmFIELD
			delete_field_from_submissionpage(doctype, "MBI", "1") #sbmFIELD
			delete_mbifielddescr(doctype) #sbmFIELDDESC
			delete_collection_from_fielddesc(doctype) #sbmFIELDDESC
			continue
		if (get_number_doctypes_docid(doctype) >0): continue #check if doctype already exists
		if doctype in diff: 
			print "creating Doctype: %s (default)" %(doctype)
			inst = "default" # this can be done, because we loop over default doctypes at the end
		else: print "creating Doctype: %s" %(doctype)
		 
		insert_doctype_details(doctype,docname,doctypedescr) #create doctype
		
		numrows_function = get_number_functions_action_doctype(doctype="DEMOTHE", action="SBI")
		
		#clone_functions_foraction_fromdoctype_todoctype("DEMOTHE", doctype, "SBI") #clone actions/functions from DEMOTHE	
		#clone_functions_foraction_fromdoctype_todoctype("DEMOTHE", doctype, "MBI") #clone actions/functions from DEMOTHE	
		
		#SBI without cloning --add function parameter
		add_function_parameter("Report_Number_Generation", "autorngen")
		add_function_parameter("Report_Number_Generation", "counterpath")
		add_function_parameter("Report_Number_Generation", "edsrn")
		add_function_parameter("Report_Number_Generation", "nblength")
		add_function_parameter("Report_Number_Generation", "rnformat")
		add_function_parameter("Report_Number_Generation", "rn")
		add_function_parameter("Report_Number_Generation", "yeargen")
		
		add_function_parameter("Print_Success", "edsrn")
		add_function_parameter("Print_Success", "newrnin")
		add_function_parameter("Print_Success", "status")
		
		add_function_parameter("Mail_Submitter_hgf", "authorfile")
		add_function_parameter("Mail_Submitter_hgf", "edsrn")
		add_function_parameter("Mail_Submitter_hgf", "emailFile")
		add_function_parameter("Mail_Submitter_hgf", "newrnin")
		add_function_parameter("Mail_Submitter_hgf", "status")
		add_function_parameter("Mail_Submitter_hgf", "titleFile")
		
		#MBI without cloning --add function parameter
		add_function_parameter("Get_Report_Number","edsrn")
		add_function_parameter("Get_Recid","record_search_pattern")
		add_function_parameter("Create_Modify_Interface_hgf", "fieldnameMBI")
		add_function_parameter("Send_Modify_Mail_hgf", "fieldnameMBI")
		add_function_parameter("Send_Modify_Mail_hgf", "addressesMBI")
		add_function_parameter("Send_Modify_Mail_hgf", "emailFile")
		add_function_parameter("Send_Modify_Mail_hgf", "sourceDoc")
		
		#SBI without cloning --insert function details
		insert_function_details("Create_Recid", "Creating Record-ID")
		insert_function_details("Report_Number_Generation", "Generate Report number")
		insert_function_details("Create_hgf_collection", "create workflow collections")
		insert_function_details("Convert_hgf_fields", "postprocessing of the record data. convert email,date,collections...")
		insert_function_details("Create_hgf_record_json", "create hgf record in json format")
		insert_function_details("Make_HGF_Record", "convert HGF-record into MARCxml")
		insert_function_details("Insert_Record", "insert record into database")
		insert_function_details("Print_Success", "inform the user about the successful submission")
		insert_function_details("Mail_Submitter_hgf", "mail to the submitter of the record")
	
		#MBI without cloning --insert function details
		insert_function_details("Get_Report_Number", "get the report number")
		insert_function_details("Get_Recid", "get the record-id")
		insert_function_details("Is_Allowed2Edit", "check for modify permissions")
		insert_function_details("Prefill_hgf_fields", "prefill hgf fields in modify form")
		insert_function_details("Create_Modify_Interface_hgf", "new create modify interface function for hgf")
		insert_function_details("Insert_hgf_modify_record", "replace old record by new one completely")
		insert_function_details("Send_Modify_Mail_hgf", "replace old modify mail by new hgf mail")
		
		#SBI without cloning --insert function into websubmit steps
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Create_Recid", "1", "10")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Report_Number_Generation", "1", "20")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Create_hgf_collection", "1", "30")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Convert_hgf_fields", "1", "40")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Create_hgf_record_json", "1", "50")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Make_HGF_Record", "1", "60")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Insert_Record", "1", "70")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Print_Success", "1", "80")
		insert_function_into_submission_at_step_and_score(doctype, "SBI", "Mail_Submitter_hgf", "1", "90")
		
		#MBI without cloning --insert function into websubmit steps 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Get_Report_Number", "1", "10") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Get_Recid", "1", "20") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Is_Allowed2Edit", "1", "30") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Prefill_hgf_fields", "1", "40") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Create_Modify_Interface_hgf", "1", "50") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Get_Report_Number", "2", "10") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Get_Recid", "2", "20") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Is_Allowed2Edit", "2", "30") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Create_hgf_collection", "2", "40") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Convert_hgf_fields", "2", "50") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Create_hgf_record_json", "2", "60") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Make_HGF_Record", "2", "70") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Insert_hgf_modify_record", "2", "80") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Print_Success_MBI", "2", "90") 
		insert_function_into_submission_at_step_and_score(doctype, "MBI", "Send_Modify_Mail_hgf", "2", "100") 
		
		## add action in sbmIMPLEMENT for doctype
		#insert_submission_details_clonefrom_submission(doctype,"SBI","DEMOTHE")
		#insert_submission_details_clonefrom_submission(doctype,"MBI","DEMOTHE")
		
		# add action in sbmIMPLEMENT for doctype --without cloning 
		insert_submission_details(doctype, "SBI", "Y", "1", "1", "", "1", "1", "0", "")
		insert_submission_details(doctype, "MBI", "Y", "1", "2", "", "", "0", "0", "")
		
		## add sbmParameters 
		insert_parameters(doctype,inst)
		
		## create institutes defined fields
		create_mask(config,doctype,inst)
					
def create_user_defined_fielddesc(sbmfield,config,inst):
	"""create institutional defined fielddescriptor
	sbmfield: [fieldname,fielddesc,m/o,order,placeholder]
	element: alephcode,marccode,type,size,rows,cols,maxlength,val,fidesc,cd,md,modifytext,fddfi2,cookie	
	"""
	el_dict = {"alephcode":0,\
			"marccode":1,\
			"type":2,\
			"size":3,\
			"rows":4,\
			"cols":5,\
			"maxlength":6,\
			"val":7,\
			"fidesc":8,\
			"cd":9,\
			"md":10,\
			"modifytext":11,\
			"fddfi2":12,\
			"cookie":13}
	
	sbm_dict = {"fieldname":0,\
			 "fielddesc":1,\
			 "mo":2,\
			 "order":3,\
			 "placeholder":4}
	
	hgf_field = sbmfield[sbm_dict["fieldname"]]
	if hgf_field.startswith("hgf"): 
		element = config["fielddesc"][hgf_field] # we have to read the fielddescriptor from confg file, because all fielddescriptors in database will be redefined to "user defined fields" at the end of this function
	else: 
		if hgf_field in config["default_form"]: element = get_field_from_sbmfielddesc(hgf_field)[1:]
		else: return "","O" #non hgf-fields (defined collections,...)
	placeholder = "" #initialise
	fieldlabel = "" #initialise
	if len(sbmfield) == sbm_dict["placeholder"] +1: placeholder = sbmfield[sbm_dict["placeholder"]] #get placeholder
	
	if hgf_field == "hgf_start":  		
    	# define a fieldset which can then be used for internal element
    	# placement relative to that div so we end up with a table-less
    	# form doing arrangement entirely in CSS
		if read_javascript_includes():
			fieldlabel = read_javascript_includes()
		fieldlabel += '<fieldset id="submissionfields"><legend id="submissionlegend">%s</legend><div id="loadingMsg"><img src="/img/search.png" alt="Loading..." />Loading data. Please stand by...    </div>' %sbmfield[sbm_dict["fielddesc"]]
		return fieldlabel,sbmfield[sbm_dict["mo"]].upper()
		
	if hgf_field == "hgf_end":
    		# close the main fieldset
		fieldlabel = '</fieldset>'
		return fieldlabel,sbmfield[sbm_dict["mo"]].upper()
		
	if hgf_field == "hgf_comment": #technical field
		if sbmfield[1] == "hidden": pass# 'hidden' is generated by create_mask function
		else:	 
			fieldlabel = "<span class=\"Comment\" id=\"hgf_comment\">%s</span>" % sbmfield[sbm_dict["fielddesc"]] 
			return fieldlabel,sbmfield[sbm_dict["mo"]].upper()
			
	if hgf_field == "hgf_preview": #mathjax title preview
		fieldlabel = ""
		return fieldlabel,sbmfield[sbm_dict["mo"]].upper()
	
	if element[el_dict["marccode"]] == "": #no marccode
		unique_id = sbmfield[sbm_dict["fieldname"]] # i.e. hgf_import is Input-field, but not MARC
		id1 = ""
		id2 = ""
	else : 
		id1 = element[el_dict["marccode"]][0:3]
		id2 = element[el_dict["marccode"]]
		unique_id = hgf_field.replace("hgf_","")
	size,rows,cols = element[3:6]
	value = element[el_dict["val"]]
	if value == "NULL": value = ""
	fieldtext = sbmfield[sbm_dict["fielddesc"]]
	fieldtype = "D" #change fieldtype to user defined input. IMPORTANT: whole information about the field (spans, fieldname, input-field, textarea) are stored in the fieldlabel in the sbmFIELD herefore fidesc in sbmFIELDDESC has to be "" and eltype "D")
	
	
	if inst != "default":
		suffix = "#" + inst.upper() + "_font" # suffix for twiki page at GSI	
	else: suffix = ""
	#Insert Helptext#
	wiki_base = ""
	if ("CFG_HGF_WIKI_BASE_URL" in globals()):
    	# Twiki needs all page titles to start with a capital letter.
    	# Therefore, capitalize() the uniq_id when constructing the URL.
    		wiki_base = CFG_HGF_WIKI_BASE_URL 
        else:
		wiki_base = "http://invenio-wiki.gsi.de/cgi-bin/view/Main/"
	help_text = '<span class="Helptext" id="%(unique_id)s%(suffix)s"><a href="%(wiki_base)s%(unique_id)s%(suffix)s" alt="Help" target="_blank"><img src="/img/hgfinfo.png"></a></span>' %{'unique_id':unique_id.capitalize(),"suffix":suffix,"wiki_base":wiki_base}

	mog = "" #this variable is set for group dependent mandatory fields 
	if element[el_dict["type"]].upper() == "I": #Input text box
		groupclass = get_groupclass(sbmfield[sbm_dict["mo"]]) #get groupclass in case of fieldlevel=m1,m2,m3...... if no groupclass, then return ""
		if groupclass != "": mog = "MOG"
		if sbmfield[sbm_dict["mo"]].lower().startswith("m"):#fieldlevel
			fieldlabel = '<span class="MG%(id2)s G%(id2)s MG%(id1)s G%(id1)s MG G %(mog)s"><label for="I%(unique_id)s" class="L%(unique_id)s ML%(id2)s L%(id2)s ML%(id1)s L%(id1)s ML L">%(fieldtext)s</label> %(help_text)s <input name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="MI%(id2)s I%(id2)s MI%(id1)s I%(id1)s MI I %(groupclass)s"></input></span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
		else: 	
			if unique_id == sbmfield[sbm_dict["fieldname"]]: #no marccode but Input-field
				fieldlabel = '<span class="G G%(unique_id)s %(mog)s"> <label for="I%(unique_id)s" class="L%(unique_id)s L">%(fieldtext)s</label> %(help_text)s <input name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="I %(groupclass)s"></input> </span>' % {'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
			else:
				fieldlabel = '<span class="G%(id2)s G%(id1)s G %(mog)s"> <label for="I%(unique_id)s" class="L%(id2)s L%(id1)s L">%(fieldtext)s</label> %(help_text)s <input name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="I%(id2)s I%(id1)s I %(groupclass)s"></input> </span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
	elif element[el_dict["type"]].upper() == "T":	# Textarea
		groupclass = get_groupclass(sbmfield[sbm_dict["mo"]])
		if groupclass != "": mog = "MOG"
		if sbmfield[sbm_dict["mo"]].lower().startswith("m"):#fieldlevel
			fieldlabel = '<span class="MG%(id2)s G%(id2)s MG%(id1)s G%(id1)s MG G %(mog)s"> <label for="I%(unique_id)s" class="ML%(id2)s L%(id2)s ML%(id1)s L%(id1)s ML L" >%(fieldtext)s</label> %(help_text)s <textarea name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="MI%(id2)s I%(id2)s MI%(id1)s I%(id1)s MI I %(groupclass)s" cols="%(cols)s" rows="%(rows)s"></textarea> </span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'rows':rows,'cols':cols,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
		else:
			fieldlabel = '<span class="G%(id2)s G%(id1)s G G%(unique_id)s %(mog)s"> <label for="I%(unique_id)s" class="L%(id2)s L%(id1)s L">%(fieldtext)s</label> %(help_text)s <textarea name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="I%(id2)s I%(id1)s I %(groupclass)s" cols="%(cols)s" rows="%(rows)s"></textarea> </span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'rows':rows,'cols':cols,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
	elif element[el_dict["type"]].upper() == "H": #hidden field
		if unique_id == sbmfield[sbm_dict["fieldname"]]:
			fieldlabel = '<span class="G"> <label for="I%(unique_id)s" class="L%(unique_id)s L"></label> <input type="hidden" name="%(hgf_name)s" id="I%(unique_id)s" value="%(value)s" class="I"></input> </span>' % {'unique_id':unique_id,'value':value,'hgf_name':hgf_field}
		else:
			fieldlabel = '<span class="G%(id2)s G%(id1)s G"> <label for="I%(unique_id)s" class="L%(unique_id)s L%(id2)s L%(id1)s L"></label> <input type="hidden" name="%(hgf_name)s" id="I%(unique_id)s" value="%(value)s" class="I%(id2)s I%(id1)s I"></input> </span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'value':value,'hgf_name':hgf_field}
	elif element[el_dict["type"]].upper() == "F": #File field
		groupclass = get_groupclass(sbmfield[sbm_dict["mo"]])
		if groupclass != "": mog = "MOG"
		if sbmfield[sbm_dict["mo"]].startswith("m"):#fieldlevel
			if unique_id == sbmfield[sbm_dict["fieldname"]]: #no marccode but Input-field
				fieldlabel = '<span class="MG MG%(unique_id)s %(mog)s"> <label for="I%(unique_id)s" class="L%(unique_id)s ML">%(fieldtext)s</label> %(help_text)s <input type="file" name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="MI %(groupclass)s"></input> </span>' % {'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
			else:	
				fieldlabel = '<span class="MG%(id2)s G%(id2)s MG%(id1)s G%(id1)s MG G %(mog)s"><label for="I%(unique_id)s" class="ML%(id2)s L%(id2)s ML%(id1)s L%(id1)s ML L">%(fieldtext)s</label> %(help_text)s <input type="file" name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="MI%(id2)s I%(id2)s MI%(id1)s I%(id1)s MI I %(groupclass)s"></input></span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'groupclass':groupclass,'mog':mog,'placeholder':placeholder}
		else: 	
			if unique_id == sbmfield[sbm_dict["fieldname"]]: #no marccode but Input-field
				fieldlabel = '<span class="G G%(unique_id)s"> <label for="I%(unique_id)s" class="L%(unique_id)s L">%(fieldtext)s</label> %(help_text)s <input type="file" name="%(hgf_name)s" placeholder="%(placeholder)s" id="I%(unique_id)s" class="I"></input> </span>' % {'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'placeholder':placeholder}
			else:
				fieldlabel = '<span class="G%(id2)s G%(id1)s G"> <label for="I%(unique_id)s" class="L%(id2)s L%(id1)s L">%(fieldtext)s</label> %(help_text)s <input name="%(hgf_name)s" placeholder="%(placeholder)s" type="file" id="I%(unique_id)s" class="I%(id2)s I%(id1)s I"></input> </span>' % {'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'placeholder':placeholder}
	elif element[el_dict["type"]].upper() == "C": #check box
		fieldlabel = make_specialfields(unique_id,id1,id2,size,fieldtext,hgf_field,help_text,sbmfield,config,"checkbox",inst)
	elif element[el_dict["type"]].upper() == "R": #Radio button Warninig invenio default for "R" would be Response Element
		fieldlabel = make_specialfields(unique_id,id1,id2,size,fieldtext,hgf_field,help_text,sbmfield,config,"radio",inst)
	else: 	return "","O" #other hgf-field with marccode (if exists)
	
	eltype = get_eltype_from_sbmfielddesc(hgf_field)
	fidesc = ""
	modification_text = fieldlabel #modification text
	if eltype != fieldtype: update_eltype_in_sbmfielddesc(hgf_field,fieldtype,modification_text,fidesc) #redefine fielddescriptor in database
	
	if len(sbmfield[sbm_dict["mo"]])>1: fieldlevel = sbmfield[sbm_dict["mo"]][0].upper() #prevent submitting irregular values into DB for fieldlevel, only M,O possible 
	else: fieldlevel = sbmfield[sbm_dict["mo"]].upper() 
	return fieldlabel,fieldlevel

def get_input(values,inputclass,typ):
	"""make multiple radio buttons/ checkboxes """
	if typ == "radio": inputfield = '<input type="radio" name="%(hgf_name)s" checked="checkedvalue"  value="value2" %(inputclass)s></input>value1'
	if typ == "checkbox": inputfield = '<input type="checkbox" name="%(hgf_name)s" checked="checkedvalue"  value="value2" %(inputclass)s></input>value1'
	inp_fields = ""
	values = eval(values)
	if isinstance(values[0],str): values = [values] #workaround for one checkbox/radio
	for tupl in values:
		value1 = tupl[0]
		value2 = tupl[1]
		if len(tupl) == 3: checkedvalue = tupl[2]
		else: checkedvalue = ""
		field = inputfield.replace("value1",value1).replace("value2",value2).replace("checked=\"checkedvalue\"",checkedvalue)
		inp_fields += field
	return inp_fields	
								
def make_specialfields(unique_id,id1,id2,size,fieldtext,hgf_field,help_text,sbmfield,config,typ,inst):
	"""create radio buttons and checkboxes"""
	specialfields = config["default"]["specialfields"]
	if "specialfields" in config[inst].keys():
		if hgf_field in config[inst]["specialfields"].keys():
			specialfields = config[inst]["specialfields"]
		else: 
			warning("Please define %s in specialfields. we take %s from the default" %(hgf_field,hgf_field))
		
	else: 
		warning("Please define specialfields under config['%s']. we take specialfields from default" %inst)
			
	values = specialfields[hgf_field] #get special values for radio buttons
	groupclass = get_groupclass(sbmfield[2])
	mog = "" # this variable is set for group mandatory fields
	if groupclass != "": mog = "MOG"
	if sbmfield[2].startswith("m"): #fieldlevel
		if unique_id == sbmfield[0].replace("hgf_",""): #no marccode but Input-field 
			spanclass = '<span class="MG MG%(unique_id)s %(mog)s"> <label for="I%(unique_id)s" class="L%(unique_id)s ML">%(fieldtext)s</label> %(help_text)s'
			inputclass = 'class="MI %s"' % groupclass
			inputfield = get_input(values,inputclass,typ) 
		else:
			spanclass = '<span class="MG%(id2)s G%(id2)s MG%(id1)s G%(id1)s MG G %(mog)s"><label for="I%(unique_id)s" class="ML%(id2)s L%(id2)s ML%(id1)s L%(id1)s ML L">%(fieldtext)s</label> %(help_text)s'
			inputclass = 'class="MI%(id2)s I%(id2)s MI%(id1)s I%(id1)s MI I %s"' %groupclass
			inputfield = get_input(values,inputclass,typ) 
	else:
		if unique_id == sbmfield[0].replace("hgf_",""): #no marccode but Input-field
			spanclass = '<span class="G G%(unique_id)s"> <label for="I%(unique_id)s" class="L%(unique_id)s L">%(fieldtext)s</label> %(help_text)s'
			inputclass = 'class="I %s"' %groupclass
			inputfield = get_input(values,inputclass,typ) 	 
		else:
			spanclass = '<span class="G%(id2)s G%(id1)s G"> <label for="I%(unique_id)s" class="L%(id2)s L%(id1)s L">%(fieldtext)s</label> %(help_text)s'
			inputclass = 'class="I%(id2)s I%(id1)s I %s"' %groupclass
			inputfield = get_input(values,inputclass,typ) 
	end = '</span>'
	span_field = spanclass + inputfield + end
	span_field = span_field %{'id1':id1,'id2':id2,'unique_id':unique_id,'size':size,'fieldtext':fieldtext,'hgf_name':hgf_field,'help_text':help_text,'inputclass':inputclass,'mog':mog}
	return span_field			
								
								
def insert_mbifields(config,doctype,inst):
	"""defines the fields in sbmFIELD to appear in the modification form. hidden fields are already skipped in the create_mask function
	This page should never asppear in the frontend, but needed for the MBI constructor
	"""
	
	docname = get_docname_from_schema(doctype,config)
	fieldtext = '<table width="100%" bgcolor="#99CC00" align="center" cellspacing="2" cellpadding="2" border="1"><tr><td align="left"><br /><b>Modify a docname bibliographic information:</b><br /><br /><span style="color: red;">*</span>Reference Number:&nbsp;&nbsp;'
	fieldtext = fieldtext.replace("docname",docname)
	fieldlevel = "O"
	action = "MBI"
	pagenum = "1"
	fieldname = "rn"
	fieldshortdesc = fieldname.replace("hgf_","")
	fieldcheck = ""
	insert_field_onto_submissionpage(doctype, action, pagenum, fieldname, fieldtext, fieldlevel, fieldshortdesc, fieldcheck) #insert into sbmFIELD	
	
	## hgf_change
	select_box = '<select visibility="hidden" name="mod_%s[]" size="1"><option value="Select:">Please click continue:</option></select>' %doctype #fake selectbox
	elname = "mod_" + doctype
	elmarccode = ""
	eltype = "S"
	elsize = ""
	elrows = ""
	elcols = ""
	elmaxlength = ""
	elval = ""
	elfidesc = select_box # select box for modification form
	elmodifytext = ""
	insert_element_details(elname, elmarccode, eltype, elsize, elrows, elcols, elmaxlength, elval, elfidesc, elmodifytext) # inserrt into sbmFIELDDESCR
	
	
	fieldtext = ''
	fieldlevel = "O"
	action = "MBI"
	pagenum = "1"
	fieldname = elname
	fieldshortdesc = elname.replace("hgf_","")
	fieldcheck = ""
	insert_field_onto_submissionpage(doctype, action, pagenum, fieldname, fieldtext, fieldlevel, fieldshortdesc, fieldcheck) #insert into sbmFIELD	
	
	#mbi_end 
	fieldtext = '<br /><br /></td></tr></table><br />'
	fieldlevel = "O"
	action = "MBI"
	pagenum = "1"
	fieldname = "mbi_end"
	fieldshortdesc = fieldname.replace("hgf_","")
	fieldcheck = ""
	insert_field_onto_submissionpage(doctype, action, pagenum, fieldname, fieldtext, fieldlevel, fieldshortdesc, fieldcheck) #insert into sbmFIELD	
		
def create_mask(config,doctype,inst):
	""""""
	default_keys = sort_hgf_fields(config,doctype,inst)   # create new field order
	for field in default_keys: #fields
		if doctype in config[inst].keys(): #check if doctype defined for institional changes
			if field in config[inst][doctype].keys():
				if config[inst][doctype][field] == "None": continue #field is None and will not appear on submissionpage
				else:
					order_index = default_keys.index(field)
					sbmfield = merge_sbmfield(doctype,config,inst,field,order_index)# we have institutional changes
			else: 
				if field in config["default_form"].keys():
					sbmfield = [field] + config["default_form"][field]#field unchanged
				else: 
					sbmfield = [field] + ["hidden","o"] #add hidden field
		else:  
			if field in config["default_form"].keys():
				sbmfield = [field] + config["default_form"][field]#field unchanged
			else: 
				sbmfield = [field] + ["hidden","o"] #add hidden field
				
		fieldtext_visible = sbmfield[1]
		fieldtext,fieldlevel = create_user_defined_fielddesc(sbmfield,config,inst)
		action = "SBI"
		pagenum = "1"
		fieldname = field
		fieldshortdesc = fieldtext_visible
		fieldcheck = ""
		#document specific field modifications
		insert_field_onto_submissionpage(doctype, action, pagenum, fieldname, fieldtext, fieldlevel, fieldshortdesc, fieldcheck) #sbmFIELD
		fieldlabels.append(fieldtext) 	 	
	insert_mbifields(config,doctype,inst) # insert mbi-fields for modification mask
	
			
			
			
################### end main functions ################################################
			
def process_all():
	"""main-function to insert all Collections, Documenttypes, Fields into database (and everything needed to get instituts-defined submission and modification forms) """
	confilepath = check_args()
	if confilepath != "":  #check arguments and sets some global variables 
		config = read_conf(confilepath) #read config-file
		inst = get_hgf_institute(config) #check which hgf-institute
		build_or_remove_fielddesc(config) #create/delete fielddescriptors (fields + marctags)
		insert_repnr_fielddesc(inst) #report number as hidden input in submit  
		build_or_remove_doctypes(config,inst) #create/delete doctypes
		build_or_remove_schema(config) #create/delete collections for submit form
		generate_css(fieldlabels,inst) #create css_file 
	else: pass
	
if __name__ == "__main__":
	process_all()
	pass
