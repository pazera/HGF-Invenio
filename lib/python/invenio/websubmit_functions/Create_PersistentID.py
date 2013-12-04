## This file is part of Invenio for the HGF collaboration.
##
## Create_PersistentID.py provides functions for registering 
## Persistent-IDs, currently only Handles.
##
##
## CDS Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import os
import re
import subprocess
import time 


# The configured values currently only used as websubmit function, 
# (therefore websubmit_config.py would be also possible,)
# but for customizing via invenio(-local).conf is config.py used.
from invenio.config import CFG_WEBSUBMIT_STORAGEDIR \
                          ,CFG_WEBSUBMIT_PATH_HANDLESERVER  \
                          ,CFG_WEBSUBMIT_HANDLE_PREFIX      \
                          ,CFG_WEBSUBMIT_HANDLE_AUTHENTIFICATION \
                          ,CFG_WEBSUBMIT_HANDLE_CREATE_SPECIFICATION

from invenio.websubmit_config import InvenioWebSubmitFunctionError 


def Create_PersistentID(parameters, curdir, form, user_info=None):
    """
    Register a persistent identifier for an URL depend on type and 
    return persistent identifier, if successful registered.
    
    @param parameters: (dictionary) of parameters contain following keys and values

    @param type: (string) Type of persistent identifier, which should be registered. 
                 This types are until now expected 'handle', 'doi', 'urn'.

    @param url: (string) URL for persistent identifier, which should be registered. 

    @param persist_id: (string) contains and optional proposal value for the persistent identifier.
    
    @return: (string) registered persistent identifier or if failed something None is returned
    
    @Exceptions raised: InvenioWebSubmitFunctionError:
                            - if type is unknown;
                            - if persist identifier unable to register;
    """
    
    type = parameters["type"]
    url = parameters["url"]
    
    #for registration without given persistent id
    try:
        persist_id = parameters["persist_id"]
    except KeyError:
        persist_id = None        
    
    return register_persistID(type, url, persist_id, curdir)


def register_persistID(type, url, persist_id=None, curdir=None): 
    """
    Register persistent identifier for an url depend on type and 
    return persistent identifier, if successful registered otherwise None.
    Following types are until now known: 'handle', 'doi', 'urn'
    It's possible to give a proposed value for the persistent identifier.
    Also it's possible to propose a directory for saving files while registration.
    """
    
    #identify directory for saving files
    if curdir == None:
        curdir = CFG_WEBSUBMIT_STORAGEDIR
    
    #call registration depend on type
    if type.lower() == 'handle':
        return register_handle(curdir, url, persist_id)        
    elif type.lower() == 'doi':
        return register_doi(curdir, url, persist_id)
    elif type.lower() == 'urn':
        return register_urn(curdir, url, persist_id)
    elif type ==  None or type == '':
        return None    
    else:  
        err = 'ERROR persistent identifier type %s is unknown!' %(type)  
        raise InvenioWebSubmitFunctionError(err)       
        

def register_handle(curdir, url, persist_id=None):
    """Register handle and return Handle-ID """
    
    # Handle-Server have to be installed and configured for using Handle-Registration
    if CFG_WEBSUBMIT_PATH_HANDLESERVER == '' or \
        CFG_WEBSUBMIT_HANDLE_PREFIX  == '' or \
        CFG_WEBSUBMIT_HANDLE_AUTHENTIFICATION == '' or \
        CFG_WEBSUBMIT_HANDLE_CREATE_SPECIFICATION == '':
        return None
    
    #if proposal handle-id not given, find out the next free handle-id
    if persist_id == None: persist_id = get_max_handle_digit() + 1    
    
    #create batch file
    reg_time_str = 'handle_%s' %(time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()))
    bfile_name = os.path.join(CFG_WEBSUBMIT_STORAGEDIR, reg_time_str+'.txt')                         
    logfile_name = os.path.join(CFG_WEBSUBMIT_STORAGEDIR, 'log_%s.log' %(reg_time_str))
    create_handle_batch_file(bfile_name, url, persist_id)

    #register with batch operation
    command = 'java -cp "%s" "net.handle.apps.batch.GenericBatch" "%s" "%s"' \
                %(os.path.join(os.path.split(CFG_WEBSUBMIT_PATH_HANDLESERVER)[0], os.path.join('bin','handle.jar'))
                 ,bfile_name, logfile_name)
                
    try:
        p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
        p.wait ()
        
        #check success of registration  
        res = check_handle_registration(logfile_name)
        if res[0] == False:
            raise InvenioWebSubmitFunctionError(res[1])  
        return persist_id
    
    except (OSError):
        err = 'ERROR could not register handle for url %s via batchfile %s!' %(url, bfile_name)
        raise InvenioWebSubmitFunctionError(err)       
        
    
