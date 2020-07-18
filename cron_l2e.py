#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import sys
from asterisk.agi import *
import os
import datetime
import requests
import json

#This is the script run by crontab every midnight

import sqlite3

def connect_database():
    conn = sqlite3.connect('/root/ivr_data.db')
    print("Opened database successfully")
    return conn

def HLR(number,conn,call_id):
        cursor = conn.execute("SELECT EXISTS(SELECT 1 FROM HLR WHERE PHONE_NUMBER=" + str(number) + ")")
        print("yes")
        for row in cursor:
            exists = row[0]
        if exists == 0:
            dict_HLR_op_code={}
            dict_HLR_op_code_new={}
            with open('HLR.json') as f:
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
            # print(h_r)
            mccmnc=h_r["results"][0]["mccmnc"]
            # mccmnc = '405854'
            if mccmnc in dict_HLR_op_code_new:
                print("INSERT INTO HLR VALUES (" + 'str(number)' + "," + 'str(dict_HLR_op_code_new[mccmnc])' + ")")
                conn.execute("INSERT INTO HLR VALUES (" + "'"  +str(number)+ "'"  + "," + "'" +  str(dict_HLR_op_code_new[mccmnc])+ "'" + ")")
                conn.commit()
                recharge_HLR(number,dict_HLR_op_code_new[mccmnc],conn,call_id)
            else:
                
                z='{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
                conn.execute("INSERT INTO CALL VALUES (NULL," + "'" + str(number)+ "'" + ",'" + intro + "','" + q1 + "','" + q2 + "','" + q3 + "','" + q4 + "','" + per + "','" + "Operator not supported" + "','" + z +"'," + "'NO HLR'" + ")")
                conn.commit()
        else:
            cursor = conn.execute("SELECT OPCODE FROM HLR WHERE PHONE_NUMBER=" + "'" + str(number) + "'")
            for row in cursor:
                op_code = row[0]
            
            recharge_HLR(number,op_code,conn,call_id)

def recharge_HLR(number,op_code,conn,call_id):

        global intro, q1, q2, q3, q4, per
        amount=10
        if op_code == 'JO':
            amount=11
        z='{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
        #trying via IMWallet
        jolo_to_imwallet={'AT':'AR','BS':'B','IDX':'ID','RG':'RG','TD':'DG','UN':'UN','VF':'VF','JO':'JO'}
        op_code_imwallet=jolo_to_imwallet[op_code]
        rech=requests.get("https://joloapi.com/api/v1/recharge.php?userid=cgnetswara&key=xxxxxxxxx&operator=%s&service=%s&amount=%s&orderid=%s" % (op_code,str(number),amount,z))
        print(rech.text)
        if eval(rech.text)["status"] != 'FAILED':
                   
            conn.execute("UPDATE CALL SET RECH_TEXT = '" + rech.text + "', DATE_TIME = '" + z + "', STATUS = 'YES JOLO' WHERE ID = " + call_id)
            conn.commit()
        else:
                    
            rech=requests.post("http://www.login.imwallet.in/API/APIService.aspx?userid=6264241440&pass=xxxxxxx&mob=%s&opt=%s&amt=%s&agentid=%s&fmt=JSON" %(number,op_code_imwallet,amount,z))
            print(number,op_code_imwallet,z)
            if(json.loads(rech.text)['STATUS'].split(',')[0]=='FAILED' or json.loads(rech.text)['STATUS'].split(',')[0]=='Failed'):
                conn.execute("UPDATE CALL SET RECH_TEXT = '" + rech.text + "', DATE_TIME = '" + z + "', STATUS = 'NO' WHERE ID = " + call_id)
                conn.commit()
            else:
 conn.execute("UPDATE CALL SET RECH_TEXT = '" + rech.text + "', DATE_TIME = '" + z + "', STATUS = 'YES IM' WHERE ID = " + call_id)
                conn.commit()


conn = connect_database()
call_id = conn.execute("SELECT ID,PHONE_NUMBER FROM CALL WHERE STATUS = 'NO'")

for row in call_id:
        HLR(row[1],conn,str(row[0]))
conn.close()
