##
## Name:          Is_Submitter_Or_Editor
## Description:   function Is_Submitter_Or_Editor
##             This function compares the email of the current logged
##             user with the original submitter of the document. If
##             identical it grants editing rights. If not, it is
##             checked if the logged in user is in the group
##             EDITORS and belongs to a group named like either of
##             the collections associated with the record. If not 
##             it check whether the user has special rights.
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


def Is_Submitter_Or_Editor(parameters, curdir, form, user_info=None):
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

    # By default we have no special privileges
    Is_Submitter   = 0   # 1 for original submitter
    Is_Editor      = 0   # 1 for member of EDITORS group
    Is_Groupmember = 0   # 1 for member of the group
    Editor_Auth    = 0   # 1 for Editor + belongs to institute
    auth_code      = 1   # 0 if access is granted by higher rights

    doctype = form['doctype']
    act = form['act']

    # Check the email of the currently logged in user against the
    # originator email in the record.
    email = Get_Field("8560_f",sysno)
    email = re.sub("[\n\r ]+","",email)
    uid_email = re.sub("[\n\r ]+","",uid_email)

    if re.search(uid_email,email,re.IGNORECASE) is None:
      Is_Submitter = 0
    else:
      Is_Submitter = 1

    # Get group memberships of the user to see if she is in EDITORS
    # groups = bfo.user_info['group']
    groups = user_info['group']

    # Get_Field returns a \n separated string of all field values it
    # can find. Split it to get a list we can loop
    dc = Get_Field("980__a", sysno)
    doccollections = dc.split('\n')

    for group in groups:
      if group == 'EDITORS':
        Is_Editor = 1
      if group == 'STAFF':
        Editor_Auth = 1

    # if we are Editor, we also need to be member of the right group.
    if Is_Editor == 1:
      for col in doccollections:
        for group in groups:
            # from external auth we get a postfix the we need to strip off
            grp = group.replace(' ['+CFG_EXTERNAL_AUTH_DEFAULT+']', '')
            if col == grp:
               Editor_Auth = 1

    if (Is_Submitter == 0) and (auth_code != 0) and (Editor_Auth == 0):
        # We are neither submitter nor do we have special rights
        raise InvenioWebSubmitFunctionStop("""
<SCRIPT>
   document.forms[0].action="/submit";
   document.forms[0].curpage.value = 1;
   document.forms[0].step.value = 0;
   user_must_confirm_before_leaving_page = false;
   // alert('You (%s) are not the submitter (%s) of this document nor editor for this group.\\nYou are not allowed to modify it.');
   document.forms[0].submit();
</SCRIPT>""" % (uid_email,email))
    elif Editor_Auth == 1:
      # keep the alert only for testing, fall trough silently in
      # productive systems
      return (""" 
<SCRIPT>
  // alert('This record was originally submitted by %s. You (%s) are allowed to modify it as you are Editor for this group.');
</SCRIPT>""" % (email,uid_email))
    elif auth_code == 0:
      # keep the alert only for testing, fall trough silently in
      # productive systems
      return ("""
<SCRIPT>
  // alert('Only the submitter of this document has the right to do this action. \\nYour login (%s) is different from the one of the submitter (%s).\\n\\nAnyway, as you have a special authorization for this type of documents,\\nyou are allowed to proceed! Watch out your actions!');
</SCRIPT>""" % (uid_email,email))

    return