def create_handle_batch_file(bfile_name, url, persist_id): 
    """Create and return batch file for Handle registration"""  
    bfile = open(bfile_name, 'w')  
                   
    #header with authentication information
    bfile.write(CFG_WEBSUBMIT_HANDLE_AUTHENTIFICATION+'\n\n')
   
    #create-part of handle batch format
    bfile.write('CREATE %s/%s\n%s %s' \
                %(CFG_WEBSUBMIT_HANDLE_PREFIX,persist_id \
                  ,CFG_WEBSUBMIT_HANDLE_CREATE_SPECIFICATION, url))
    bfile.close()
    return bfile


def check_handle_registration(logfile_name):
    """Checking result of handle registration via parsing the handle logfile
    and return tuple with boolean value and message. It's True, if handle 
    is successful registered otherwise return False with error message. 
    """
    try:
        lfile = open(logfile_name, 'r')
        content =  lfile.read()   
        res = re.search("(.*)(==>SUCCESS)(.*)[\t\n\r\f\v](.*)", content)
        lfile.close()
        if res != None: #success
            return (True, res.group(2))
        return (False, content) #different failures
    except IOError:
        err = "Handle logfile not found %s" %(logfile_name)          
        return (False, err)


def get_max_handle_digit():
    """Find the max existing Handle-ID as digit and return this. 
    Therefore a handle server's built-in database is used, which 
    return a list of handles, where the max digit Handle-ID is parsed """
    
    #ask handle server db and return list of handles
    command = 'java -cp "%s" "net.handle.apps.db_tool.DBList" "%s"' \
                %(os.path.join(os.path.split(CFG_WEBSUBMIT_PATH_HANDLESERVER)[0], os.path.join('bin','handle.jar'))
                 ,CFG_WEBSUBMIT_PATH_HANDLESERVER)
                
    try:
        p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
        p.wait ()
        out = p.stdout.read()

        #parse handle listing for digits, a listing looks like this:
        #Listing handles:
        #1234/22
        #1234/8
        #1234/xxx
        digit_list = []
        for item in out.split('\n'):
            res = re.search("(%s)/(\d+)" %(CFG_WEBSUBMIT_HANDLE_PREFIX), item)
            if res != None:
                digit_list.append(int(res.group(2)))
        
        #for first handle registration
        if len(digit_list) == 0: return 0 
        
        return max(digit_list) 

            
    except (OSError):
        err = 'ERROR could not find max registered Handle-ID!'
        raise InvenioWebSubmitFunctionError(err)  

    
def register_doi(curdir, url, persist_id=None):
    """Register doi and return DOI """
    reg_persist_id = None
    return reg_persist_id
 
 
def register_urn(curdir, url, persist_id=None):
    """Register urn and return Handle-ID """     
    reg_persist_id = None
    return reg_persist_id   
  
    
def test_register_handle():
    """test handle registration functions"""
	
#    #test registration with given handle
#    print register_persistID('handle','http://www.handle.net/tech_manual/Handle_Technical_Manual.pdf' ,'12')
#    
#    #test get max registered digit handle id for registration without given handle
#    print get_max_handle_digit()
#    
#    #test registration without given handle
#    print register_persistID('handle', 'http://www.handle.net/tech_manual/Handle_Technical_Manual.pdf')

	#test handle registration without given persistent id
    parameters = {'type':'handle', 'url':'http://www.handle.net/tech_manual/Handle_Technical_Manual.pdf' }
    print Create_PersistentID(parameters, None, None)
	

    
if __name__ == "__main__":
    pass
#    #test handle registration functions
#    test_register_handle()