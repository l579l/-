#coding=utf8
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from mysql_orm_api import writeCtrlMessage,readUserMessage

engine = create_engine("mysql+pymysql://lab202:123123@192.168.1.111:3306/zxzldb?charset=utf8",\
                        pool_size=10,max_overflow=3,echo_pool=True)
Session = sessionmaker(bind=engine)  #订制mysql会话
Base =automap_base()
Base.prepare(engine,reflect=True)
in_str={'黄陂/第一舍/第一栏,第二栏,第五栏':{'trig_num':50,'trig_interv':30},'UserID':'张三','Timestamp':1234234231}
#print(writeCtrlMessage(Session,Base,in_str))
print(readUserMessage(Session,Base,'张三'))


'''
from plugins.mysqlDBapi import *
from plugins.mysqlConnPool import mysqlConnPool
mysql = mysqlConnPool()

zxdata={'name':'孙二','password':'hgfty534'}
#print(registerUser(zxdata))
#print(validateMessage(zxdata))

zxdata1={'alias':'黄陂区/001楼/001舍/0002号','trig_interv':42,'trig_num':52,'feeder_id':'zxzl0001'}
zxdata2={'alias':'黄陂区/001楼/001舍/0001号','request_keys':['trig_interv','trig_num']}
regisFeeder(mysql,zxdata1)
#print(writeCtrlMessage(mysql,zxdata1))
#print(readCtrlMessage(zxdata2))

#zxdata3={'alias':'黄陂区/001楼/001舍/0001号','time_record':1525829150,'equi_acc_mat':671.51,'equi_acc_wat':952.45}

zxdata4={'alias':'黄陂区/001楼/001舍/0001号','request_keys':['equi_acc_mat','equi_acc_wat'],'during':[0,1525829436]}
#print(writeEverydayMessage(zxdata3))
#print(readHistoryMessage(mysql,zxdata4))
zxdata5={'alias':'黄陂区/001楼/001舍/0001号','alert_keys':['wat_break','feeder_empt'],'duetime_prom':100}
#print(writeAlarmMessage(zxdata5,0))
'''
