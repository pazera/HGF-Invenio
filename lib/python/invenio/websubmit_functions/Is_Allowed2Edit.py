##
## Name:        Is_Allowed2Edit
## Description: function Is_Allowed2Edit
##    Users should be allowed to edit a record:
##    - Members of an institute should be allowed to edit all records
##      in their private institute collection unless they were
##      approved by their respective EDITOR
##      => Compare user groups with 980__a: needs match
##      => 980__a must NOT contain UNRESTRICTED which signifies
##         approval by either EDITOR or even STAFF
##    - If the user is owner and EDITOR of one of the contributing
##      institutes. Does NOT need to be the submitter
##    - If the user is STAFF
##
## Author:     A. Wagner
##
## PARAMETERS:    -
## OUTPUT: HTML
##

import re
import os
from invenio.access_control_engine import acc_authorize_action
from invenio.websubmit_config import InvenioWebSubmitFunctionStop
from invenio.websubmit_functions.Retrieve_Data import Get_Field
from invenio.websubmit_functions.Shared_Functions import write_file
from invenio.access_control_config import CFG_EXTERNAL_AUTH_DEFAULT

def checkModifyPermissions(uid_email, groups, recid):
  # This function gives permisson to modify a record. It is also
  # called by bfe_modifylnk to create a link if modification is
  # allowed. We implement a 3 step workflow:
  # User submitted records:
  #   - they end up in private collections, one per institute. Every
  #     member of the institute is allowed to edit any record in those
  #     collections unless it reached a higher state.
  #   - if an EDITOR of an institute approved a record, users are no
  #     longer allowed to edit them. You need to be at least editor
  #     for one of the owning institutes to modify it.
  #   - if STAFF approved a record for publications database you need
  #     to be at least STAFF to modify it.
  from invenio.access_control_config import CFG_EXTERNAL_AUTH_DEFAULT
  from invenio.websubmit_functions.Retrieve_Data import Get_Field
  import re

  # Literal names of our EDITORS and STAFF groups
  Editorsgrp     = 'EDITORS'
  Staffgrp       = 'STAFF'

  # we need editor rights if editor touched the record. This is marked
  # by the record to have 980__a:EDITORS set
  ReqEditorGrp   = Editorsgrp 

  # we need staff rights if staff approved the record. This is marked
  # by the record to have 980__a:VDB set, ie the final public
  # collection in our workflow
  ReqStaffGrp    = 'VDB'

  # By default we have no special privileges
  Is_Submitter   = False   # is original submitter
  Is_Editor      = False   # is member of EDITORS group
  Is_Staff       = False   # is member of STAFF group
  Is_Groupmember = False   # is member of the group
  Require_Editor = True    # at least reuquire editor rights
  Require_Staff  = True    # at least reuquire editor rights

  # Check the email of the currently logged in user against the
  # originator email in the record.
  email = Get_Field("8560_f",recid)
  email = re.sub("[\n\r ]+","",email)
  uid_email = re.sub("[\n\r ]+","",uid_email)

  # Is_Submitter is always sufficient as EDITORS set their name upon
  # approval as does STAFF.
  if re.search(uid_email,email,re.IGNORECASE) is None:
    Is_Submitter = False
  else:
    Is_Submitter = True

  # Being STAFF is enough for everything
  if Staffgrp in groups:
     Is_Staff  = True
     Is_Editor = True
  if Editorsgrp in groups:
     Is_Editor = True

  # Get a list of all collections a document belongs to
  dc = Get_Field("980__a", recid)
  doccollections = dc.split('\n')

  # if a document was handled by EDITORS at least another EDITOR is
  # required to change it.
  if ReqEditorGrp in doccollections:
     Require_Editor = True
  else:
     Require_Editor = False

  if ReqStaffGrp in doccollections:
     Require_Staff = True
  else:
     Require_Staff = False

  # Check if we are member of a suitable group
  for group in groups:
      # from external auth we get a postfix the we need to strip off
      grp = group.replace(' ['+CFG_EXTERNAL_AUTH_DEFAULT+']', '')
      if (grp != Editorsgrp) and (grp != Staffgrp):
         if grp in doccollections:
             Is_Groupmember = True

  #-# print 'Is_Staff      ', Is_Staff
  #-# print 'Is_Editor     ', Is_Editor
  #-# print 'Is_Groupmember', Is_Groupmember
  #-# print 'Require_Staff ', Require_Staff
  #-# print 'Require_Editor', Require_Editor
  
  permit = False

  # Now we have extracted our group memberships and the records
  # status. Compare it to our requirements for modification to finally
  # give access or deny it.

  if Is_Staff:
    # Staff is always true
    permit = True

  # This is redundant, as Staff is always allowed to edit
  # if Require_Staff and Is_Staff:
  #   permit = True

  if Require_Editor and Is_Editor and Is_Groupmember:
    # Only EDITORS of the contributing institutes...
    permit = True

  if not(Require_Staff or Require_Editor) and Is_Groupmember:
    # All group members
    permit = True
    
  if Is_Submitter and not (Require_Editor or Require_Staff):
    # Submitter if no higher stage is achieved
    permit = True

  return permit

def Is_Allowed2Edit(parameters, curdir, form, user_info=None):
    """
    This function compares the email of the current logged
    user with the original submitter of the document. If
    identical it grants editing rights. If not, it is
    checked if the logged in user is in the group
    EDITORS and belongs to a group named like either of
    the collections associated with the record. If not 
    it check whether the user has special rights.
    """

    global uid_email,sysno,uid
    groups = user_info['group']

    permit = checkModifyPermissions(uid_email, groups, sysno)

    if permit:
      return
    else:
      raise InvenioWebSubmitFunctionStop("""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   user_must_confirm_before_leaving_page = false;
   // alert('You (%s) are not allowed to modify this document.');
   document.forms[0].submit();
</SCRIPT>""" % (uid_email))

    return

### if __name__ == '__main__':
###   print checkModifyPermissions('X', ['STAFF'] , 131805)
###   print checkModifyPermissions('Y', ['EDITORS'] , 131805)
###   print checkModifyPermissions('Y', ['EDITORS', 'I:(DE-Juel1)IEK-8-20101013 [FZJ eMail-Account]'] , 131805)
###   print checkModifyPermissions('Z', ['I:(DE-Juel1)IEK-8-20101013 [FZJ eMail-Account]'] , 131805)
