#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import sys
from asterisk.agi import *
import os
import datetime
import requests
import json

import sqlite3

def connect_database():
    conn = sqlite3.connect('/root/ivr_data.db')
    print("Opened database successfully")
    return conn

def HLR(number,conn):
        cursor = conn.execute("SELECT EXISTS(SELECT 1 FROM HLR WHERE PHONE_NUMBER=" + str(number) + ")")
        print("yes")
        for row in cursor:
            exists = row[0]
        if exists == 0:
            dict_HLR_op_code={}
            dict_HLR_op_code_new={}
            with open('/root/HLR.json') as f:
                dict_HLR_op_code = json.load(f)
            HLR_to_op={'aircel':'1','bsnl':'3','cellone':'3','airtel':'28','vodafone':'22','docomo':'17','reliance':'13','idea':'8','uninor':'19','videocon':'5','jio':'jio'}
            op_code_map={'1':'AL','3':'BS','28':'AT','8':'IDX','10':'MS','12':'RL','13':'RG','17':'TD','19':'UN','5':'VD','22':'VF','jio':'JO'}
            for mccmnc in dict_HLR_op_code:
                lookup_query=dict_HLR_op_code[mccmnc]
                for op in HLR_to_op:
                    if op in lookup_query:
                        dict_HLR_op_code_new[mccmnc]=op_code_map[HLR_to_op[op]]

            hlr_response=requests.get("http://share-env-1.ap-south-1.elasticbeanstalk.com/lookup/?number=" + str(number))
            h_r=json.loads(hlr_response.text)
            
            mccmnc=h_r["results"][0]["mccmnc"]
            # mccmnc = '405854'
            if mccmnc in dict_HLR_op_code_new:
                print("INSERT INTO HLR VALUES (" + 'str(number)' + "," + 'str(dict_HLR_op_code_new[mccmnc])' + ")")
                conn.execute("INSERT INTO HLR VALUES (" + "'"  +str(number)+ "'"  + "," + "'" +  str(dict_HLR_op_code_new[mccmnc])+ "'" + ")")
                conn.commit()
                
		recharge_HLR(number,dict_HLR_op_code_new[mccmnc],conn)
            else:
                
                z='{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
                conn.execute("INSERT INTO CALL VALUES (NULL," + "'" + str(number)+ "'" + ",'" + intro + "','" + q1 + "','" + q2 + "','" + q3 + "','" + q4 + "','" + per + "','" + "Operator not supported" + "','" + z +"'," + "'NO HLR'" + ")")
                conn.commit()
        else:
            cursor = conn.execute("SELECT OPCODE FROM HLR WHERE PHONE_NUMBER=" + "'" + str(number) + "'")
            for row in cursor:
                op_code = row[0]
            
            recharge_HLR(number,op_code,conn)

def recharge_HLR(number,op_code,conn):

        global intro, q1, q2, q3, q4, per
        amount=10
        if op_code == 'JO':
            amount=11
        z='{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
        #trying via IMWallet
        jolo_to_imwallet={'AT':'AR','BS':'B','IDX':'ID','RG':'RG','TD':'DG','UN':'UN','VF':'VF','JO':'JO'}
        op_code_imwallet=jolo_to_imwallet[op_code]
        rech=requests.get("https://joloapi.com/api/v1/recharge.php?userid=cgnetswara&key=xxxxxxxx&operator=%s&service=%s&amount=%s&orderid=%s" % (op_code,str(number),amount,z))
        if eval(rech.text)["status"] != 'FAILED':
                    
            conn.execute("INSERT INTO CALL VALUES (NULL,'" + str(number) + "','" + intro + "','" + q1 + "','" + q2 + "','" + q3 + "','" + q4 + "','" + per + "','" + rech.text + "','" + z + "','" "YES JOLO'" + ")")
            conn.commit()
        else:
                    
            rech=requests.post("http://www.login.imwallet.in/API/APIService.aspx?userid=6264241440&pass=xxxxxxx&mob=%s&opt=%s&amt=%s&agentid=%s&fmt=JSON" %(number,op_code_imwallet,amount,z))
            print(number,op_code_imwallet,z)
            if(json.loads(rech.text)['STATUS'].split(',')[0]=='FAILED' or json.loads(rech.text)['STATUS'].split(',')[0]=='Failed'):
                conn.commit()
            else:
                conn.execute("INSERT INTO CALL VALUES (NULL,'" + str(number) + "','" + intro + "','" + q1 + "','" + q2 + "','" + q3 + "','" + q4 + "','" + per + "','" + rech.text + "','" + z + "','" +  "YES IM'" + ")")
                conn.commit()

agi = AGI()
agi.verbose("python agi started")
agi.verbose("Here")

#phno = "9182913295"
#intro = "r1"
#q1 = "r1"
#q2 = "r1"
#q3 = "r1"
#q4 = "r1"
#per = "0"

phno = agi.get_variable('targetnumber')
intro = agi.get_variable('RINTRO')
q1 = agi.get_variable('RQ1')
q2 = agi.get_variable('RQ2')
q3 = agi.get_variable('RQ3')
q4 = agi.get_variable('RQ4')
per = agi.get_variable('PERMISSION')

conn = connect_database()

#permission 0 indicates user didn't complete the call
if (str(per) == '0'):
        z='{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
        conn.execute("INSERT INTO CALL VALUES (NULL," + "'" + str(phno)+ "'" + ",'" + intro + "','" + q1 + "','" + q2 + "','" + q3 + "','" + q4 + "','" + per + "','" + "HANGUP" + "','" + z +"'," + "'CALL HUNGUP'" + ")")
        conn.commit()
else:
        HLR(phno,conn)

conn.close()
