import os
import simplejson as json
import re

"""
Helper functions used in various steps of websubmit/modify. Collect
functions that are used in various stages of websubmit here, e.g. to
handle the shuffeling of files necessary for websubmit, processing of
hgf-structures to/from JSON.

Note that curdir generally refers to the curdir used in websubmit.
This naming convention is kept throughout the module.
"""

# ----------------------------------------------------------------------
# from Prefill_hgf_fields.py

def add_non_json_fields(json_dict):
  """
  Add single input fields if field has no repetition

  For autosuggest field keep structured keys, and skip the creation of
  the individual subfields. Otherwise we'd need to delete them later
  on anyway, as those fields deliver their values via the technical
  strutured fields.

  @param json_dict: dict keyed by marc tags
  """
  autosuggest_keys = get_autosuggest_keys()
  for key in json_dict.keys():
    if not len(json_dict[key])==1:
      # json_dict[key] has always to be a list, and we can create only
      # individual files if it's lenght is exactly 1. If not the
      # second entry would just overwrite the first values.
      continue

    if key in autosuggest_keys:
      # do not create files for autosuggest/tokeninput entries
      continue

    # We found a structured field which is non autosuggest/tokeninput
    # and contains only one value. E.g. 773__ This gets spread up into
    # individual files for each key, e.g. 773__a, 773__0 ...
    for subfield in json_dict[key][0].keys():
      fieldname = key + subfield
      json_dict[fieldname] = json_dict[key][0][subfield]
    del json_dict[key] # Remove structure key from dict: we have individual files
  return json_dict



def clean_fields(curdir, fieldname):
  """ In case we have a structured field (ie. XXX__) and string inputs
  (XXX__a), we need to clean up the curdir such, that only the
  structured fields survive. Thus we delete the simple fields here.

  @param curdir   : curdir from websubmit containing all files
  @param fieldname : the (structured) field that should survive
  """

  # TODO either we should call delete_fields here or use this function
  # for delete_fields. At least both sound very similar.

  liste = os.listdir(curdir)
  to_remove = []
  for file in liste:
    if not fieldname in file:
      continue
    if fieldname == file: 
      continue # technical field should not be deleted
    to_remove.append(file)

  for i in to_remove:
    file_to_delete = os.path.join(curdir,i)
    os.remove(file_to_delete)

def get_autosuggest_keys():
  """
  Define which fields are use autosuggest or tokeninput in the
  webfrontend. Those fields always return the real values in the
  structured technical subfields and the simple fields only serve
  display purposes, thus their data should not be considered later on.
  """
 
  autosuggest_keys = [ "0247_", "1001_", "7001_", "245__",
			     "3367_", "536__", "9131_",
			     "9201_", "980__", "982__"]
  return [] ####TODO CERN DEMO does not need autosuggest!!!!!!!!!!!!!!!!!!!!

def read_file(curdir, filename):
  """
  Get contents of a file from curdir

  @param curdir  : curdir from websubmit containing all files
  @param filename: file to read from curdir
  """

  fd = open(os.path.join(curdir,filename),"r")
  text = fd.read().replace("\n","").replace("\r","")
  fd.close()
  return text

def read_json(curdir, filename):
  """
  Read json from a file and return dict

  Check if the file associated with the field name exists. If so,
  read it else return an empty dict.
  Note: usually all files should exist, however, in Postpone
  processes we might get an almost empty record so not even the
  mandantory fields got filled in. This is meant to catch this.

  @param curdir   : curdir from websubmit containing all files
  @param fieldname: Filename to read
  """
  if not check_field_exists(curdir,filename): 
    return  []
  text = read_file(curdir,filename)

  if text.startswith("["):
    pass #we have a list
  else:
    # create a list of the input. This is necessary, as Inveino does
    # not have a possibility to define an overall "startof/endof" an
    # output format. Thus if we return JSON-structures from simple
    # output format we get them without the necessary [] around it.
    text = '[' + text +']'
  jsontext = washJSONinput(text)
  jsondict = json.loads(jsontext, 'utf8')
  #marcfield = fieldname.replace("hgf_","")
  #if isinstance(jsondict,list): jsondict = {marcfield:jsondict} # if json Frormat as list
  return jsondict

