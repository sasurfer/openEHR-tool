import requests
from url_normalize import url_normalize
from lxml import etree
import json
from json_tools import diff
import string,random
import sys
from flask import request
from myutils import myutils,structuredMarand2EHRBase
from flask import current_app
import redis
#import uuid

def init_ehrbase():
    current_app.logger.debug('inside init_ehrbase')
    client=requests.Session()
    return client

def getstatusredis(r):
    try:
        if r.ping():
            return "ok"
    except redis.ConnectionError as e:
        return e


def getstatus(client,auth,url_base_status):
    current_app.logger.debug('inside getstatus')
    myresp={}
    myurl=url_normalize(url_base_status)
    try:
        response=client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json',
                                       'Accept': 'application/json'},verify=True)
    except requests.exceptions.RequestException as e:
        myresp['status']='Failed to connect. Check your configuration and that EHRBase is running'
        myresp['status_code']="503"
        myresp['text']=e
        return myresp

    current_app.logger.debug('Get status')
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    if(response.status_code<210 and response.status_code>199):
        myresp['text']=response.text
        myresp['status']='success'
        myresp['headers']=response.headers
        myresp['status_code']=  response.status_code
        myresp['json']=json.loads(response.text)
        return myresp
    else:
        myresp['text']=response.text
        myresp['status']='failure'
        myresp['headers']=response.headers  
        myresp['status_code']=  response.status_code   
        current_app.logger.warning("GET status failure")
        return myresp    



def createPageFromBase4templatelist(client,auth,url_base,basefile,targetfile):
    current_app.logger.debug('inside createPageFromBase4templatelist')
    #client.auth = (username,password)
    myresp={}
    myurl=url_normalize(url_base  + 'definition/template/adl1.4')
    response=client.get(myurl,params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/XML'},verify=True)
    current_app.logger.debug('Get list templates')
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    if(response.status_code<210 and response.status_code>199):
        myresp['text']=response.text
        myresp['status']='success'
        myresp['headers']=response.headers
        myresp['status_code']=  response.status_code
        results=json.loads(response.text)
        templates=[r['template_id'] for r in results]
        if(len(templates)==0):
            templates=['No templates available']
        myresp['templates']=templates
        drmstart=['<select  class="form-select" type="text" id="tname" name="tname">']
        drmoptions=['<option>'+t+'</option>' for t in templates]
        drmstop=['</select>']
        drm=[]
        drm=drmstart+drmoptions+drmstop
        drmstring='\n'.join(drm)
        with open('./templates/'+basefile,'r') as ff:
            lines=ff.readlines()
        with open('./templates/'+targetfile,'w') as fg:
            docopy=True
            for line in lines:
                if('<!--dropdownmenustart-->' in line):
                    docopy=False
                    fg.write(drmstring)
                elif('<!--dropdownmenustop-->' in line):
                    docopy=True
                else:
                    if(docopy):
                        fg.write(line)
        return myresp
    else:
        myresp['text']=response.text
        myresp['status']='failure'
        myresp['headers']=response.headers  
        myresp['status_code']=  response.status_code   
        current_app.logger.warning("GET templates for createPageFromBase4templatelist failure")
        return myresp    

def gettemp(client,auth,url_base,url_base_ecis,tformat,template,ehrbase_version):
    myresp={}
    current_app.logger.debug('inside gettemp')
    current_app.logger.info(f'Get Template: template={template} format={tformat}')
    if(tformat=="OPT"):
        myurl=url_normalize(url_base  + 'definition/template/adl1.4/'+template)
        response=client.get(myurl,params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/XML'},verify=True)
    else: #format webtemplate
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'definition/template/adl1.4/'+template)
                response=client.get(myurl,params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/JSON',
                                                      'Accept': 'application/openehr.wt+json'},verify=True)
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis+'template/'+template)
                current_app.logger.debug('myurl')
                current_app.logger.debug(myurl)        
                response=client.get(myurl,params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/openehr.wt+json'},verify=True)
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    if(response.status_code<210 and response.status_code>199):
        if(tformat=="OPT"):
            root = etree.fromstring(response.text)
            responsexml = etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)
            responsexml=responsexml.replace("#","%23")
            myresp['template']=responsexml
        else:
            nohash=response.text.replace("#","%23")
            myresp['template']=json.dumps(json.loads(nohash),sort_keys=True, indent=1, separators=(',', ': '))
        myresp['status']='success'
        current_app.logger.info(f'GET success for template={template} in format={tformat}')
    else:
        myresp['status']='failure'
        
        current_app.logger.warning(f'GET Template failure for template={template} in format={tformat}') 
    myresp['text']=response.text
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code  
    return myresp

def listtemp(client,auth,url_base):    
    #client.auth = (username,password)
    myresp={}
    current_app.logger.debug('inside listtemp')
    print(f"url={url_base  + 'definition/template/adl1.4'}")
    myurl=url_normalize(url_base  + 'definition/template/adl1.4')
#    response=client.get(myurl,params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/json'},verify=certifi.where())
    response=client.get(myurl,params={'format': 'JSON'},
                        headers={'Authorization':auth,'Content-Type':'application/json'},
                        verify=True)
    current_app.logger.debug('Get list templates')
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'GET success for template list')
        myresp['json']=response.text
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'GET Template failure for template list') 
    myresp['text']=response.text
    myresp['headers']=response.headers  
    myresp['status_code']=  response.status_code  
    return myresp


def posttemp(client,auth,url_base,uploaded_template):
    current_app.logger.debug('inside posttemp')
    root=etree.fromstring(uploaded_template)
    telement=root.find("{http://schemas.openehr.org/v1}template_id")
    template_name=""
    if telement is not None:   
        for i in telement:
            template_name=i.text
        current_app.logger.info(f'POST Template : template={template_name}')
    else:
        current_app.logger.info('POST Template')
    myurl=url_normalize(url_base  + 'definition/template/adl1.4/')
    response=client.post(myurl,params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/XML'},
        data=etree.tostring(root),verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'Template POST template={template_name} success')
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'POST Template failure for template={template_name}')
    return myresp

def updatetemp(client,adauth,url_base_admin,uploaded_template,templateid):
    current_app.logger.debug('inside updatetemp')
    current_app.logger.info(f'Updating template: template={templateid}')
    root=etree.fromstring(uploaded_template)    
    myurl=url_normalize(url_base_admin  + 'template/'+templateid)
    response=client.put(myurl,params={'format': 'XML'},headers={'Authorization':adauth,'Content-Type':'application/xml',
                 'prefer':'return=minimal','accept':'application/xml' },
                 data=etree.tostring(root),verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'Update PUT success for template={templateid}')        
        return myresp
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Update Template PUT failure for template={templateid}')    
        return myresp

def deltemp(client,adauth,url_base_admin,templateid):
    current_app.logger.debug('inside deletetemp')
    current_app.logger.info(f'Deleting template: template={templateid}')
    myurl=url_normalize(url_base_admin  + 'template/'+templateid)
    response=client.delete(myurl,headers={'Authorization':adauth },verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'Delete Template success for template={templateid}')        
        return myresp
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Delete Template failure for template={templateid}')    
        return myresp

