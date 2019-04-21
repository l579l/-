#coding=utf-8
#from plugins.mysqlConnPool import mysqlConnPool
from decimal import Decimal

#mysql = mysqlConnPool()

#------------------------------用户注册，登录，权限验证----------------
def registerUser(mysql,message):
    re = mysql.apply(('user_table',message),MODE='insert')
    mysql.close()
    return re

def validateMessage(mysql,message,toValidate="password"):
    if toValidate.lower() not in ('password','authority'):
        raise Exception('参数有误!')
    messages = message.copy()
    name = messages.pop('name')
    col_name = tuple(messages.keys())[0]
    re = mysql.apply(('user_table',col_name,{'name':name}),MODE='query')[0]
    if toValidate.lower() == 'password':
        if re[col_name].decode('utf-8') == messages[col_name]:
            return True
        else:
            return False
    else:
        AUTHORITY = ('S','A','B','C')
    #将用户的权限与操作的权限对比，高则返回True
        if AUTHORITY.index(re[col_name]) <= AUTHORITY.index(messages[col_name].upper()):
            return True
        else:
            return False

        
#------------------------------服务器数据交互--------------------------
def regisFeeder(mysql,message):
    re = mysql.apply(('feeder_info',message),MODE='insert')
    mysql.close()
    return re

def writeCtrlMessage(mysql,message):
    messages = message.copy()
    alias = messages.pop('alias')
    format_arg = ('feeder_info',messages,{'alias':alias})
    if not mysql.apply(format_arg,MODE='modify'):
        return False
    mysql.close()
    return {'status_code':'zx001'}


def readCtrlMessage(mysql,message):
    messages = message.copy()
    alias = messages.pop('alias')
    format_arg = ('feeder_info',messages['request_keys'],{'alias':alias})
    re = mysql.apply(format_arg,MODE='query')[0]
    for key,value in re.items():
        if isinstance(value,Decimal):
            re[key]=float(value)                
    mysql.close()
    return re

def readHistoryMessage(mysql,message):
    messages = message.copy()
    alias = messages.pop('alias')
    feeder = mysql.apply(('feeder_info','feeder_id',{'alias':alias}),MODE='query')[0]
    if messages['request_keys'][0].startswith('equi'):
        table_name = 'quan_' + feeder['feeder_id']
    else:
        table_name = 'qita_' + feeder['feeder_id']
    sql = "select * from %s where time_record >=%s and time_record <=%s \
            order by time_record asc" %(table_name,*messages['during'])
    try:
        re=mysql.apply(sql,MODE='SQL')[0]
    except:
        return {'status_code':'zx000'}
    finally:
        for key,value in re.items():
            if isinstance(value,Decimal):
                re[key]=float(value)   
        mysql.close()
        return re

def writeEverydayMessage(mysql,message):
    messages = message.copy()
    alias = messages.pop('alias')
    feeder = mysql.apply(('feeder_info','feeder_id',{'alias':alias}),MODE='query')[0]
    if any((key.startswith('equi') for key in messages.keys())):
        table_name = 'quan_' + feeder['feeder_id']
    else:
        table_name = 'qita_' + feeder['feeder_id']
    re = mysql.apply((table_name,messages),MODE='insert')
    mysql.close()
    return re
    

def writeAlarmMessage(mysql,message,status=1):
    messages = message.copy()
    if status not in (0,1):raise Exception('status只能取0或1')
    alias = messages.pop('alias')
    changed_value = {}
    for key in messages['alert_keys']:
        changed_value[key]=status
    if messages.__contains__('duetime_prom'):
        changed_value['duetime_prom'] = messages['duetime_prom']
    format_arg = ('feeder_info',changed_value,{'alias':alias})
    if not mysql.apply(format_arg,MODE='modify'):
        return False
    mysql.close()
    return {'status_code':'zx001'}
    

    