def remove_file(curdir, filename):
  """
  Delete an arbitrary file from curdir.

  @param curdir   : curdir from websubmit containing all files
  @param fieldname: Marc Tag to process (our files follow the hgf_<marc> naming convention)
  """
  #os.remove(os.path.join(curdir,filename)) TODO: use os.remove if possible
  os.system("rm -f %s" %os.path.join(curdir,filename))


def wash_db_record_dict(record_dict):
  """
  create nice json dictionary

  @param record_dict: output of search_engine.get_record
  @type record_dict : Invenio Marc tuple
  """
  json_dict = {}
  for marccode in record_dict.keys():
    #loop 1: all datafields (we get a list with repeatable datafields)
    ct_fields = len(record_dict[marccode]) # field counter
    #print marccode
    for marcfield in record_dict[marccode]: #loop2: all 700 fields
      #print marcfield
      ind1 = marcfield[1]
      ind2 = marcfield[2]
      if (ind1 == "" or ind1 == " "): ind1 = "_"
      if (ind2 == "" or ind2 == " "): ind2 = "_"

      fullmarccode = str(marccode) + ind1 + ind2
      #print fullmarccode, marcfield
      _dict ={}
      for subfield in marcfield[0]:
        #loop3: all subfields
        subfield_code = subfield[0]
        subfield_val = subfield[1]
        _dict[subfield_code]=subfield_val
      if _dict == {}: continue
      if not fullmarccode in json_dict.keys(): json_dict[fullmarccode] = []
      json_dict[fullmarccode].append(_dict)

  return json_dict

def write_done_file(curdir):
  """
  In original Invenio the modify contains a step 0 to select the
  fields that should be modified. This page generates a donefile for
  step 1 to know that step 0 was passed and also to pass on the fields
  to modify.

  As we do not use the step 0 and always use the full forms with all
  fields we just fake this file to stay compatible here.

  @param curdir: curdir from websubmit containing all files
  """
  write_file(curdir, "Create_Modify_Interface_DONE", "DONE")

def write_file(curdir, filename, text):
  """
  Write a text file to curdir for further processing

  @param curdir  : curdir from websubmit containing all files
  @param filename: name of the file to generate. We need the real file
                   name here and do not prpend hgf_ automagically as
                   we use this function to write any file
  @param text    : conents of the file
  """
  wd = open(os.path.join(curdir,filename),"w")
  wd.write(text)
  wd.close()


def write_json(curdir, filename, _dict):
  """
  Write python structure (usually a dictionary) as JSON to a file

  @param curdir  : curdir from websubmit containing all files
  @param filename: file to write, no automatic name conversoin to hgf_
  @param dict     : dictionary to write. This dict should be properly keyed
                    by Marc tags. Note that due to this structure we
                    do /not/ use repeatable subfields here.
  """
  fw = open(os.path.join(curdir,filename), "w")
  json.dump(_dict, fw)
  fw.close()

def write_all_files(curdir, json_dict):
  """
  Write files for the keys contained in json_dict.

  @param curdir: curdir from websubmit containing all files
  @param json_dict: dict keyed by marc tags
  """
  for field in json_dict.keys():
    fieldname = "hgf_" + field
    if len(field) == len('XXXii'):
      write_json(curdir, fieldname, json_dict[field])
    else:
      write_file(curdir, fieldname, json_dict[field])
  return


# ----------------------------------------------------------------------
# from Convert_hgf_Fields