def delalltemp(client,adauth,url_base_admin):
    current_app.logger.debug('inside deletealltemp')
    current_app.logger.info(f'Deleting all template')
    myurl=url_normalize(url_base_admin  + 'template/all')
    response=client.delete(myurl,headers={'Authorization':adauth },verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        myresp['deleted']=json.loads(response.text)['deleted']
        current_app.logger.info(f'Delete all Templates success')        
        return myresp
    else:
        if response.status_code==422:
            errorjson=json.loads(response.text)
            message=errorjson['message']
            myresp['error422']=message
        myresp['status']='failure'
        current_app.logger.warning(f'Delete all Templates failure')    
        return myresp



def createehrid(client,auth,url_base,eid):
    current_app.logger.debug('inside createehrid')
    withehrid=True
    if(eid==""):
        withehrid=False    
    if(not withehrid):
        myurl=url_normalize(url_base  + 'ehr')
        current_app.logger.info("Create ehr without ehrid")
        response=client.post(myurl, params={},headers={'Authorization':auth, \
            'Content-Type':'application/JSON','Accept': 'application/json','Prefer': 'return={representation|minimal}'},verify=True)
    else:
        myurl=url_normalize(url_base  + 'ehr/'+eid)
        current_app.logger.info(f"Create ehr with ehrid: ehrid={eid}")
        response=client.put(myurl, params={},headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json','Prefer': 'return={representation|minimal}'},verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    if(response.status_code<210 and response.status_code>199):
        myresp['status']="success"
        if(withehrid):
            ehrid=response.headers['ETag'].replace('"','')
            current_app.logger.info(f'EHR creation PUT success with given ehrid={eid}')
            if(eid != ehrid):
                current_app.logger.debug('ehrid given and obtained do not match')
        else:
            ehrid=response.headers['ETag'].replace('"','')
            current_app.logger.info(f'EHR creation POST success with ehrid={ehrid}')
        myresp["ehrid"]=ehrid
        myresp['text']=response.text
    else:
        myresp['status']="failure"
        myresp['text']=response.text   
        myresp['headers']=response.headers
        if(withehrid):
            ministr=' PUT with ehrid='+eid
        else:
            ministr=" POST"     
        current_app.logger.warning('EHR creation"+ministr+" failure')    
    myresp['status_code']=response.status_code 
    current_app.logger.debug(myresp)
    return myresp

def createehrsub(client,auth,url_base,sid,sna,eid):
    current_app.logger.debug('inside createehrsub')
    body1='''
    {
    "_type" : "EHR_STATUS",
    "name" : {
        "_type" : "DV_TEXT",
        "value" : "EHR Status"
    },
    "subject" : {
        "_type" : "PARTY_SELF",
        "external_ref" : {
            "_type" : "PARTY_REF",
    '''
    body2=f'   "namespace" : "{sna}",'
    body3='''
            "type" : "PERSON",
            "id" : {
            "_type" : "GENERIC_ID",
    '''
    body4=f'	"value" : "{sid}",\n'
    body5='''
          "scheme" : "id_scheme"
            }
        }
    },
    "archetype_node_id" : "openEHR-EHR-EHR_STATUS.generic.v1",
    "is_modifiable" : true,
    "is_queryable" : true
    }
    '''
    body=body1+body2+body3+body4+body5
    current_app.logger.debug(body)
    myurl=url_normalize(url_base  + 'ehr')
    withehrid=True
    if(eid==""):
        withehrid=False
    if(not withehrid):
        myurl=url_normalize(url_base  + 'ehr')
        response=client.post(myurl, params={},headers={'Authorization':auth, \
                'Content-Type':'application/JSON','Accept': 'application/json','Prefer': 'return={representation|minimal}'},
                data=body,verify=True)
    else:
        myurl=url_normalize(url_base  + 'ehr/'+eid)
        response=client.put(myurl, params={},headers={'Authorization':auth, \
                'Content-Type':'application/JSON','Accept': 'application/json','Prefer': 'return={representation|minimal}'},
                data=body,verify=True)       
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    if(response.status_code<210 and response.status_code>199):
        myresp['status']="success"
        if(withehrid):
            ehrid=response.headers['ETag'].replace('"','')
            current_app.logger.info(f'EHR creation PUT success with given ehrid={eid}')
            if(eid != ehrid):
                current_app.logger.debug('ehrid given and obtain do not match')
        else:            
            ehrid=response.headers['ETag'].replace('"','')
            current_app.logger.info(f'EHR creation POST success with ehrid={ehrid}')
        myresp["ehrid"]=ehrid
        myresp['text']=response.text
    else:
        myresp['status']="failure"
        myresp['headers']=response.headers
        myresp['text']=response.text
        if(withehrid):
            ministr=' PUT with ehrid='+eid
        else:
            ministr=" POST"     
        current_app.logger.warning('EHR creation"+ministr+" failure')    
    myresp['status_code']=response.status_code 
    return myresp

def getehrid(client,auth,url_base,ehrid):
    current_app.logger.debug('inside getehrid')
    current_app.logger.debug("launched getehr")
    myurl=url_normalize(url_base  + 'ehr/'+ehrid)
    response=client.get(myurl, params={},headers={'Authorization':auth, \
            'Content-Type':'application/JSON','Accept': 'application/json','Prefer': 'return={representation|minimal}'},verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    if(response.status_code<210 and response.status_code>199):
        myresp['status']="success"
        myresp["ehrid"]=ehrid
        myresp['text']=response.text
        current_app.logger.info(f"EHR GET success for ehrid={ehrid}")
    else:
        myresp['status']="failure"
        myresp['text']=response.text   
        myresp['headers']=response.headers     
        current_app.logger.warning(f"EHR GET failure for ehrid={ehrid}")
    myresp['status_code']=response.status_code 
    return myresp


def delehrid(client,adauth,url_base_admin,ehrid):
    current_app.logger.debug('inside delehrid')
    current_app.logger.info(f'Deleting ehr: ehrid={ehrid}')  
    myurl=url_normalize(url_base_admin  + 'ehr/'+ehrid)
    response=client.delete(myurl,headers={'Authorization':adauth },verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        myresp['ehrid']=ehrid
        current_app.logger.info(f'Delete ehr success for template={ehrid}')        
        return myresp
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Delete ehr failure for template={ehrid}')    
        return myresp    


def getehrsub(client,auth,url_base,sid,sna):
    current_app.logger.debug('inside getehrsub')
    current_app.logger.debug(f'sid={sid} sna={sna}')
    myurl=url_normalize(url_base  + 'ehr')
    response=client.get(myurl, params={'subject_id':sid,'subject_namespace':sna},headers={'Authorization':auth, \
            'Content-Type':'application/JSON','Accept': 'application/json','Prefer': 'return={representation|minimal}'},verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    if(response.status_code<210 and response.status_code>199):
        myresp['status']="success"
        # ehrid=response.headers['Location'].split("ehr/")[3]
        ehrid=response.headers['Location'].split('/')[-1]
        myresp["ehrid"]=ehrid
        myresp['text']=response.text
        current_app.logger.info(f"EHR GET success for subject_id={sid} subject_namespace={sna} => ehrid={ehrid}")
    else:
        myresp['status']="failure"
        myresp['text']=response.text   
        myresp['headers']=response.headers       
        current_app.logger.warning(f"EHR GET failure for subject_id={sid} subject_namespace={sna}")  
    myresp['status_code']=response.status_code 
    return myresp

def postehrstatus(client,auth,url_base,uploaded_ehrstatus):
    current_app.logger.debug('inside postehrstatus')
    ehrs = json.loads(uploaded_ehrstatus)
    ehrsjson=json.dumps(ehrs)
    myurl=url_normalize(url_base  + 'ehr')
    response=client.post(myurl,headers={'Authorization':auth,\
        'Content-Type':'application/json','Prefer': 'return=representation'},
        data=ehrsjson,verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'EHR creation.EHR_STATUS POST success')
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'EHR creation.EHR_STATUS POST FAILURE')
    return myresp


def getehrstatus(client,auth,url_base,eid,outtype,vat,vid):
    current_app.logger.debug('inside getehrstatus')
    if outtype=='VAT':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/ehr_status')
        if vat=="":
            response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        else:
            response = client.get(myurl,params={'version_at_time':vat},headers={'Authorization':auth,'Content-Type':'application/json'} ,verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET EHR_STATUS success for ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET EHR_STATUS failure for ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    else: #outtype='VBV'
        if vid=='':
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/ehr_status/')
        else:
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/ehr_status/'+vid)
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET EHR_STATUS success for ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET EHR_STATUS failure for ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers    
        return myresp

def updateehrstatus(client,auth,url_base,ehrfile,eid,vid):
    current_app.logger.debug('inside updateehrstatus')
    myurl=url_normalize(url_base  + 'ehr/'+eid+'/ehr_status')
    ehrstat = json.loads(ehrfile)
    ehrstatusjson=json.dumps(ehrstat)
    response = client.put(myurl,params={'format': 'RAW'},headers={'Authorization':auth,'Content-Type':'application/json', \
            'accept':'application/json','If-Match':vid, \
        'Prefer': 'return=representation'}, data=ehrstatusjson,verify=True) 
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp["status_code"]=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp["status"]="success"
        current_app.logger.info(f"PUT EHR_STATUS success. ehr={eid} versionid={vid}")
    else:
        myresp["status"]="failure"
        current_app.logger.warning(f"PUT EHR_STATUS failure.ehr={eid} versionid={vid}")
    myresp['text']=response.text
    myresp["headers"]=response.headers
    return myresp  


def getehrstatusversioned(client,auth,url_base,eid,outtype,vat,vid):
    current_app.logger.debug('inside getehrstatus')
    if outtype=='INFO':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_ehr_status')
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'} ,verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET EHR_STATUS Versioned success for ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET EHR_STATUS Versioned failure for ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers    
        return myresp
    elif outtype=='REVHIST':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_ehr_status/revision_history')
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET EHR_STATUS Versioned success for ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET EHR_STATUS Versioned failure for ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers    
        return myresp
    elif outtype=='VAT':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_ehr_status/version')
        if vat=="":
            response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        else:
            response = client.get(myurl,params={'version_at_time':vat},headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET EHR_STATUS Versioned success for ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET EHR_STATUS VErsioned failure for ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    else: #outtype='VBV'
        if vid=='':
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_ehr_status/version')
        else:
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_ehr_status/version/'+vid)
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET EHR_STATUS Versioned success for ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET EHR_STATUS Versioned failure for ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers    
        return myresp

def getdir(client,auth,url_base,eid,outtype,vat,vid,path,filetype):
    current_app.logger.debug('inside getehrstatus')
    if outtype=='VAT':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/directory')
        if vat=="":
            if filetype=='JSON':
                response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation','accept':'application/json'} ,verify=True)
            else:
                response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/xml','Prefer':'return=representation',"accept":'application/xml'},verify=True )
        else:
            if filetype=='JSON':
                response = client.get(myurl,params={'version_at_time':vat,'path':path},headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation','accept':'application/json'} ,verify=True)
            else:
                response = client.get(myurl,params={'version_at_time':vat,'path':path},headers={'Authorization':auth,'Content-Type':'application/xml','Prefer':'return=representation',"accept":'application/xml'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            if filetype=='JSON':
                myresp['json']=response.text
            else:
                xmlstringwithencoding=response.text
                positionfirstgreaterthan=xmlstringwithencoding.find('>')
                if 'encoding' in xmlstringwithencoding[0:positionfirstgreaterthan+1]:
                    xmlstring=xmlstringwithencoding[positionfirstgreaterthan+1:]
                else:
                    xmlstring=xmlstringwithencoding
                print(f'xmlstring={xmlstring}')
                root = etree.fromstring(xmlstring)
                myresp['xml']=etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)
            current_app.logger.info(f"GET Directory success for ehrid={eid} outtype={outtype} path={path} filetype={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET Directory failure for ehrid={eid} outtype={outtype} path={path} filetype={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    else: #outtype='VBV'
        if vid=='':
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/directory/')
        else:
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/directory/'+vid)
        if filetype=='JSON':
            response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation','accept':'application/json'} ,verify=True)
        else:
            response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation',"accept":'application/xml'} ,verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            if filetype=='JSON':
                myresp['json']=response.text
            else:
                xmlstringwithencoding=response.text
                positionfirstgreaterthan=xmlstringwithencoding.find('>')
                if 'encoding' in xmlstringwithencoding[0:positionfirstgreaterthan+1]:
                    xmlstring=xmlstringwithencoding[positionfirstgreaterthan+1:]
                else:
                    xmlstring=xmlstringwithencoding
                root = etree.fromstring(xmlstring)
                myresp['xml']=etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)            
            current_app.logger.info(f"GET Directory success for ehrid={eid} outtype={outtype} path={path} filetype={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET Directory failure for ehrid={eid} outtype={outtype} path={path} filetype={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers    
        return myresp

def postdir(client,auth,url_base,eid,uploaded_dir,filetype):
    current_app.logger.debug('inside postdir')
    if filetype=="JSON":
        dir = json.loads(uploaded_dir)
        dirjson=json.dumps(dir)
    else:
        if uploaded_dir.startswith(b'\xef\xbb\xbf'):
            uploaded_dir = uploaded_dir[3:]
        # root=etree.fromstring(uploaded_dir)
        # print(f'dirxml={etree.tostring(root, pretty_print=True).decode()}')
        # uploaded_dir=uploaded_dir.replace(b"\n",b"").lstrip()
        # root=etree.fromstring(uploaded_dir)
        # print(type('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'))
        # print(type(etree.tostring(root)))
        # dirxml=b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+etree.tostring(root)
        # print(f'dirxml={dirxml}')
        root=etree.fromstring(uploaded_dir)
        dirxml=etree.tostring(root)
        print(f'xml given={repr(dirxml)}')
    myurl=url_normalize(url_base  + 'ehr/'+eid+'/directory')
    if filetype=='JSON':  
        response=client.post(myurl,headers={'Authorization':auth,\
        'Content-Type':'application/json','Prefer': 'return=representation', \
            'accept':'application/json'}, \
        data=dirjson,verify=True)
    else:
        response=client.post(myurl,headers={'Authorization':auth,\
        'Content-Type':'application/xml','Prefer': 'return=representation', \
            'accept':'application/xml'}, params={'format': 'XML'},\
        data=dirxml,verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        if filetype=='XML':
            xmlstringwithencoding=response.text
            positionfirstgreaterthan=xmlstringwithencoding.find('>')
            if 'encoding' in xmlstringwithencoding[0:positionfirstgreaterthan+1]:
                xmlstring=xmlstringwithencoding[positionfirstgreaterthan+1:]
            else:
                xmlstring=xmlstringwithencoding
            root = etree.fromstring(xmlstring)
            myresp['xml']=etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)
        else:
            myresp['json']=response.text
        current_app.logger.info(f'Directory FOLDER POST success filetype={filetype}')
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Directory FOLDER POST FAILURE')
    return myresp

def updatedir(client,auth,url_base,eid,vid,uploaded_dir,filetype):
    current_app.logger.debug('inside updatedir')
    dir = json.loads(uploaded_dir)
    dirjson=json.dumps(dir)
    myurl=url_normalize(url_base  + 'ehr/'+eid+'/directory')
    if filetype=='JSON':
        response=client.put(myurl,headers={'Authorization':auth,\
        'Content-Type':'application/json','Prefer': 'return=representation',
        'If-Match':vid,'accept':'application/json'},
        data=dirjson,verify=True)    
    else:
        response=client.put(myurl,headers={'Authorization':auth,\
        'Content-Type':'application/json','Prefer': 'return=representation',
        'If-Match':vid},
        data=dirjson,verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        if filetype=='XML':
            xmlstringwithencoding=response.text
            positionfirstgreaterthan=xmlstringwithencoding.find('>')
            if 'encoding' in xmlstringwithencoding[0:positionfirstgreaterthan+1]:
                xmlstring=xmlstringwithencoding[positionfirstgreaterthan+1:]
            else:
                xmlstring=xmlstringwithencoding
            root = etree.fromstring(xmlstring)
            myresp['xml']=etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)
        else:
            myresp['json']=response.text
        current_app.logger.info(f'Directory FOLDER PUT success')
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Directory FOLDER PUT FAILURE')
    return myresp

def deldiradmin(client,adauth,url_base_admin,eid,did):
    current_app.logger.debug('inside deldiradmin')
    myurl=url_normalize(url_base_admin  + 'ehr/'+eid+'/directory/'+did)
    response = client.delete(myurl,headers={'Authorization':adauth,'Content-Type':'application/json'},verify=True )
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp["status_code"]=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp["status"]="success"
        current_app.logger.info(f"DELETE Directory success for ehrid={eid} id={did}")
    else:
        myresp["status"]="failure"
        current_app.logger.info(f"DELETE Directory failure for ehrid={eid} id={did}")
    myresp['text']=response.text
    myresp["headers"]=response.headers
    return myresp


def deldir(client,auth,url_base,eid,vid):
    current_app.logger.debug('inside deldir')
    myurl=url_normalize(url_base  + 'ehr/'+eid+'/directory')
    response = client.delete(myurl,headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation','accept':'application/json',\
                                            'If-Match':vid},verify=True )
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp["status_code"]=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp["status"]="success"
        current_app.logger.info(f"DELETE Directory success for ehrid={eid} vid={vid}")
    else:
        myresp["status"]="failure"
        current_app.logger.info(f"DELETE Directory failure for ehrid={eid} vid={vid}")
    myresp['text']=response.text
    myresp["headers"]=response.headers
    return myresp



def delcomp(client,adauth,url_base_admin,compid,ehrid):
    #ADMIN DELETE COMPOSITION
    current_app.logger.debug('inside delcomp')
    current_app.logger.info(f'Deleting comp: id={compid}') 
    myurl=url_normalize(url_base_admin+ 'ehr/'+ehrid+'/composition/'+compid)
#    response=client.delete(myurl)
    response=client.delete(myurl,headers={'Authorization':adauth },verify=True)    
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'Delete composition success for id={compid} from ehr={ehrid}. ADMIN method')        
        return myresp
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Delete composition failure for id={compid} from ehr={ehrid}. ADMIN method')    
        return myresp    

def delcompuser(client,auth,url_base,compid,ehrid):
    #USER DELETE COMPOSITION
    current_app.logger.debug('inside delcompuser')
    current_app.logger.info(f'Deleting comp: versionUID={compid}') 
    myurl=url_normalize(url_base  + 'ehr/'+ehrid+'/composition/'+compid)
    response=client.delete(myurl,headers={'Authorization':auth },verify=True)    
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        current_app.logger.info(f'Delete composition success for versionid={compid} from ehr={ehrid}')        
        return myresp
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Delete composition failure for versionid={compid} from ehr={ehrid}')    
        return myresp   


def getcompversioned(client,auth,url_base,compid,eid,outtype,vat,vid):
    current_app.logger.debug('inside getcompversioned')
    if outtype=='INFO':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_composition/'+compid)
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'} ,verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET CompositionVersioned success for compositionid={compid} ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET CompositionVersioned failure for compositionid={compid} ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif outtype=='REVHIST':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_composition/'+compid+'/revision_history')
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET CompositionVersioned success for compositionid={compid} ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET CompositionVersioned failure for compositionid={compid} ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif outtype=='VAT':
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_composition/'+compid+'/version')
        if vat=="":
            response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        else:
            response = client.get(myurl,params={'version_at_time':vat},headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET CompositionVersioned success for compositionid={compid} ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET CompositionVersioned failure for compositionid={compid} ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    else: #outtype='VBV'
        if vid=='':
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_composition/'+compid+'/version')
        else:
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/versioned_composition/'+compid+'/version/'+vid)
        response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            current_app.logger.info(f"GET CompositionVersioned success for compositionid={compid} ehrid={eid} outtype={outtype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET CompositionVersioned failure for compositionid={compid} ehrid={eid} outtype={outtype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers    
        return myresp

def postcomp(client,auth,url_base,url_base_ecis,composition,eid,tid,filetype,check,ehrbase_version):
    current_app.logger.debug('inside postcomp')
    if(filetype=="XML"):
        myurl=url_normalize(url_base + 'ehr/'+eid+'/composition')
        root=etree.fromstring(composition)
        response = client.post(myurl,
                       params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml', \
                           'accept':'application/xml'}, data=etree.tostring(root),verify=True) 
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['Location'].split("composition/")[1]
            current_app.logger.info(f"POST composition success. format={filetype} template={tid}  ehr={eid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo 
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")  
        else:
            current_app.logger.warning(f"POST composition failure. format={filetype} template={tid}  ehr={eid}")
            myresp["status"]="failure"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=="JSON"):
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
        comp = json.loads(composition)
        compositionjson=json.dumps(comp)
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                params={'format': 'JSON'}
            else:#EHRBase version<2.5.0
                params={'format': 'RAW'}
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        response = client.post(myurl,params=params,headers={'Authorization':auth,'Content-Type':'application/json', \
             'accept':'application/json'}, data=compositionjson,verify=True) 
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['Location'].split("composition/")[1]
            current_app.logger.info(f"POST composition success. format={filetype} template={tid}  ehr={eid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"POST composition failure. format={filetype} template={tid}  ehr={eid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp  
    elif(filetype=="STRUCTURED"):   #STRUCTURED
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition')
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        comp = json.loads(composition)
        compositionjson=json.dumps(comp)
        response = client.post(myurl,
                       params={'ehrId':eid,'templateId':tid,'format':'STRUCTURED'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},
                       data=compositionjson,verify=True
                      )           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['Location'].split("composition/")[1]
            current_app.logger.info(f"POST composition success. format={filetype} template={tid}  ehr={eid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"POST composition failure. format={filetype} template={tid}  ehr={eid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=="STRUCTMARAND"):   #STRUCTURED MARAND from Archetype Designer
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition')
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        compMARAND = json.loads(composition)
        compEHRBaseresp = structuredMarand2EHRBase.structuredMarand2EHRBase(compMARAND,client,auth,url_base,url_base_ecis,tid,ehrbase_version)                  
        myresp={}
        if compEHRBaseresp['status']=='failure':
            myresp['status']='failure'
            current_app.logger.warning(f"composition conversion from Structured Marand to Structured EHRBase failure")
            myresp["headers"]=compEHRBaseresp['headers']
            return myresp 
        compositionjson=json.dumps(compEHRBaseresp['composition'])
        current_app.logger.debug('derived structured composition')
        current_app.logger.debug(compositionjson)
        response = client.post(myurl,
                       params={'ehrId':eid,'templateId':tid,'format':'STRUCTURED'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},
                       data=compositionjson,verify=True
                      )    
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)

        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['Location'].split("composition/")[1]
            current_app.logger.info(f"POST composition success. format={filetype} template={tid}  ehr={eid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"POST composition failure. format={filetype} template={tid}  ehr={eid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp    
    else:#FLAT JSON
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition')
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        comp = json.loads(composition)
        compositionjson=json.dumps(comp)
        response = client.post(myurl,
                       params={'ehrId':eid,'templateId':tid,'format':'FLAT'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},
                       data=compositionjson,verify=True
                      )           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['Location'].split("composition/")[1]
            current_app.logger.info(f"POST composition success. format={filetype} template={tid}  ehr={eid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"POST composition failure. format={filetype} template={tid}  ehr={eid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp


def updatecomp(client,auth,url_base,url_base_ecis,composition,eid,tid,compid,filetype,check,ehrbase_version):
    current_app.logger.debug('inside updatecomp')
    versionid=compid
    compid=compid.split('::')[0]
    if(filetype=="XML"):
        myurl=url_normalize(url_base + 'ehr/'+eid+'/composition/'+compid)
        root=etree.fromstring(composition)
        response = client.put(myurl,
                       params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml', \
                           'accept':'application/xml','If-Match':versionid, \
            'Prefer': 'return=representation'}, data=etree.tostring(root),verify=True) 
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['ETag'].replace('"','')
            current_app.logger.info(f"PUT composition success. format={filetype} template={tid} ehr={eid} versionid={versionid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo 
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")  
        else:
            current_app.logger.warning(f"PUT composition failure. format={filetype} template={tid} ehr={eid} versionid={versionid}")
            myresp["status"]="failure"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=="JSON"):
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
        comp = json.loads(composition)
        compositionjson=json.dumps(comp)
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                params={'format': 'JSON'}
            else:#EHRBase version<2.5.0
                params={'format': 'RAW'}
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        response = client.put(myurl,params=params,headers={'Authorization':auth,'Content-Type':'application/json', \
             'accept':'application/json','If-Match':versionid, \
            'Prefer': 'return=representation'}, data=compositionjson,verify=True) 
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['compositionid']=response.headers['ETag'].replace('"','')
            current_app.logger.info(f"PUT composition success. format={filetype} template={tid} ehr={eid} versionid={versionid}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"PUT composition failure. format={filetype} template={tid} ehr={eid} versionid={versionid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp  
    elif(filetype=="STRUCTURED"):   #STRUCTURED
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition/'+compid)
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        comp = json.loads(composition)
        compositionjson=json.dumps(comp)
        response = client.put(myurl,
                       params={'ehrId':eid,'templateId':tid,'format':'STRUCTURED'},
                       headers={'Authorization':auth,'Content-Type':'application/json',\
                                'Prefer':'return=representation',\
                                    'accept':'application/json','If-Match':versionid},
                       data=compositionjson,verify=True
                      )           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
           #doesn't return versionid so we have to update it manually
            try:
                vsplit=versionid.split('::')
                version=int(vsplit[2])
                myresp['compositionid']=vsplit[0]+'::'+vsplit[1]+'::'+str(version+1)
            except:
                myresp['compositionid']=versionid+'+1'
                check='No'
            current_app.logger.info(f"PUT composition success. format={filetype} template={tid} ehr={eid} versionid={myresp['compositionid']}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"PUT composition failure. format={filetype} template={tid} ehr={eid} versionid={versionid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    else:#FLAT JSON
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition/'+compid)
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        comp = json.loads(composition)
        compositionjson=json.dumps(comp)
        response = client.put(myurl,params={'ehrId':eid,'templateId':tid,\
                                            'format':'FLAT'},\
                              headers={'Authorization':auth,'Content-Type':'application/json', \
             'accept':'application/json','If-Match':versionid, \
            'Prefer': 'return=representation'}, data=compositionjson,verify=True)          
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            #doesn't return versionid so we have to update it manually
            try:
                vsplit=versionid.split('::')
                version=int(vsplit[2])
                myresp['compositionid']=vsplit[0]+'::'+vsplit[1]+'::'+str(version+1)
            except:
                myresp['compositionid']=versionid+'+1'
                check='No'
            current_app.logger.info(f"PUT composition success. format={filetype} template={tid} ehr={eid} versionid={myresp['compositionid']}")
            if(check=="Yes"):
                checkinfo= compcheck(client,auth,url_base,url_base_ecis,compositionjson,eid,filetype,myresp['compositionid'])
                if(checkinfo==None):
                    myresp['check']='Retrieved and posted Compositions match'
                    myresp['checkinfo']=""
                    current_app.logger.info(f"check success. Retrieved and posted Compositions match")
                else:
                    myresp['check']='WARNING: Retrieved different from posted Composition'
                    myresp['checkinfo']=checkinfo
                    current_app.logger.warning(f"check failure. Retrieved and posted Compositions do not match")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"PUT composition failure. format={filetype} template={tid} ehr={eid} versionid={versionid}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp


def getcomp(client,auth,url_base,url_base_ecis,compid,eid,filetype,ehrbase_version):
    current_app.logger.debug('inside getcomp')
    if(filetype=="XML"):
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
        #root=etree.fromstring(composition)
        response=client.get(myurl,params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml','accept':'application/xml'},verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        myresp['compositionid']=compid
        myresp['ehrid']=eid
        if(response.status_code<210 and response.status_code>199):
            root = etree.fromstring(response.text)
 #          root.indent(tree, space="\t", level=0)
            myresp['xml'] = etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)
            myresp["status"]="success"
            current_app.logger.info(f"Composition GET success compositionid={compid} ehrid={eid} format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"Composition GET failure compositionid={compid} ehrid={eid} format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=="JSON"):
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
        response = client.get(myurl, params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/json'},verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        myresp['compositionid']=compid
        myresp['ehrid']=eid
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['json']=response.text
            current_app.logger.info(f"GET Composition success for compositionid={compid} ehrid={eid} format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET Composition failure for compositionid={compid} ehrid={eid} format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=='STRUCTURED'):
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition/'+compid)
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        response = client.get(myurl,
                       params={'ehrId':eid,'format':'STRUCTURED'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},
                      verify=True)           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        myresp['compositionid']=compid
        myresp['ehrid']=eid
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            try:
                if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                    myresp['structured']=json.dumps(json.loads(response.text),sort_keys=True, indent=1, separators=(',', ': '))
                else:#EHRBase version<2.5.0
                    myresp['structured']=json.dumps(json.loads(response.text)['composition'],sort_keys=True, indent=1, separators=(',', ': '))
            except myutils.EHRBaseVersion:
                current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
                raise 
            current_app.logger.info(f"GET Composition success for compositionid={compid} ehrid={eid} format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"GET Composition failure for compositionid={compid} ehrid={eid} format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    else:#FLAT JSON
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis  + 'composition/'+compid)
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        response = client.get(myurl,
                       params={'ehrId':eid,'format':'FLAT'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},verify=True
                      )           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        myresp['compositionid']=compid
        myresp['ehrid']=eid
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            try:
                if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                    myresp['flat']=json.dumps(json.loads(response.text),sort_keys=True, indent=1, separators=(',', ': '))
                else:#EHRBase version<2.5.0
                    myresp['flat']=json.dumps(json.loads(response.text)['composition'],sort_keys=True, indent=1, separators=(',', ': '))
            except myutils.EHRBaseVersion:
                current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
                raise 
            current_app.logger.info(f"GET Composition success for compositionid={compid} ehrid={eid} format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"GET Composition failure for compositionid={compid} ehrid={eid} format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp


def postaql(client,auth,url_base,aqltext,qname,version,qtype):
    
    current_app.logger.debug('inside postaql')
    if(qtype==""):
        qtype="AQL"
    if(version==""):
        version="1.0.0"
    aqltext=aqltext.translate({ord(c):' ' for c in '\n\r'})
    # if "'" in aqltext:
    #     aqltext=aqltext.replace("'",'\\\'')
    #aqltext="{'q':'"+aqltext+"'}"
    myurl=url_normalize(url_base  + 'definition/query/'+qname+"/"+version)
    response = client.put(myurl,params={'type':qtype,'format':'RAW'},headers={'Authorization':auth,'Content-Type':'text/plain'},data=aqltext,verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    current_app.logger.debug(f"aqltext={aqltext} qname={qname} qtype={qtype} version={version}")
    myresp={}
    myresp["status_code"]=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp["status"]="success"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        rlocationsplit=myresp['headers']['Location'].split('/')
        rversion=rlocationsplit[-1]
        rname=rlocationsplit[-2]
        myresp['name']=rname
        myresp['version']=rversion
        current_app.logger.info(f"AQL POST success")
    else:
        myresp["status"]="failure"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        current_app.logger.warning("AQL POST failure")
    return myresp

def createPageFromBase4querylist(client,auth,url_base,basefile,targetfile):
    current_app.logger.debug('inside createPageFromBase4querylist')
    myresp={}
    myurl=url_normalize(url_base  + 'definition/query')
    response = client.get(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'},verify=True)
    current_app.logger.debug('Get list queries')
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    if(response.status_code<210 and response.status_code>199):
        myresp['text']=response.text
        myresp['status']='success'
        myresp['headers']=response.headers
        myresp['status_code']=  response.status_code
        results=json.loads(response.text)['versions']
        names=[r['name'] for r in results]
        versions=[r['version'] for r in results]
        
        if(len(names)==0):
            qdata=['No queries available']
        else:
            qdata=[]
            for n,v in zip(names,versions):
                qdata.append(n+'$v'+v)
        myresp['qdata']=qdata
        drmstart=['<select  class="form-select" type="text" id="qdata" name="qdata">']
        drmoptions=['<option>'+q+'</option>' for q in qdata]
        drmstop=['</select>']
        drm=[]
        drm=drmstart+drmoptions+drmstop
        drmstring='\n'.join(drm)
        with open('./templates/'+basefile,'r') as ff:
            lines=ff.readlines()
        with open('./templates/'+targetfile,'w') as fg:
            docopy=True
            for line in lines:
                if('<!--dropdownmenustart-->' in line):
                    docopy=False
                    fg.write(drmstring)
                elif('<!--dropdownmenustop-->' in line):
                    docopy=True
                else:
                    if(docopy):
                        fg.write(line)
        return myresp
    else:
        myresp['text']=response.text
        myresp['status']='failure'
        myresp['headers']=response.headers  
        myresp['status_code']=  response.status_code   
        current_app.logger.warning("GET queries for createPageFromBase4tquerylist failure")
        return myresp   


def getaql(client,auth,url_base,qname,version):
    current_app.logger.debug('inside getaql')
    if(version!=""):
        myurl=url_normalize(url_base  + 'definition/query/'+qname+"/"+version)
    else:
        myurl=url_normalize(url_base  + 'definition/query/'+qname)
    response = client.get(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'},verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    current_app.logger.debug(f"qname={qname} version={version}")
    myresp={}
    myresp["status_code"]=response.status_code
    textok=True
    if 'versions' in response.text:
        if len(json.loads(response.text)['versions'])==0:
            textok=False
    if(response.status_code<210 and response.status_code>199 and textok):
        myresp["status"]="success"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        if ('q' in myresp['text']):
            myresp['aql']=json.loads(myresp['text'])['q']
        current_app.logger.info("AQL GET success")
    else:
        myresp["status"]="failure"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        current_app.logger.warning("AQL GET failure")
    return myresp  


def delaql(client,adauth,url_base_admin,qname,version):
    #ADMIN DELETE STORED QUERY
    current_app.logger.debug('inside delaql')
    if(version!=""):
        myurl=url_normalize(url_base_admin  + 'query/'+qname+"/"+version)
    else:
        myurl=url_normalize(url_base_admin  + 'query/'+qname)
    response = client.delete(myurl,headers={'Authorization':adauth,'Content-Type': 'application/json'},verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    current_app.logger.debug(f"qname={qname} version={version}")
    myresp={}
    myresp["status_code"]=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp["status"]="success"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        current_app.logger.info("AQL DELETE success")
    else:
        myresp["status"]="failure"
        myresp['text']=response.text
        myresp["headers"]=response.headers
        current_app.logger.warning("AQL DELETE failure")
    return myresp  

def runaql(client,auth,url_base,aqltext,qmethod,limit,offset,eid,qparam,qname,version):
    current_app.logger.debug('inside runaql')
    if(aqltext !=""): #PASTED QUERY
        if(qmethod=="GET"):    
            myurl=url_normalize(url_base  + 'query/aql')            
            params={}            
            addlimittoq=''
            if limit != "":
                params['limit']=limit
                addlimittoq=' limit '+limit
                if offset != "":
                    addlimittoq=addlimittoq+' offset '+offset
            #        params['offset']=offset
            # if(offset != ""):
            #     params['offset']=offset
            # if(fetch != ""):
            #     params['fetch']=fetch
            if(eid != ""):
                params['ehrid']=eid
                addeidtoq=' e/ehr_id/value='+"'"+eid+"'"
                if 'where' in aqltext.lower():
                    aqltext=aqltext+' and'+addeidtoq
                else:
                    aqltext=aqltext+' where'+addeidtoq
            aqltext=aqltext+addlimittoq
            if(qparam != ""):
                qplist=qparam.split(",")
                myqp={}
                for qp in qplist:
                    key=qp.split("=")[0]
                    value=qp.split("=")[1]
                    try:
                        val = int(value)
                    except ValueError:
                        val=value
                    myqp[key]=val
                params['query_parameters']=myqp
            params['q']=aqltext
            current_app.logger.debug(f'q={aqltext}')
            current_app.logger.debug(f"params={params}")
            response = client.get(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
                params=params,verify=True)
        else: #POST
            myurl=url_normalize(url_base  + 'query/aql')            
            data={}
            params={}
            addlimittoq=''
            if(limit != ""):
                data['limit']=limit 
                addlimittoq=' limit '+limit
                if offset !="":
                    addlimittoq=addlimittoq+' offset '+offset
            # if(offset != ""):
            #     data['offset']=offset
            # if(fetch != ""):
            #     data['fetch']=fetch
            if( eid !="" or qparam != ""):
                qv={} 
                if(eid != ""):
                    qv['ehrid']=eid
                    addeidtoq=' e/ehr_id/value='+"'"+eid+"'"
                    if 'where' in aqltext.lower():
                        aqltext=aqltext+' and'+addeidtoq
                    else:
                        aqltext=aqltext+' where'+addeidtoq                    
                if(qparam != ""):
                    qplist=qparam.split(",")
                    for qp in qplist:
                        key=qp.split("=")[0]
                        value=qp.split("=")[1]
                        try:
                            val = int(value)
                        except ValueError:
                            val=value
                            qv[key]=val
                data["query_parameters"]=qv 
            aqltext=aqltext+addlimittoq    
            data['q']=aqltext               
            current_app.logger.debug(f"data={data}")
            response = client.post(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
                data=json.dumps(data),verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['text']=response.text
            myresp["headers"]=response.headers
            current_app.logger.info(f"RUN AQL success. qmethod={qmethod}")
        else:
            myresp["status"]="failure"
            myresp['text']=response.text
            myresp["headers"]=response.headers
            current_app.logger.info(f"RUN AQL failure. qmethod={qmethod}")
        return myresp  
    else: #NO QUERY PASSED
        myresp["status"]="failure"
        myresp['text']='No aql query'
        myresp["headers"]=''
        myresp["status_code"]='500'
        return myresp
        # if(qmethod=="GET"):  
        #     myurl=url_normalize(EHR_SERVER_BASE_URL  + 'query/'+qname+"/"+version)            
        #     params={}
        #     if(limit != ""):
        #         params['limit']=limit             
        #     # if(offset != ""):
        #     #     params['offset']=offset
        #     # if(fetch != ""):
        #     #     params['fetch']=fetch
        #     if(eid != ""):
        #         params['ehrid']=eid
        #     if(qparam != ""):
        #         qplist=qparam.split(",")
        #         myqp={}
        #         for qp in qplist:
        #             key=qp.split("=")[0]
        #             value=qp.split("=")[1]
        #             try:
        #                 val = int(value)
        #             except ValueError:
        #                 val=value
        #             myqp[key]=val
        #         params["query_parameters"]=myqp
        #     current_app.logger.debug(f"params={params}")
        #     response = client.get(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
        #         params=params,verify=True)
        # else: #POST
        #     myurl=url_normalize(EHR_SERVER_BASE_URL   + 'query/'+qname+"/"+version)       
        #     data={}
        #     if(limit != ""):
        #         data['limit']=limit 
        #     # if(offset != ""):
        #     #     data['offset']=offset
        #     # if(fetch != ""):
        #     #     data['fetch']=fetch
        #     if( eid !="" or qparam != ""):
        #         qv={} 
        #         if(eid != ""):
        #             qv['ehrid']=eid
        #         if(qparam != ""):
        #             qplist=qparam.split(",")
        #             for qp in qplist:
        #                 key=qp.split("=")[0]
        #                 value=qp.split("=")[1]
        #                 try:
        #                     val = int(value)
        #                 except ValueError:
        #                     val=value
        #                     qv[key]=val
        #         data["query_parameters"]=qv
        #     current_app.logger.debug(f"data={data}")
        #     response = client.post(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
        #         data=json.dumps(data),verify=True )
        # current_app.logger.debug('Response Url')
        # current_app.logger.debug(response.url)
        # current_app.logger.debug('Response Status Code')
        # current_app.logger.debug(response.status_code)
        # current_app.logger.debug('Response Text')
        # current_app.logger.debug(response.text)
        # current_app.logger.debug('Response Headers')
        # current_app.logger.debug(response.headers)
        # myresp={}
        # myresp["status_code"]=response.status_code
        # if(response.status_code<210 and response.status_code>199):
        #     myresp["status"]="success"
        #     myresp['text']=response.text
        #     myresp["headers"]=response.headers
        #     current_app.logger.info(f"RUN stored AQL success. qmethod={qmethod} qname={qname} version={version}")
        # else:
        #     myresp["status"]="failure"
        #     myresp['text']=response.text
        #     myresp["headers"]=response.headers
        #     current_app.logger.warning(f"RUN stored AQL failure. qmethod={qmethod} qname={qname} version={version}")
        # return myresp  



def compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,compid):
    current_app.logger.debug('      inside compcheck')
    if(filetype=="XML"):
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
        response=client.get(myurl,params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml','accept':'application/xml'},verify=True)
        origcompositiontree=etree.fromstring(composition)
        if(response.status_code<210 and response.status_code>199):
            retrievedcompositiontree= etree.fromstring(response.text)
            comparison_results=myutils.compare_xmls(origcompositiontree,retrievedcompositiontree)
            ndiff=myutils.analyze_comparison_xml(comparison_results)
            if(ndiff>0):
                return comparison_results
            else:
                return None            
    elif(filetype=="JSON"):
        myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition/'+compid)
        response = client.get(myurl, params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/json'} ,verify=True)
        origcomposition=json.loads(composition)
        if(response.status_code<210 and response.status_code>199):       
            retrievedcomposition=json.loads(response.text)
            origchanged=myutils.change_naming(origcomposition)
            retrchanged=myutils.change_naming(retrievedcomposition)
            comparison_results=myutils.compare_jsons(origchanged,retrchanged)
            ndiff=myutils.analyze_comparison_json(comparison_results)
            if(ndiff>0):
                return comparison_results
            else:
                return None  
    elif(filetype=='STRUCTURED'):
        myurl=url_normalize(url_base_ecis  + 'composition/'+compid)
        response = client.get(myurl,
                       params={'ehrId':eid,'format':'STRUCTURED'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},verify=True
                      )           
        origcomposition=json.loads(composition)
        if(response.status_code<210 and response.status_code>199):
            retrievedcomposition=json.loads(response.text)['composition']
            origchanged=myutils.change_naming(origcomposition)
            retrchanged=myutils.change_naming(retrievedcomposition)
            comparison_results=myutils.compare_jsons(origchanged,retrchanged)
            ndiff=myutils.analyze_comparison_json(comparison_results)
            if(ndiff>0):
                return comparison_results
            else:
                return None                        
    else:
        myurl=url_normalize(url_base_ecis  + 'composition/'+compid)
        response = client.get(myurl,
                       params={'ehrId':eid,'format':'FLAT'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},verify=True
                      )           
        origcomposition=json.loads(composition)
        if(response.status_code<210 and response.status_code>199):
            retrievedcomposition=json.loads(response.text)['composition']
            origchanged=myutils.change_naming(origcomposition)
            retrchanged=myutils.change_naming(retrievedcomposition)
            comparison_results=myutils.compare_jsons(origchanged,retrchanged)
            ndiff=myutils.analyze_comparison_json(comparison_results)
            if(ndiff>0):
                return comparison_results
            else:
                return None
            
    
    
def get_dashboard_info(client,auth,url_base,adauth,url_base_management):
    current_app.logger.debug('inside get_dashboard info')         
    #get aql stored
    myresp={}
    myresp['status']='failure'
    myurl=url_normalize(url_base  + 'definition/query/')
    responseaql = client.get(myurl, headers={'Authorization':auth,'Content-Type': 'application/json'},verify=True)                     
    current_app.logger.debug('Get AQL stored')
    current_app.logger.debug('Response Url')
    current_app.logger.debug(responseaql.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(responseaql.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(responseaql.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(responseaql.headers)
    if(responseaql.status_code<210 and responseaql.status_code>199):
        resultsaql=json.loads(responseaql.text)['versions']
        myresp['aql']=len(resultsaql) 
        myresp['status']='success1'
        myresp['success1']=True
        current_app.logger.debug('Dashboard: GET AQL stored success')
    else:
        myresp['success1']=False
        myresp['text']=responseaql.text
        myresp['headers']=responseaql.headers
        current_app.logger.warning("Dashboard: GET AQL failure")
        #return myresp
    # get total ehrs  
    myurl=url_normalize(url_base  + 'query/aql')
    data={}
    aqltext="select e/ehr_id/value FROM EHR e"
    data['q']=aqltext
    response = client.post(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
                data=json.dumps(data) ,verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)  
    if(response.status_code<210 and response.status_code>199):
        results=json.loads(response.text)['rows']
        myresp['ehr']=len(results) 
        myresp['status']='success2'
        myresp['success2']=True
        current_app.logger.debug('Dashboard: GET list ehrs success')
    else:
        myresp['success2']=False
        myresp['text']=response.text
        myresp['headers']=response.headers
        current_app.logger.warning('Dashboard: GET list ehrs failure')
        #return myresp

    #get ehrid,compid, templateid list
    myurl=url_normalize(url_base  + 'query/aql')
    data={}
    aqltext="select e/ehr_id/value,c/uid/value,c/archetype_details/template_id/value from EHR e contains COMPOSITION c"
    data['q']=aqltext
    response = client.post(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
                data=json.dumps(data),verify=True )
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
  
    if(response.status_code<210 and response.status_code>199):
        results=json.loads(response.text)['rows']
        myresp['composition']=len(results)
        myresp['status']='success3'
        myresp['success3']=True
        current_app.logger.debug('Dashboard: GET list ehrs,compositions,templates used success')
    else:
        myresp['success3']=False
        myresp['text']=response.text
        myresp['headers']=response.headers
        current_app.logger.warning('Dashboard: GET list ehrs,compositions,templates used failure')
        #return myresp 
    #calculate total ehr in use    
    ehr=set(r[0] for r in results)
    myresp['uehr']=len(ehr)     
    #total templates in use
    templates_in_use=set(r[2] for r in results)
    myresp['utemplate']=len(templates_in_use)     
    #get templates
    myurl=url_normalize(url_base  + 'definition/template/adl1.4')
    response2=client.get(myurl,params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/XML'},verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response2.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response2.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response2.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response2.headers)
  
    if(response2.status_code<210 and response2.status_code>199):
        current_app.logger.debug(f"Dashboard: GET all templates success")
        resultstemp=json.loads(response2.text)
        myresp['template']=len(resultstemp)
        templates=[rt['template_id'] for rt in resultstemp]
        myresp['status']='success4'
        myresp['success4']=True
        #compositions per ehr
        c=[0]*len(ehr)
        for i,e in enumerate(ehr):
            c[i]=0
            for r in results:
                if(r[0]==e):
                    c[i]+=1
        cpe={i:c.count(i) for i in c}
        #compositions per template
        d={}
        for i,t in enumerate(templates_in_use):
            for r in results:
                if(r[2]==t):
                    if t in d:
                        d[t]+=1
                    else:
                        d[t]=1
                
        #fill bar and pie variables
        myresp['bar_label']=list(cpe.keys())
        myresp['bar_value']=list(cpe.values())  
        myresp['bar_max']=max(myresp['bar_value'],default=0)      
        myresp['pie_label']=list(d.keys())
        myresp['pie_value']=list(d.values())
    else:
        myresp['success4']=False
        current_app.logger.warning(f"Dashboard: Get all templates failure")
        myresp['text']=response2.text
        myresp['headers']=response2.headers
        #return myresp               

#   additional info from management/env management/info if available and admin credentials provided
# The first,second,third,fourth and sixth for env,info in .env.ehrbase must be set 
#MANAGEMENT_ENDPOINTS_WEB_EXPOSURE=env,health,info,metrics,prometheus
#MANAGEMENT_ENDPOINTS_WEB_BASEPATH=/management
#MANAGEMENT_ENDPOINT_ENV_ENABLED=true
#MANAGEMENT_ENDPOINT_HEALTH_ENABLED=true
#MANAGEMENT_ENDPOINT_HEALTH_DATASOURCE_ENABLED=true
#MANAGEMENT_ENDPOINT_INFO_ENABLED=true
#MANAGEMENT_ENDPOINT_METRICS_ENABLED=true
#MANAGEMENT_ENDPOINT_ENV_SHOWVALUES=ALWAYS
    if(adauth!=""):        
        myurl=url_normalize(url_base_management+'info')
        resp = client.get(myurl,headers={'Authorization':adauth,'Content-Type':'application/JSON'},verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(resp.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(resp.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(resp.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(resp.headers)     
        if(resp.status_code<210 and resp.status_code>199):
            current_app.logger.debug("Dashboard: GET management info success")

            
            current_app.logger.debug(f'INFOOOOOOOO: {json.loads(resp.text)}')

            myresp['status']='success5'
            myresp['success5']=True
            # info=json.loads(resp.text)['build']
            # myinfo={}
            # myinfo['openehr_sdk']=info['openEHR_SDK']['version']
            # myinfo['ehrbase_version']=info['version']
            # myinfo['archie']=info['archie']['version']
            # myresp['info']=myinfo
            myresp['info']=json.loads(resp.text)
        else:
            myresp['success5']=False
            current_app.logger.warning("Dashboard: GET management info failure")
            myresp['text']=resp.text
            myresp['headers']=resp.headers
            #return myresp 
    
        myurl=url_normalize(url_base_management+'env')
        resp2 = client.get(myurl,headers={'Authorization':adauth,'Content-Type':'application/JSON'},verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(resp2.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(resp2.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(resp2.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(resp2.headers)         
        if(resp2.status_code<210 and resp2.status_code>199):
            current_app.logger.debug("Dashboard: GET management env success")
            env=json.loads(resp2.text)

            current_app.logger.debug(f'ENVVVVVV {env}')

            

            myresp['status']='success6'
            myresp['success6']=True
            myresp['env0']=env['propertySources'][0]
            myresp['env1']=env['propertySources'][1]
            myresp['env2']=env['propertySources'][2]
            myresp['env3']=env['propertySources'][3]
            myresp['env4']=env['propertySources'][4]
            myresp['env5']=env['propertySources'][5]

        #     myenv={}
        #     myenv["activeProfiles"]=env["activeProfiles"]    
        #     myenv['Java']= env["propertySources"][2]["properties"]["java.specification.vendor"]["value"] + " " \
        #                     + env["propertySources"][2]['properties']["java.home"]["value"] 
        #     myenv['JavaVM']=   env["propertySources"][2]['properties']["java.vm.name"]["value"]+ \
        #                 " "+ env["propertySources"][2]['properties']['java.vm.vendor']['value'] + \
        #                 " " + env["propertySources"][2]['properties']["java.vm.version"]["value"]                                
        #     myenv["OS"]=env["propertySources"][2]['properties']['os.name']['value'] +  \
        #             " "+ env["propertySources"][2]['properties']["os.arch"]["value"]+ \
        #             " "+  env["propertySources"][2]['properties']["os.version"]["value"] 
        #     myresp['env']=myenv
        #     gen_properties={}
        #     end_properties={}
        #     gen_properties["CACHE_ENABLED"]=env["propertySources"][3]["properties"]["CACHE_ENABLED"]["value"]
        #     end_properties["MANAGEMENT_ENDPOINTS_WEB_EXPOSURE"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINTS_WEB_EXPOSURE"]
        #     end_properties["MANAGEMENT_ENDPOINTS_WEB_BASEPATH"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINTS_WEB_BASEPATH"]
        #     end_properties["MANAGEMENT_ENDPOINT_INFO_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_INFO_ENABLED"]
        #     end_properties["MANAGEMENT_ENDPOINT_PROMETHEUS_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_PROMETHEUS_ENABLED"]
        #     end_properties["MANAGEMENT_ENDPOINT_HEALTH_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_HEALTH_ENABLED"]
        #     end_properties["MANAGEMENT_ENDPOINT_METRICS_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_METRICS_ENABLED"]
        #     end_properties["MANAGEMENT_ENDPOINT_ENV_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_ENV_ENABLED"]
        #     end_properties["MANAGEMENT_ENDPOINT_HEALTH_PROBES_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_HEALTH_PROBES_ENABLED"]
        #     end_properties["MANAGEMENT_ENDPOINT_HEALTH_DATASOURCE_ENABLED"]=env["propertySources"][3]["properties"]["MANAGEMENT_ENDPOINT_HEALTH_DATASOURCE_ENABLED"]
        #     myresp['end_properties']=end_properties
        #     db={}
        #     db["username"]=env["propertySources"][3]["properties"]["DB_USER"]["value"]
        #     db["password"]=env["propertySources"][3]["properties"]["DB_PASS"]["value"]
        #     db["url"]=env["propertySources"][3]["properties"]["DB_URL"]["value"]
        #     myresp["db"]=db
        #     aql={}
        #     if "ENV_AQL_ARRAY_DEPTH" in env["propertySources"][3]["properties"]:
        #         aql["ENV_AQL_ARRAY_DEPTH"]=env["propertySources"][3]["properties"]["ENV_AQL_ARRAY_DEPTH"]["value"]
        #         aql["ENV_AQL_ARRAY_IGNORE_NODE"]=env["propertySources"][3]["properties"]["ENV_AQL_ARRAY_IGNORE_NODE"]["value"]
        #         aql["ENV_AQL_ARRAY_DEPTH"]=env["propertySources"][3]["properties"]["ENV_AQL_ARRAY_DEPTH"]["value"]
        #         aql["ENV_AQL_ARRAY_IGNORE_NODE"]=env["propertySources"][3]["properties"]["ENV_AQL_ARRAY_IGNORE_NODE"]["value"]
        #     else:
        #         aql["ENV_AQL_ARRAY_DEPTH"]='Unknown'
        #         aql["ENV_AQL_ARRAY_IGNORE_NODE"]='Unknown'
        #         aql["ENV_AQL_ARRAY_DEPTH"]='Unknown'
        #         aql["ENV_AQL_ARRAY_IGNORE_NODE"]='Unknown'

        #     current_app.logger.debug(f'PROPERTIES={env["propertySources"]}')
 
        #     if "server.aqlConfig.useJsQuery" in env["propertySources"][4]["properties"]:
        #         aql["server.aqlConfig.useJsQuery"]=env["propertySources"][4]["properties"]["server.aqlConfig.useJsQuery"]["value"]
        #         aql["server.aqlConfig.ignoreIterativeNodeList"]=env["propertySources"][4]['properties']["server.aqlConfig.ignoreIterativeNodeList"]["value"]
        #         aql["server.aqlConfig.iterationScanDepth"]=env["propertySources"][4]['properties']["server.aqlConfig.iterationScanDepth"]["value"]
        #         myresp["aqlinfo"]=aql
        #     elif "spring.datasource.url" in env["propertySources"][4]["properties"]: #version 2.0.0 upwards
        #         myresp["aqlinfo"]={}
        #         springinfo={}
        #         # springinfo['security.authType']=env["propertySources"][3]['properties']['security.authType']['value']
        #         # springinfo['spring.flyway.user']=env["propertySources"][3]['properties']['spring.flyway.user']['value']
        #         # springinfo['spring.flyway.password']=env["propertySources"][3]['properties']['spring.flyway.password']['value']
        #         # springinfo['spring.flyway.schemas']=env["propertySources"][3]['properties']['spring.flyway.schemas']['value']
        #         # springinfo['spring.datasource.url']=env["propertySources"][3]['properties']['spring.datasource.url']['value']
        #         # springinfo['spring.datasource.username']=env["propertySources"][3]['properties']['spring.datasource.username']['value']
        #         # springinfo['spring.datasource.password']=env["propertySources"][3]['properties']['spring.datasource.url']['value']
        #         # springinfo['spring.datasource.hikari.minimum-idle']=env["propertySources"][3]['properties']['spring.datasource.hikari.minimum-idle']['value']
        #         # springinfo['spring.datasource.hikari.maximum-pool-size']=env["propertySources"][3]['properties']['spring.datasource.hikari.maximum-pool-size']['value']
        #         # springinfo['spring.datasource.hikari.max-lifetime']=env["propertySources"][3]['properties']['spring.datasource.hikari.max-lifetime']['value']
        #         # myresp["springinfo"]=springinfo
                
        #     gen_properties["SERVER_NODENAME"]=env["propertySources"][3]['properties']["SERVER_NODENAME"]["value"]
        #     gen_properties["HOSTNAME"]=env["propertySources"][3]['properties']["HOSTNAME"]["value"]
        #     gen_properties["LANG"]=env["propertySources"][3]['properties']["LANG"]["value"]
        #     gen_properties["SECURITY_AUTHTYPE"]=env["propertySources"][3]['properties']["SECURITY_AUTHTYPE"]["value"]
        #     if( "SYSTEM_ALLOW_TEMPLATE_OVERWRITE") in env["propertySources"][3]['properties']:
        #         gen_properties["SYSTEM_ALLOW_TEMPLATE_OVERWRITE"]=env["propertySources"][3]['properties']["SYSTEM_ALLOW_TEMPLATE_OVERWRITE"]["value"]
        #     else:
        #         gen_properties["SYSTEM_ALLOW_TEMPLATE_OVERWRITE"]='Unknown'
        #     myresp["gen_properties"]=gen_properties
        #     terminology={}
        #     terminology["validation.external-terminology.enabled"]=env["propertySources"][5]['properties']["validation.external-terminology.enabled"]["value"]
        #     # terminology["validation.external-terminology.provider.fhir.type"]=env["propertySources"][5]['properties']["validation.external-terminology.provider.fhir.type"]["value"]
        #     # terminology["validation.external-terminology.provider.fhir.url"]=env["propertySources"][5]['properties']["validation.external-terminology.provider.fhir.url"]["value"]
        #     myresp["terminology"]=terminology
        #     plugin={}
        #     plugin["plugin-manager.plugin-dir"]=env["propertySources"][5]['properties']["plugin-manager.plugin-dir"]["value"]
        #     plugin["plugin-manager.plugin-config-dir"]=env["propertySources"][5]['properties']["plugin-manager.plugin-config-dir"]["value"]
        #     plugin["plugin-manager.enable"]=env["propertySources"][5]['properties']["plugin-manager.enable"]["value"]
        #     plugin["plugin-manager.plugin-context-path"]=env["propertySources"][5]['properties']["plugin-manager.plugin-context-path"]["value"]
        #     myresp['plugin']=plugin   
        else:
            myresp['success6']=False
            current_app.logger.warning(f"Dashboard: GET management env failure")
            myresp['text']=resp2.text
            myresp['headers']=resp2.headers
            #return myresp 
    
        myurl=url_normalize(url_base_management  + 'health')
        resp3 = client.get(myurl,headers={'Authorization':adauth,'Content-Type':'application/JSON'},verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(resp3.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(resp3.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(resp3.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(resp3.headers)       
        if(resp3.status_code<210 and resp3.status_code>199) or resp3.status_code==503:
            current_app.logger.info("Dashboard: GET management health success")

            current_app.logger.debug(f'HEALTHHHHH {json.loads(resp3.text)}')


            health=json.loads(resp3.text)
            # myresp["db"]["db"]=health["components"]["db"]["details"]["database"]
            #disk={}
            #disk["total_space"]=health["components"]["diskSpace"]["details"]["total"]
            #disk["free_space"]=health["components"]["diskSpace"]["details"]["free"]
            #myresp["disk"]=disk
            myresp['status']='success7'
            myresp['health']=health
            myresp['success7']=True
        else:
            myresp['success7']=False
            current_app.logger.warning("Dashboard: GET management health failure")
            myresp['text']=resp3.text
            myresp['headers']=resp3.headers
            #return myresp             
        return myresp


def postbatch1(client,auth,url_base,url_base_ecis,uploaded_files,tid,check,sidpath,snamespace,filetype,myrandom,comps,inlist,ehrbase_version):
    current_app.logger.debug('inside postbatch1')
    ehrslist=[]
    number_of_files=len(uploaded_files)
    if(inlist==True):          
        myurl=url_normalize(url_base  + 'query/aql')
        data={}
        aqltext="select e/ehr_id/value FROM EHR e"
        data['q']=aqltext
        response = client.post(myurl,headers={'Authorization':auth,'Content-Type': 'application/json'}, \
                data=json.dumps(data),verify=True )
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        if(response.status_code<210 and response.status_code>199):
            current_app.logger.debug("Postbatch1: get all Ehrs success")
            results=json.loads(response.text)['rows']
            ehrslist=[r[0] for r in results]       
            if len(ehrslist)==0:
                inlist=False
    if(filetype=="XML"):
        succ=0
        csucc=0
        compids=[]
        eids=[]
        myresp={}
        filenamefailed=[]
        filenamecheckfailed=[]
        for uf,composition in zip(uploaded_files,comps):
            root=etree.fromstring(composition)
            #create EHRID
            if(myrandom):
                sid=randomstring()
                sna='fakenamespace'
            else:
                sna=snamespace
                sid=findpath(filetype,sidpath,composition)
                current_app.logger.debug(f'sid found={sid}')
                if(sid==-1):
                    current_app.logger.warning(f"Chosen field={sidpath} not found in file. Couldn't obtain a valid subject_id")
                    myresp['status']='failed'
                    myresp['error']='Error while getting the SubjectID. Chosen Field not found in file' + uf.filename
                    myresp['success']=succ
                    myresp['csuccess']=csucc
                    myresp['filenamefailed']=filenamefailed
                    myresp['filenamecheckfailed']=filenamecheckfailed
                    myresp['compositionid']=compids
                    myresp['ehrid']=eids
                    return myresp
            eid=""
            if(inlist==False):
                resp10=createehrsub(client,auth,url_base,sid,sna,eid)
                if(resp10['status']!='success'):
                    if(resp10['status_code']==409 and 'Specified party has already an EHR set' in json.loads(resp10['text'])['message']):
                        #get ehr summary by subject_id , subject_namespace
                        payload = {'subject_id':sid,'subject_namespace':sna}
                        ehrs = client.get(url_base + 'ehr',  params=payload,headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json'},verify=True)
                        eid=json.loads(ehrs.text)["ehr_id"]["value"]
                        current_app.logger.debug('ehr already existent')
                        eids.append(eid)
                        current_app.logger.debug(f'Patient {sid}: retrieved ehrid={eid}')
                else:
                    eid=resp10['ehrid']
                    eids.append(eid)
            else:
                eid=random.choice(ehrslist)
                eids.append(eid)
            myurl=url_normalize(url_base + 'ehr/'+eid+'/composition')
            response = client.post(myurl,
                       params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml', \
                           'accept':'application/xml'}, data=etree.tostring(root),verify=True) 
            current_app.logger.debug('Response Url')
            current_app.logger.debug(response.url)
            current_app.logger.debug('Response Status Code')
            current_app.logger.debug(response.status_code)
            current_app.logger.debug('Response Text')
            current_app.logger.debug(response.text)
            current_app.logger.debug('Response Headers')
            current_app.logger.debug(response.headers)
            if(response.status_code<210 and response.status_code>199):
                succ+=1
                cid=response.headers['Location'].split("composition/")[1]
                compids.append(cid)
                current_app.logger.info(f'postbatch1: POST success composition={cid} format={filetype} filename={uf.filename} ehrid={eid}')
                if(check=="Yes"):
                    checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,cid)
                    if(checkinfo==None):
                        csucc+=1
                        current_app.logger.info(f'postbatch1: successfully checked composition={cid} filename={uf.filename} ehrid={eid}')
                    else:
                        filenamecheckfailed.append(uf.filename)
                        current_app.logger.warning(f'postbatch1: unsuccessfully checked composition={cid} filename={uf.filename} ehrid={eid}')
            else:
                filenamefailed.append(uf.filename)
                current_app.logger.warning(f'postbatch1: POST failure filename={uf.filename} ehrid={eid}')
        if(check=='Yes'):
            current_app.logger.info(f"{csucc}/{number_of_files} files successfully POSTed and checked")
            if(csucc==number_of_files):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        else:
            current_app.logger.info(f"{succ}/{number_of_files} files successfully POSTed")
            if(succ==number_of_files):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        myresp['ehrid']=eids
        myresp['compositionid']=compids
        myresp['nsuccess']=succ
        myresp['csuccess']=csucc
        myresp['filenamefailed']=filenamefailed
        myresp['filenamecheckfailed']=filenamecheckfailed
        myresp['error']=""
        return myresp
    elif(filetype=="JSON"):
        succ=0
        csucc=0
        eids=[]
        compids=[]
        myresp={}
        filenamefailed=[]
        filenamecheckfailed=[]
        for uf,composition in zip(uploaded_files,comps):
#            uf.stream.seek(0)
#            composition=uf.read()
            comp = json.loads(composition)
            compositionjson=json.dumps(comp)
            #create EHRID
            if(myrandom):
                sid=randomstring()
                sna='fakenamespace'
            else:
                sna=snamespace
                sid=findpath(filetype,sidpath,comp)
                current_app.logger.debug(f'sid found={sid}')
                if(sid==-1):
                    current_app.logger.warning(f"Chosen field={sidpath} not found in file. Couldn't obtain a valid subject_id")
                    myresp['status']='failed'
                    myresp['error']='Error while getting the SubjectID. Chosen Field not found in file' + uf.filename
                    myresp['nsuccess']=succ
                    myresp['csuccess']=csucc
                    myresp['filenamefailed']=filenamefailed
                    myresp['filenamecheckfailed']=filenamecheckfailed
                    myresp['compositionid']=compids
                    myresp['ehrid']=eids
                    return myresp
            eid=""
            if(inlist==False):            
                resp10=createehrsub(client,auth,url_base,sid,sna,eid)
                if(resp10['status']!='success'):
                    if(resp10['status_code']==409 and 'Specified party has already an EHR set' in json.loads(resp10['text'])['message']):
                        #get ehr summary by subject_id , subject_namespace
                        payload = {'subject_id':sid,'subject_namespace':sna}
                        ehrs = client.get(url_base + 'ehr',  params=payload,headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json'},verify=True)
                        eid=json.loads(ehrs.text)["ehr_id"]["value"]
                        current_app.logger.debug('ehr already existent')
                        eids.append(eid)
                        current_app.logger.debug(f'Patient {sid}: retrieved ehrid={eid}')
                else:
                    eid=resp10['ehrid']
                    eids.append(eid)
            else:
                eid=random.choice(ehrslist)
                eids.append(eid)                  
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
            try:
                if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                    params={'format': 'JSON'}
                else:#EHRBase version<2.5.0
                    params={'format': 'RAW'}
            except myutils.EHRBaseVersion:
                current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
                raise             
            response = client.post(myurl,params=params,headers={'Authorization':auth,'Content-Type':'application/json', \
             'accept':'application/json'}, data=compositionjson,verify=True)   
            current_app.logger.debug('Response Url')
            current_app.logger.debug(response.url)
            current_app.logger.debug('Response Status Code')
            current_app.logger.debug(response.status_code)
            current_app.logger.debug('Response Text')
            current_app.logger.debug(response.text)
            current_app.logger.debug('Response Headers')
            current_app.logger.debug(response.headers)
            if(response.status_code<210 and response.status_code>199):
                succ+=1
                cid=response.headers['Location'].split("composition/")[1]
                compids.append(cid)
                current_app.logger.info(f'postbatch1: POST success composition={cid} format={filetype} filename={uf.filename} ehrid={eid}')
                if(check=="Yes"):
                    checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,cid)
                    if(checkinfo==None):
                        csucc+=1
                        current_app.logger.info(f'postbatch1: successfully checked composition={cid} filename={uf.filename} ehrid={eid}')
                    else:
                        filenamecheckfailed.append(uf.filename)
                        current_app.logger.warning(f'postbatch1: unsuccessfully checked composition={cid} filename={uf.filename} ehrid={eid}')
            else:
                filenamefailed.append(uf.filename)
                current_app.logger.warning(f'postbatch1: POST failure filename={uf.filename} ehrid={eid}')
        if(check=='Yes'):
            current_app.logger.info(f"{csucc}/{number_of_files} files successfully POSTed and checked")
            if(csucc!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        else:
            current_app.logger.info(f"{succ}/{number_of_files} files successfully POSTed")
            if(succ!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        myresp['ehrid']=eids                
        myresp['compositionid']=compids
        myresp['nsuccess']=succ
        myresp['csuccess']=csucc
        myresp['filenamefailed']=filenamefailed
        myresp['filenamecheckfailed']=filenamecheckfailed
        myresp['error']=""
        return myresp

    else:#FLAT JSON
        succ=0
        csucc=0
        compids=[]
        eids=[]
        myresp={}
        filenamefailed=[]
        filenamecheckfailed=[]
        for uf,composition in zip(uploaded_files,comps):
            comp = json.loads(composition)
            compositionjson=json.dumps(comp) 
            #create EHRID
            if(myrandom):
                sid=randomstring()
                sna='fakenamespace'
            else:
                sna=snamespace
                sid=findpath(filetype,sidpath,comp)
                current_app.logger.debug(f'sid found={sid}')
                if(sid==-1):
                    current_app.logger.warning(f"Chosen field={sidpath} not found in file. Couldn't obtain a valid subject_id")
                    myresp['status']='failed'
                    myresp['error']='Error while getting the SubjectID. Chosen Field not found in file' + uf.filename
                    myresp['nsuccess']=succ
                    myresp['csuccess']=csucc
                    myresp['filenamefailed']=filenamefailed
                    myresp['filenamecheckfailed']=filenamecheckfailed
                    myresp['compositionid']=compids
                    myresp['ehrid']=eids
                    return myresp
            eid=""
            if(inlist==False):
                resp10=createehrsub(client,auth,url_base,sid,sna,eid)
                if(resp10['status']!='success'):
                    if(resp10['status_code']==409 and 'Specified party has already an EHR set' in json.loads(resp10['text'])['message']):
                        #get ehr summary by subject_id , subject_namespace
                        payload = {'subject_id':sid,'subject_namespace':sna}
                        ehrs = client.get(url_base + 'ehr',  params=payload,headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json'},verify=True)
                        eid=json.loads(ehrs.text)["ehr_id"]["value"]
                        current_app.logger.debug('ehr already existent')
                        eids.append(eid)
                        current_app.logger.debug(f'Patient {sid}: retrieved ehrid={eid}')
                else:
                    eid=resp10['ehrid']
                    eids.append(eid)
            else:
                eid=random.choice(ehrslist)
                eids.append(eid)                    
            try:
                if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                    myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
                else:#EHRBase version<2.5.0
                    myurl=url_normalize(url_base_ecis  + 'composition')
            except myutils.EHRBaseVersion:
                current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
                raise 
            response = client.post(myurl,
                       params={'ehrId':eid,'templateId':tid,'format':'FLAT'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=minimal'},
                       data=compositionjson,verify=True
                      )
            current_app.logger.debug('Response Url')
            current_app.logger.debug(response.url)
            current_app.logger.debug('Response Status Code')
            current_app.logger.debug(response.status_code)
            current_app.logger.debug('Response Text')
            current_app.logger.debug(response.text)
            current_app.logger.debug('Response Headers')
            current_app.logger.debug(response.headers)
            if(response.status_code<210 and response.status_code>199):
                succ+=1
                cid=response.headers['Location'].split("composition/")[1]
                compids.append(cid)
                current_app.logger.info(f'postbatch1: POST success composition={cid} format={filetype} filename={uf.filename} ehrid={eid}')                
                if(check=="Yes"):
                    checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,cid)
                    if(checkinfo==None):
                        csucc+=1
                        current_app.logger.info(f'postbatch1: successfully checked composition={cid} filename={uf.filename} ehrid={eid}')
                    else:
                        filenamecheckfailed.append(uf.filename)
                        current_app.logger.warning(f'postbatch1: unsuccessfully checked composition={cid} filename={uf.filename} ehrid={eid}')
            else:
                filenamefailed.append(uf.filename)
                current_app.logger.warning(f'postbatch1: POST failure filename={uf.filename} ehrid={eid}')
        if(check=='Yes'):
            current_app.logger.info(f"{csucc}/{number_of_files} files successfully POSTed and checked")
            if(csucc!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        else:
            current_app.logger.info(f"{succ}/{number_of_files} files successfully POSTed and checked")
            if(succ!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        myresp['ehrid']=eids
        myresp['compositionid']=compids           
        myresp['nsuccess']=succ
        myresp['csuccess']=csucc
        myresp['filenamefailed']=filenamefailed
        myresp['filenamecheckfailed']=filenamecheckfailed
        myresp['error']=""
        return myresp


def findpath(filetype,sidpath,composition):
    
    current_app.logger.debug('      inside findpath')
    elements=sidpath.split("/")
    elements=[el.lower().replace("_"," ") for el in elements]
    if(filetype=="XML"):
        root=etree.fromstring(composition)
        tree = etree.ElementTree(root)
        matches=[]
        for value in tree.iter('value'):
            if(elements[-1] in value.text.lower()):
                matches.append(tree.getelementpath(value))                
        if(len(matches)==1):
            sidp='value'.join(matches[0].rsplit('name', 1))
            return tree.findtext(sidp)
        elif(len(matches)>1):
            mm=[]
            for match in matches:
                pelements=match.split["/"]
                count=0
                for pe in pelements:
                    for el in elements[:-1]:
                        if(el==pe):
                            count+=1
                mm.append(count)
            max_item = max(mm)
            index=mm.index(max_item)
            sidp='value'.join(matches[index].rsplit('name', 1))
            return tree.findtext(sidp)
        else:
            return -1
    elif(filetype=="JSON"):
        matches=[]
        findjson("value", elements[-1], composition, "", matches) 
        if(len(matches)==1):
            elm=matches[0].split('/')
            elm[-2]='value'
            mystring=composition
            for e in elm:
                es=e.split("[")
                if len(es)>1:
                    mystring=mystring[es[0]]
                    es2=es[1].split(']')
                    mystring=mystring[int(es2[0])]
                else:
                    mystring=mystring[e]
      #      context/other_context/items[0]/items[0]/name/value
#   jsonstring['context']['other_context']['items'][0]['items'][0]['value']['value']
            return mystring
        elif(len(matches)>1):
            mm=[]
            for match in matches:
                pelements=match.split["/"]
                count=0
                for pe in pelements:
                    for el in elements[:-1]:
                        if(el==pe):
                            count+=1
                mm.append(count)
            max_item = max(mm)
            index=mm.index(max_item)
            elm=matches[index].split('/')
            elm[-2]='value'
            mystring=composition
            for e in elm:
                es=e.split("[")
                if len(es)>1:
                    mystring=mystring[es[0]]
                    es2=es[1].split(']')
                    mystring=mystring[int(es2[0])]
                else:
                    mystring=mystring[e]            
            return mystring
        else:
            return -1
    else:#FLAT JSON
        matches=[]
        for c in composition:
            if(elements[-1] in c.lower().replace("_"," ")):
                    matches.append(c)
        if(len(matches)==1):
            return composition[matches[0]]
        elif(len(matches)>1):
            mm=[]
            for match in matches:
                pelements=match.split["/"]
                count=0
                for pe in pelements:
                    for el in elements:
                        if(el==pe):
                            count+=1
                mm.append(count)
            max_item = max(mm)
            index=mm.index(max_item)
            return composition[matches[index]]
        else:
            return -1

def findjson(keytofind, valuetofind, JSON, path, all_paths):
    current_app.logger.debug('      inside findjson')
    if keytofind in JSON and type(JSON[keytofind])==str and valuetofind in JSON[keytofind].lower():
        path = path + keytofind 
        all_paths.append(path)
    for i,key in enumerate(JSON):
        if(type(JSON) is list):
            findjson(keytofind, valuetofind, key, path + '['+str(i)+']/',all_paths)
        else:
            if isinstance(JSON[key], dict):
                findjson(keytofind, valuetofind, JSON[key], path + key + '/',all_paths)
            elif(type(JSON[key]) is list):
                findjson(keytofind, valuetofind, JSON[key], path + key,all_paths)



def randomstring(N=10,chars=string.ascii_letters+string.digits):
    return ''.join(random.choice(chars) for _ in range(N))


def postbatch2(client,auth,url_base,url_base_ecis,uploaded_files,tid,check,eid,filetype,random,comps,ehrbase_version):
    current_app.logger.debug('inside postbatch2')
    number_of_files=len(uploaded_files)
    myresp={}
    if(filetype=="XML"):
        succ=0
        csucc=0
        compids=[]
        filenamefailed=[]
        filenamecheckfailed=[]
        #create EHRID
        if(random):
            sid=randomstring()
            sna='fakenamespace'
            eid=""
            resp10=createehrsub(client,auth,url_base,sid,sna,eid)
            if(resp10['status']!='success'):
                if(resp10['status_code']==409 and 'Specified party has already an EHR set' in json.loads(resp10['text'])['message']):
                    #get ehr summary by subject_id , subject_namespace
                    payload = {'subject_id':sid,'subject_namespace':sna}
                    ehrs = client.get(url_base + 'ehr',  params=payload,headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json'},verify=True)
                    current_app.logger.debug('ehr already existent')
                    eid=json.loads(ehrs.text)["ehr_id"]["value"]
                    current_app.logger.debug(f'Patient {sid}: retrieved ehrid={eid}')
            else:
                eid=resp10['ehrid']
        else:
            resp10=createehrid(client,auth,url_base,eid)
            if(resp10['status']!='success'):
                myerror="couldn't create ehrid="+eid+" "+resp10['status_code']+"\n"+ resp10['headers']+"\n"+resp10['text']
                current_app.logger.debug(myerror)
                myresp['error']=myerror
                myresp['status']='failed'
                myresp['success']=succ
                myresp['csuccess']=csucc
                myresp['filenamefailed']=filenamefailed
                myresp['filenamecheckfailed']=filenamecheckfailed
                myresp['compositionid']=compids
                myresp['ehrid']=eid          
            else:
                eid=resp10['ehrid']

        for uf,composition in zip(uploaded_files,comps):
#            uf.stream.seek(0)
#            composition=uf.read()
            root=etree.fromstring(composition)
            myurl=url_normalize(url_base + 'ehr/'+eid+'/composition')
            response = client.post(myurl,
                       params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml', \
                           'accept':'application/xml'}, data=etree.tostring(root),verify=True) 
            current_app.logger.debug(response.text)
            current_app.logger.debug(response.status_code)
            current_app.logger.debug(response.headers)
            if(response.status_code<210 and response.status_code>199):
                succ+=1
                cid=response.headers['Location'].split("composition/")[1]
                current_app.logger.info(f'postbatch2: POST success composition={cid} format={filetype} filename={uf.filename} ehrid={eid}')
                compids.append(cid)
                if(check=="Yes"):
                    checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,cid)
                    if(checkinfo==None):
                        csucc+=1
                        current_app.logger.info(f'postbatch2: successfully checked composition={cid} filename={uf.filename} ehrid={eid}')
                    else:
                        filenamecheckfailed.append(uf.filename)
                        current_app.logger.warning(f'postbatch2: unsuccessfully checked composition={cid} filename={uf.filename} ehrid={eid}')
            else:
                filenamefailed.append(uf.filename)
                current_app.logger.warning(f'postbatch2: POST failure filename={uf.filename} ehrid={eid}')
        if(check=='Yes'):
            current_app.logger.info(f"{csucc}/{number_of_files} files successfully POSTed and checked")
            if(csucc!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        else:
            if(succ!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        myresp['ehrid']=eid
        myresp['compositionid']=compids
        myresp['nsuccess']=succ
        myresp['csuccess']=csucc
        myresp['filenamefailed']=filenamefailed
        myresp['filenamecheckfailed']=filenamecheckfailed
        return myresp
    elif(filetype=="JSON"):
        succ=0
        csucc=0
        compids=[]
        filenamefailed=[]
        filenamecheckfailed=[]
        #create EHRID
        if(random):
            sid=randomstring()
            sna='fakenamespace'
            eid=""
            resp10=createehrsub(client,auth,url_base,sid,sna,eid)
            if(resp10['status']!='success'):
                if(resp10['status_code']==409 and 'Specified party has already an EHR set' in json.loads(resp10['text'])['message']):
                    #get ehr summary by subject_id , subject_namespace
                    payload = {'subject_id':sid,'subject_namespace':sna}
                    ehrs = client.get(url_base + 'ehr',  params=payload,headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json'},verify=True)
                    current_app.logger.debug('ehr already existent')
                    eid=json.loads(ehrs.text)["ehr_id"]["value"]
                    current_app.logger.debug(f'Patient {sid}: retrieved ehrid={eid}')
            else:
                eid=resp10['ehrid']
        else:
            resp10=createehrid(client,auth,url_base,eid)
            if(resp10['status']!='success'):
                myerror=f"couldn't create ehrid={eid}"+" "+resp10['status_code']+"\n"+ resp10['headers']+"\n"+resp10['text']
                current_app.logger.debug(myerror)
                myresp['error']=myerror
                myresp['status']='failed'
                myresp['success']=succ
                myresp['csuccess']=csucc
                myresp['filenamefailed']=filenamefailed
                myresp['filenamecheckfailed']=filenamecheckfailed
                myresp['compositionid']=compids
                myresp['ehrid']=eid          
            else:
                eid=resp10['ehrid']

        for uf,composition in zip(uploaded_files,comps):
#            uf.stream.seek(0)
#            composition=uf.read()
            comp = json.loads(composition)
            compositionjson=json.dumps(comp)
            myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
            try:
                if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                    params={'format': 'JSON'}
                else:#EHRBase version<2.5.0
                    params={'format': 'RAW'}
            except myutils.EHRBaseVersion:
                current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
                raise 
            response = client.post(myurl,params=params,headers={'Authorization':auth,'Content-Type':'application/json', \
             'accept':'application/json'}, data=compositionjson,verify=True)   
            current_app.logger.debug('Response Url')
            current_app.logger.debug(response.url)
            current_app.logger.debug('Response Status Code')
            current_app.logger.debug(response.status_code)
            current_app.logger.debug('Response Text')
            current_app.logger.debug(response.text)
            current_app.logger.debug('Response Headers')
            current_app.logger.debug(response.headers)
            if(response.status_code<210 and response.status_code>199):
                succ+=1
                cid=response.headers['Location'].split("composition/")[1]
                current_app.logger.info(f'postbatch2: POST success composition={cid} format={filetype} filename={uf.filename} ehrid={eid}')
                compids.append(cid)
                if(check=="Yes"):
                    checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,cid)
                    if(checkinfo==None):
                        csucc+=1
                        current_app.logger.info(f'postbatch2: successfully checked composition={cid} filename={uf.filename} ehrid={eid}')
                    else:
                        filenamecheckfailed.append(uf.filename)
                        current_app.logger.warning(f'postbatch2: unsuccessfully checked composition={cid} filename={uf.filename} ehrid={eid}')
            else:       
                filenamefailed.append(uf.filename)
                current_app.logger.warning(f'postbatch2: POST failure filename={uf.filename} ehrid={eid}')
        if(check=='Yes'):
            current_app.logger.info(f"{csucc}/{number_of_files} files successfully POSTed and checked")
            if(csucc!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        else:
            current_app.logger.info(f"{succ}/{number_of_files} files successfully POSTed")
            if(succ!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        myresp['ehrid']=eid               
        myresp['compositionid']=compids
        myresp['nsuccess']=succ
        myresp['csuccess']=csucc
        myresp['filenamefailed']=filenamefailed
        myresp['filenamecheckfailed']=filenamecheckfailed
        myresp['error']=""
        return myresp
    else:#FLAT JSON
        succ=0
        csucc=0
        compids=[]
        filenamefailed=[]
        filenamecheckfailed=[]
        #create EHRID
        if(random):
            sid=randomstring()
            sna='fakenamespace'
            eid=""
            resp10=createehrsub(client,auth,url_base,sid,sna,eid)
            if(resp10['status']!='success'):
                if(resp10['status_code']==409 and 'Specified party has already an EHR set' in json.loads(resp10['text'])['message']):
                    #get ehr summary by subject_id , subject_namespace
                    payload = {'subject_id':sid,'subject_namespace':sna}
                    ehrs = client.get(url_base + 'ehr',  params=payload,headers={'Authorization':auth,'Content-Type':'application/JSON','Accept': 'application/json'},verify=True)
                    current_app.logger.debug('ehr already existent')
                    eid=json.loads(ehrs.text)["ehr_id"]["value"]
                    current_app.logger.debug(f'Patient {sid}: retrieved ehrid={eid}')
            else:
                eid=resp10['ehrid']
        else:
            resp10=createehrid(client,auth,url_base,eid)
            if(resp10['status']!='success'):
                if(resp10['status_code']==409 and 'EHR with this ID already exists' in json.loads(resp10['text'])['message']):
                    pass
                else:
                    myerror=f"couldn't create ehrid={eid}"+" "+resp10['status_code']+"\n"+ resp10['headers']+"\n"+resp10['text']
                    current_app.logger.debug(myerror)
                    myresp['error']=myerror
                    myresp['status']='failed'
                    myresp['success']=succ
                    myresp['csuccess']=csucc
                    myresp['filenamefailed']=filenamefailed
                    myresp['filenamecheckfailed']=filenamecheckfailed
                    myresp['compositionid']=compids
                    myresp['ehrid']=eid          
            else:
                eid=resp10['ehrid']

        for uf,composition in zip(uploaded_files,comps):
            comp = json.loads(composition)
            compositionjson=json.dumps(comp) 
            try:
                if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                    myurl=url_normalize(url_base  + 'ehr/'+eid+'/composition')
                else:#EHRBase version<2.5.0
                    myurl=url_normalize(url_base_ecis  + 'composition')
            except myutils.EHRBaseVersion:
                current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
                raise 
            response = client.post(myurl,
                       params={'ehrId':eid,'templateId':tid,'format':'FLAT'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=minimal'},
                       data=compositionjson,verify=True
                      )
            current_app.logger.debug('Response Url')
            current_app.logger.debug(response.url)
            current_app.logger.debug('Response Status Code')
            current_app.logger.debug(response.status_code)
            current_app.logger.debug('Response Text')
            current_app.logger.debug(response.text)
            current_app.logger.debug('Response Headers')
            current_app.logger.debug(response.headers)
            if(response.status_code<210 and response.status_code>199):
                succ+=1
                cid=response.headers['Location'].split("composition/")[1]
                current_app.logger.info(f'postbatch2: POST success composition={cid} format={filetype} filename={uf.filename} ehrid={eid}')                
                compids.append(cid)
                if(check=="Yes"):
                    checkinfo= compcheck(client,auth,url_base,url_base_ecis,composition,eid,filetype,cid)
                    if(checkinfo==None):
                        csucc+=1
                        current_app.logger.info(f'postbatch2: successfully checked composition={cid} filename={uf.filename} ehrid={eid}')
                    else:
                        filenamecheckfailed.append(uf.filename)
                        current_app.logger.warning(f'postbatch2: unsuccessfully checked composition={cid} filename={uf.filename} ehrid={eid}')
            else:
                filenamefailed.append(uf.filename)
                current_app.logger.warning(f'postbatch2: POST failure filename={uf.filename} ehrid={eid}') 
        if(check=='Yes'):
            current_app.logger.info(f"{csucc}/{number_of_files} files successfully POSTed and checked")
            if(csucc!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        else:
            current_app.logger.info(f"{succ}/{number_of_files} files successfully POSTed and checked")
            if(succ!=0):
                myresp['status']='success'
            else:
                myresp['status']='failure'
        myresp['ehrid']=eid
        myresp['compositionid']=compids           
        myresp['nsuccess']=succ
        myresp['csuccess']=csucc
        myresp['filenamefailed']=filenamefailed
        myresp['filenamecheckfailed']=filenamecheckfailed
        myresp['error']=""
        return myresp

def getcontrib(client,auth,url_base,eid,vid):
    current_app.logger.debug('inside getcontrib')
    myurl=url_normalize(url_base  + 'ehr/'+eid+'/contribution/'+vid)
    response = client.get(myurl,headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},verify=True )
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp["status_code"]=response.status_code
    if(response.status_code<210 and response.status_code>199):
        myresp["status"]="success"
        myresp['json']=response.text
        current_app.logger.info(f"GET Contribution success for ehrid={eid} vid={vid}")
    else:
        myresp["status"]="failure"
        current_app.logger.info(f"GET Contribution failure for ehrid={eid} vid={vid}")
    myresp['text']=response.text
    myresp["headers"]=response.headers
    return myresp



def postcontrib(client,auth,url_base,eid,uploaded_contrib):
    current_app.logger.debug('inside postcontrib')
    contrib = json.loads(uploaded_contrib)
    contribjson=json.dumps(contrib)
    myurl=url_normalize(url_base  + 'ehr/'+eid+'/contribution')
    response=client.post(myurl,headers={'Authorization':auth,\
        'Content-Type':'application/json','Prefer': 'return=representation', \
            'accept':'application/json'}, \
        data=contribjson,verify=True)
    current_app.logger.debug('Response Url')
    current_app.logger.debug(response.url)
    current_app.logger.debug('Response Status Code')
    current_app.logger.debug(response.status_code)
    current_app.logger.debug('Response Text')
    current_app.logger.debug(response.text)
    current_app.logger.debug('Response Headers')
    current_app.logger.debug(response.headers)
    myresp={}
    myresp['headers']=response.headers
    myresp['status_code']=response.status_code
    myresp['text']=response.text
    if(response.status_code<210 and response.status_code>199):
        myresp['status']='success'
        myresp['json']=response.text
        current_app.logger.info(f'Contribution POST success')
    else:
        myresp['status']='failure'
        current_app.logger.warning(f'Contribution POST FAILURE')
    return myresp



def examplecomp(client,auth,url_base,url_base_ecis,template_name,filetype,ehrbase_version):
    current_app.logger.debug('inside examplecomp')
    if(filetype=="XML"):
        myurl=url_normalize(url_base  + 'definition/template/adl1.4/'+template_name+'/example')
        response=client.get(myurl,params={'format': 'XML'},headers={'Authorization':auth,'Content-Type':'application/xml','accept':'application/xml'},verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            root = etree.fromstring(response.text)
#          root.indent(tree, space="\t", level=0)
            myresp['xml'] = etree.tostring(root,  encoding='unicode', method='xml', pretty_print=True)
            myresp["status"]="success"
            current_app.logger.info(f"GET Example composition success for template={template_name} in format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"GET Example composition failure for template={template_name} in format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=="JSON"):
        myurl=url_normalize(url_base   + 'definition/template/adl1.4/'+template_name+'/example')
        response = client.get(myurl, params={'format': 'JSON'},headers={'Authorization':auth,'Content-Type':'application/json'} ,verify=True)
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['json']=response.text
            current_app.logger.info(f"GET Example composition success for template={template_name} in format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.info(f"GET Example composition failure for template={template_name} in format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp
    elif(filetype=='STRUCTURED'):#STRUCTURED
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base+ 'definition/template/adl1.4/'+template_name+'/example')
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis+ +'template/'+template_name+'/example')
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        response = client.get(myurl,
                       params={'format':'STRUCTURED'},
                       headers={'Authorization':auth,'Content-Type':'application/json','Prefer':'return=representation'},verify=True
                        )           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['structured']=json.dumps(json.loads(response.text),sort_keys=True, indent=1, separators=(',', ': '))
            current_app.logger.info(f"GET Example composition success for template={template_name} in format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"GET Example composition success for template={template_name} in format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp        
    else:#FLAT JSON
        try:
            if myutils.compareEhrbaseVersions(ehrbase_version,"2.5.0")>0: #EHRBase version>=2.5.0
                myurl=url_normalize(url_base+ 'definition/template/adl1.4/'+template_name+'/example')
            else:#EHRBase version<2.5.0
                myurl=url_normalize(url_base_ecis+'template/'+template_name+'/example')
        except myutils.EHRBaseVersion:
            current_app.logger.info(f"Error in ehrbase version mapping. ehrbase_version={ehrbase_version}")
            raise 
        response = client.get(myurl,
                       params={'format':'FLAT'},
                       headers={'Authorization':auth,'Content-Type':'application/json'},verify=True
                        )           
        current_app.logger.debug('Response Url')
        current_app.logger.debug(response.url)
        current_app.logger.debug('Response Status Code')
        current_app.logger.debug(response.status_code)
        current_app.logger.debug('Response Text')
        current_app.logger.debug(response.text)
        current_app.logger.debug('Response Headers')
        current_app.logger.debug(response.headers)
        myresp={}
        myresp["status_code"]=response.status_code
        if(response.status_code<210 and response.status_code>199):
            myresp["status"]="success"
            myresp['flat']=json.dumps(json.loads(response.text),sort_keys=True, indent=1, separators=(',', ': '))
            current_app.logger.info(f"GET Example composition success for template={template_name} in format={filetype}")
        else:
            myresp["status"]="failure"
            current_app.logger.warning(f"GET Example composition success for template={template_name} in format={filetype}")
        myresp['text']=response.text
        myresp["headers"]=response.headers
        return myresp

def createform(client,auth,url_base,url_base_ecis,template_name,ehrbase_version):
    current_app.logger.debug('inside createform')
    filetype='FLAT'
    resp=examplecomp(client,auth,url_base,url_base_ecis,template_name,filetype,ehrbase_version)
    if(resp['status']=='failure'):
        return resp
    else:
        flatcomp=json.loads(resp['flat'])
        #remove template_name/_uid
        tkey=template_name.lower()+'/_uid'
        if tkey in flatcomp:
            del flatcomp[tkey]
        listcontext=[]
        listcontent=[]
        listcontext,listcontent,listcontextvalues,listcontentvalues=fillListsfromComp(flatcomp)
        current_app.logger.debug('listcontext')
        current_app.logger.debug(listcontext)
        current_app.logger.debug('listcontextvalues')
        current_app.logger.debug(listcontextvalues)
        contexttoadd=[]
        contenttoadd=[]
        varcontext=[]
        varcontent=[]
        # varlistctx=[]
        # varlistcnt=[]
        contexttoadd,varcontext,ivarstart=fillforms(listcontext,listcontextvalues,0)
        contenttoadd,varcontent,ivarend=fillforms(listcontent,listcontentvalues,ivarstart)

        createformfile(contexttoadd,varcontext,contenttoadd,varcontent,template_name)
        msg={}
        msg['status']='success'
        return msg

def iterwrite(f,var):
    for v in var:
        if(isinstance(v,list)):
            return iterwrite(f,v)
        else:
            f.write(v)



def createformfile(contexttoadd,varcontext,contenttoadd,varcontent,template_name):
    current_app.logger.debug('      inside createformfile')
    c1=[]
    c3=[]
    c5=[]
    contextstart='HERE NORE CONTEXT'
    contentstart='HERE THE CONTENT'
    with open('./templates/base.html','r') as bf:
        context=bf.readlines()
    icontext=0
    for i,line in enumerate(context):
        if(contextstart in line):
            c1=context[:i]
            icontext=i
        if(contentstart in line):
            c3=context[icontext+1:i]
            c5=context[i+1:]

    varline='<!-- '
    varctx=','.join(','.join(b) for b in varcontext)
    varline2=','
    varcnt=','.join(','.join(b) for b in varcontent)
    varend=' -->'
        
    formstring=''
    with open('./templates/form.html','w') as ff:
        ff.write("\n".join(c1))
        ff.write("\n".join(contexttoadd))
        ff.write("\n".join(c3))
        ff.write("\n".join(contenttoadd))
        ff.write("\n".join(c5))
        ff.write(varline+template_name+varend)
        ff.write(varline+str(varctx)+varline2+str(varcnt)+varend)

def fillforms(listc,listcvalues,ivarstart):
    current_app.logger.debug('      inside fillforms')
    startrow='<div class="row">'
    endrow='</div>'
    startcol='   <div class="col">'
    endcol='   </div>'
    label1='<label  class="form-label" for="category">'
    label3='</label><br>'
    control1='<input  class="form-control" type="text" id="'
    control3='" name="'
    control5='" placeholder="'
    control7='">'
    ctoadd=[]
    varc=[]
    #fill context or content
    i=ivarstart
    j=0
    for c,v in zip(listc,listcvalues):
        current_app.logger.debug(f'c,v in zip(listc,listcvalue) {c} {v}')
        if(j==0):
            ctoadd.append(startrow)
        elif(j%2==0):
            ctoadd.append(endrow)
            ctoadd.append(startrow)
        ctoadd.append(startcol)
        mylabel=c[0].split('|')[0]
        ctoadd.append(label1+mylabel+label3)
        for ci,vi in zip(c,v):
            segment=ci.split('/')[-1].split('|')
            piece=""
            if(len(segment)>1):
                piece=segment[1]
            else:
                piece=segment[0]
            ctoadd.append(control1+'var'+str(i)+control3+
                'var'+str(i)+control5+piece+' ex '+ str(vi) +control7)
            varc.append(['var'+str(i),ci])
            i=i+1
        j=j+1
        ctoadd.append('<br><br>')
        ctoadd.append(endcol)
    if(j%2 !=0):#add void col if needed
        ctoadd.append(startcol)
        ctoadd.append(endcol)
        ctoadd.append(endrow)
    else:
        ctoadd.append(endrow)
    return ctoadd,varc,i



def fillListsfromComp(flatcomp):
    current_app.logger.debug('      inside fillListsfromComp')
    listcontext=[]
    listcontextvalues=[]
    listcontent=[]
    listcontentvalues=[]
    words1=['context','ctx','category','language','territory','composer']
    words2=['location','start_time','_end_time','setting','_health_care_facility','_participation','_uid']
    words3=['context','ctx']
    lastel=""
    for el in flatcomp:
        current_app.logger.debug(f'el in flatcomp: {el}')
        second=el.split('/')[1].split('|')[0]
        current_app.logger.debug(f'second: {second}')
        last=el.split('/')[-1]
        current_app.logger.debug(f'last: {last}')
        if(second in words1):
            current_app.logger.debug('A')
            #check if in already considered fields
            if(second in words3):
                current_app.logger.debug(f'A1')
                third=el.split('/')[2].split('|')[0]
                current_app.logger.debug(f'third: {third}')
                if(third in words2):
                    current_app.logger.debug(f'A1A')
                    current_app.logger.debug('already considered in context')
                    continue
                else:
                    current_app.logger.debug(f'A1B')
                    #check if left part already found
                    current_app.logger.debug(f'lastel: {lastel}')
                    if(el.split('|')[0]==lastel.split('|')[0]):
                        current_app.logger.debug(f'A1B1')
                        current_app.logger.debug(f'listcontext[-1] {listcontext[-1]}')
                        current_app.logger.debug(f'el {el}')
                        listcontext[-1].extend([el])
                        listcontextvalues[-1].extend([flatcomp[el]])
                    else:
                        current_app.logger.debug(f'A1B2')
                        current_app.logger.debug(f'el {el}' )                      
                        listcontext.append([el])
                        listcontextvalues.append([flatcomp[el]])
                    lastel=el
            else:
                current_app.logger.debug(f'A2')
                pass
        else:
            #check if left part already found
            current_app.logger.debug(f'B')
            current_app.logger.debug(f'lastel: {lastel}')
            if(el.split('|')[0]==lastel.split('|')[0]):
                listcontent[-1].append(el)
                listcontentvalues[-1].append(flatcomp[el])
            else:
                listcontent.append([el])
                listcontentvalues.append([flatcomp[el]])
            lastel=el
    return listcontext,listcontent,listcontextvalues,listcontentvalues

def readform():
    current_app.logger.debug('inside readform')
    with open('./templates/form.html','r') as ff:
        allfile=ff.readlines()
    formstring=''.join(allfile)
    return formstring

def postform(client,auth,url_base,url_base_ecis,formname,ehrbase_version):
    current_app.logger.debug('inside postform')
    #retrieve var and path
    tid=formname
    formname=formname.lower()
    with open('./templates/form.html','r') as ff:
        allfile=ff.readlines()
    varinfo=allfile[-1].split('<!--')[1].split('-->')[0].strip()
    varinfolist=varinfo.split(',')
    #create flat composition
    composition={}
    #add context variables
    #category
    tcat=request.args.get("tcat","")
    if(tcat==""):
        tcat="openehr"
    ccat=request.args.get("ccat","")
    if(ccat==""):
        ccat="433"
    vcat=request.args.get("vcat","")
    if(vcat==""):
        vcat='event'
    composition[formname+'/category|terminology']=tcat
    composition[formname+'/category|code']=ccat
    composition[formname+'/category|value']=vcat
    #language
    tlan=request.args.get("tlan","")
    if(tlan==""):
        tlan="ISO_639-1"
    clan=request.args.get("clan","")
    if(clan==""):
        clan="en"
    composition[formname+'/language|terminology']=tlan
    composition[formname+'/language|code']=clan
    #territory
    tter=request.args.get("tter","")
    if(tter==""):
        tter="ISO_3166-1"
    cter=request.args.get("cter","")
    if(cter==""):
        cter="IT"
    composition[formname+'/territory|terminology']=tter
    composition[formname+'/territory|code']=cter
    #time
    stime=request.args.get("stime","")
    if(stime==""):
        stime="2022-03-15T12:04:38.49Z"
    etime=request.args.get("etime","")
    composition[formname+'/context/start_time']=stime
    if(etime != ""):
        composition[formname+'/context/_end_time']=etime
    #health_care_facility
    idhcf=request.args.get("idhcf","")
    idshcf=request.args.get("idshcf","")
    idnhcf=request.args.get("idnhcf","")
    nhcf=request.args.get("nhcf","")
    if(idhcf != ""):
        composition[formname+'/context/_health_care_facility|id']=idhcf
    if(idshcf != ""):
        composition[formname+'/context/_health_care_facility|id_scheme']=idshcf
    if(idnhcf != ""):    
        composition[formname+'/context/_health_care_facility|id_namespace']=idnhcf
    if(nhcf != ""):    
        composition[formname+'/context/_health_care_facility|name']=nhcf
    #participation1-2-3
    fpart1=request.args.get("fpart1","")
    mpart1=request.args.get("mpart1","")
    npart1=request.args.get("npart1","")
    ipart1=request.args.get("ipart1","")
    ispart1=request.args.get("ispart1","")
    inpart1=request.args.get("inpart1","")
    if(fpart1 !=""):
        composition[formname+'/context/_participation:0|function']=fpart1
    if(mpart1 !=""):
        composition[formname+'/context/_participation:0|mode']=mpart1
    if(npart1 !=""):
        composition[formname+'/context/_participation:0|name']=npart1
    if(ipart1 !=""):
        composition[formname+'/context/_participation:0|id']=ipart1
    if(ispart1 !=""):
        composition[formname+'/context/_participation:0|id_scheme']=ispart1
    if(inpart1 != ""):
        composition[formname+'/context/_participation:0|id_namespace']=inpart1
    if(fpart1 !=""):
        fpart2=request.args.get("fpart2","")
        mpart2=request.args.get("mpart2","")
        npart2=request.args.get("npart2","")
        ipart2=request.args.get("ipart2","")
        ispart2=request.args.get("ispart2","")  
        inpart2=request.args.get("inpart2","")    
        if(fpart2 !=""):
            composition[formname+'/context/_participation:1|function']=fpart2
        if(mpart2 !=""):
            composition[formname+'/context/_participation:1|mode']=mpart2
        if(npart2 !=""):
            composition[formname+'/context/_participation:1|name']=npart2
        if(ipart2 !=""):
            composition[formname+'/context/_participation:1|id']=ipart2
        if(ispart2 !=""):
            composition[formname+'/context/_participation:1|id_scheme']=ispart2
        if(inpart1 != ""):
            composition[formname+'/context/_participation:1|id_namespace']=inpart2
        if(fpart2!=""):
            fpart3=request.args.get("fpart3","")
            mpart3=request.args.get("mpart3","")
            npart3=request.args.get("npart3","")
            ipart3=request.args.get("ipart3","")
            ispart3=request.args.get("ispart3","")  
            inpart3=request.args.get("inpart3","") 
            if(fpart3 !=""):
                composition[formname+'/context/_participation:2|function']=fpart3
            if(mpart3 !=""):
                composition[formname+'/context/_participation:2|mode']=mpart3
            if(npart3 !=""):
                composition[formname+'/context/_participation:2|name']=npart3
            if(ipart3 !=""):
                composition[formname+'/context/_participation:2|id']=ipart3
            if(ispart3 !=""):
                composition[formname+'/context/_participation:2|id_scheme']=ispart3
            if(inpart3 != ""):
                composition[formname+'/context/_participation:2|id_namespace']=inpart3
    #composer PARTY_SELF or PARTY_IDENTIFIED
    cself=request.args.get("cself","")
    ciid=request.args.get("ciid","")
    if(cself != ""):#party self
        composition['ctx/composer_self']=True
        composition['ctx/composer_id']=cself
        sself=request.args.get("sself","")
        nself=request.args.get("nself","")
        if(sself != ""):
            composition['ctx/id_scheme']=sself
        if(nself != ""):
            composition['ctx/id_namespace']=nself
    elif(ciid != ""):#party identified
        composition['ctx/composer_id']=ciid
        ciname=request.args.get("ciname","")
        ciisc=request.args.get("ciisc","")
        cins=request.args.get("cins","")
        if(ciname != ""):
            composition['ctx//composer_name']=ciname
        if(ciisc != ""):
            composition['ctx//id_scheme']=ciisc
        if(cins != ""):
            composition['ctx/id_namespace']=cins      
    #setting
    setter=request.args.get("setter","")
    if(setter==""):
        setter="openehr"
    codeter=request.args.get("codeter","")
    if(codeter==""):
        codeter="238"
    valter=request.args.get("valter","")
    if(valter==""):
        valter="other care"
    composition[formname+'/context/setting|terminology']=setter
    composition[formname+'/context/setting|code']=codeter
    composition[formname+'/context/setting|value']=valter
    #location
    loc=request.args.get("loc","")
    if(loc != ""):
        composition[formname+'/context/_location']=loc
    #the remaining variables
    for var,path in two_at_a_time(varinfolist):
        value=request.args.get(var,"")
        if(value != ""):
            composition[path]=value
    #post the composition
    filetype='FLAT'
    eid=request.args.get("ename","")    
    check=request.args.get("check","")
    checkresults=""
    checkinfo=""
    comp=json.dumps(composition)
    myresp=postcomp(client,auth,url_base,url_base_ecis,comp,eid,tid,filetype,check,ehrbase_version)
    return myresp       
 
def two_at_a_time(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)

def retrievetemplatefromform(formloaded):
    current_app.logger.debug('      inside retrievetemplatefromform')
    index=formloaded.rfind("<!-- ", 0, formloaded.rfind("<!-- "))
    index2=formloaded.find(" -->",index,len(formloaded))
    template_name=formloaded[index+4:index2].strip()
    return template_name

def fixformloaded(formloaded):
    current_app.logger.debug('      inside fixformloaded')
    #fix missing double braces 
    #<h1>Form for template form.html</h1>
    #{{forname}}
    fl=formloaded.replace("<h1>Form for template form.html</h1>",
                    "<h1>Form for template {{formname}}</h1>")
    fl2=fl.replace('<input class="form-control" type="text" id="ename" name="ename" value= >',
                    '<input class="form-control" type="text" id="ename" name="ename" value={{last}}>')

    index1=fl2.find("<h2>Results</h2>")+17
    index2=fl2.find("<br><br>",index1)
    index3=fl2.find("<br><br>",index2+8)
    linestoadd1='''
    {% macro linebreaks_for_string( the_string ) -%}
    {% if the_string %}
    {% for line in the_string.split('\n') %}
    <br />
    {{ line }}
    {% endfor %}
    {% else %}
    {{ the_string }}
    {% endif %}
    {%- endmacro %}
    {{ linebreaks_for_string( yourresults ) }}
    '''
    linestoadd2='{{checkresults}}'
    linestoadd3='{{checkinfo}}'  
    formfixed=fl2[:index1]+linestoadd1+fl2[index2:index2+9]+linestoadd2+fl2[index3:index3+9]+linestoadd3+fl2[index3+10:]
    return formfixed