def get_usergroups(uid):
  """
  Get all groups of a user and return them as a list. In case a user
  does not belong to any group (this should not happen) return an
  emptyl list

  @param uid: User ID
  """
  from invenio.webgroup_dblayer import get_groups

  # TODO check Create_hgf_collection: why does it not use this
  # function

  user_groups = get_groups(uid)
  if user_groups == []:
    return []
  groups = []
  [groups.append(tup[1]) for tup in user_groups]
  return groups



def check_field_exists(curdir, fieldname):
  """
  Check if a file (fieldname) exists in curdir.

  @param curdir   : curdir frreom websubmit containing all files
  @param fieldname: file to check
  """
  # TODO replace all those os.path.exists() calls by
  # check_field_exists() to get easier code
  if os.path.exists(os.path.join(curdir,fieldname)):
    return True
  else:
    return False

# ----------------------------------------------------------------------
# from Create_hgf_collection.py

def get_user(uid):
  """
  Check role of a user, ie. if she is STAFF, EDITORS or USER

  @param uid: User ID
  """
  user_groups = get_usergroups(uid)
  if "STAFF"   in user_groups: return "STAFF"
  if "EDITORS" in user_groups: return "EDITORS"
  return "USER"     
  
def get_technical_collections():
  """
  Return a list of collections that have a special meaning in our
  workflow.
  """
  return [ "EDITORS", "MASSMEDIA", "TEMPENTRY", "USER", "VDB", "VDBINPRINT", "VDBRELEVANT"]

# ----------------------------------------------------------------------
# from Create_hgf_record_json.py

def get_hgf_files(curdir):
  """
  Get all hgf_files from curdir

  @param curdir   : curdir from websubmit containing all files
  """
  hgf_files = []
  for f in os.listdir(curdir):
    if not f.startswith("hgf_"): continue
    hgf_files.append(f)
  return hgf_files

def washJSONinput(jsontext):
    """
    Wash string jsontext intended for processing with json.loads().
    Removes newlines and commas before closing brackets and at the end
    of the string. We get this e.g. due to Invenios inability to handle
    lists properly in output formats.

    @param jsontext : The text that should be cleaned.

    Returns: String suitable for processing with json.loads()
    """
    #jsontext = re.sub('\n', '', jsontext)
    jsontext = re.sub(r"(?<!\\)(\n\r|\n|\r)", " ", jsontext)
    jsontext = re.sub(',\s*]', ']', jsontext)
    jsontext = re.sub(',\s*}', '}', jsontext)
    jsontext = re.sub(',\s*$', '', jsontext)
    return jsontext

def get_recordid(curdir):
  """
  Extract the record ID from the SN file in curdir

  @param curdir   : curdir from websubmit containing all files
  """
  return read_file(curdir, "SN")

def check_hgf_field(fieldname):
	"""
  Check if a filename matches a is a regular marcfield syntax
  prepended by hgf_. This is a simple plausibility check it does not
  evaluate if this field exists or has some meaning.

  Depending wether we have an encoded subfield (245__a vs. 245__)
  return 'asci' for subfields (plain string values) or 'json' for
  fields that hold a json-structure.

  @param fieldname : filename in curdir like hgf_245__a
  """
	if fieldname == "hgf_release": return False, "" #do not check for hgf_release
	if len(fieldname) < len("hgf_xxx"): return False, "" # controlfields or more
	if fieldname == "hgf_master": return True, "master" #record linking
	if re.search('_[A-Za-z0-9]{3}[_A-z0-9]', fieldname):
		if len(fieldname) == 9: return True, "json"
		if len(fieldname) > 9: return True, "asci"
		else: return False, "" 
	else: return False, ""

def backup_file(curdir,fieldname):
	"""
  Create a bak file in curdir. Useful for testing submission stages
  but usually not used in our productive workflows.

  @param curdir   : curdir from websubmit containing all files
  @param fieldname : filename in curdir like hgf_245__a
  """
	bak_file = os.path.join(curdir,fieldname + ".bak")
	orig_file = os.path.join(curdir,fieldname) 	
  # TODO avoid system call.
	os.system("cp %s %s" %(orig_file,bak_file)) 
