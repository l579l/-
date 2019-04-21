#coding=utf-8
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import json
from conf import *
#pool_size=20,max_overflow=3,pool_recycle=3600,

print("wx_server连接数据库")
engine = create_engine(MYSQL_CONNECT,echo_pool=True,poolclass=NullPool)
Session = sessionmaker(bind=engine)  #订制mysql会话
Base =automap_base()
Base.prepare(engine,reflect=True)

#----------修改
def handle_alias(alias):
    pieces = alias.split('/')
    ret = []
    if len(pieces) == 2:
        return [i+'/' for i in pieces[0].split(',')]
    for p1 in pieces[0].split(','):
        for p2 in pieces[1].split(','):
            for p3 in pieces[2].split(','):
                ret.append('/'.join([p1,p2,p3]))
    return ret
            
    
#输入1：['黄陂/第一舍/第一栏','黄陂/第一舍/第二栏','黄陂/第一舍/第五栏']
#输入2：{'trig_num':50,'trig_time':30}
#userID   #timestamp
def sql_writeSetMessage(alias,set_info,userID,Timestamp):
    if not alias:return None 
    sess = Session()
    Feeder = Base.classes.feeder_info
    LOG = Base.classes.logs
    #lalias=handle_alias(alias[0])
    #print(lalias)
    for i in alias:
        try:
            sess.query(Feeder).filter_by(alias=i).update(set_info.items())
        except:
            return False
    sess.add(LOG(name=userID,time=Timestamp,oper='修改',oper_data=str({tuple(alias):set_info})))
    sess.commit()
    sess.close()
    return True

#读取in_str: [lias,[keys1,keys2...]]
def sql_readCurrentStatus(in_str):
    sess = Session()
    Feeder = Base.classes.feeder_info
    result = {}
    for item in in_str[1]:
        res = sess.query(getattr(Feeder,item)).filter_by(alias=in_str[0]).all()[0][0]
        #print(res)
        result[item] = float(res) if res is not None else None
    return result


def sql_readAliasMessage(in_str):
    sess = Session()
    Feeder = Base.classes.feeder_info
    res = sess.query(Feeder.alias).filter(Feeder.alias.like(in_str+'%')).all()
    ret = [i[0] for i in res]
    sess.close()
    return ret


#查看
def readUserMessage(in_str):
    sess = Session()
    User = Base.classes.user_table
    Feeder = Base.classes.feeder_info
    auth = sess.query(User.authority).filter_by(name=in_str).one()[0]
    ret=[]
    for alias in handle_alias(auth):
        res = sess.query(Feeder.alias).filter(Feeder.alias.like(alias+'%')).all()
        ret = ret + [i[0] for i in res]
    sess.close()
    return ret

#查询历史数据，查询项目有：`str_trig_num`（撞杆触发次数'）；`ultr_ran_num`（'超声波测距区间数值'）
#`equi_acc_mat`（'饲喂器累计料量'）；`equi_acc_wat`（'饲喂器累计水量'）
def sql_readHistoryMessage(in_str): #in_str:[alias,[start_time,end_time],[key1,key2...]]
    sess = Session()
    feeder_id = sess.query(Base.classes.feeder_info.feeder_id).filter_by(alias=in_str[0]).all()[0][0]
    result = {}
    for item in in_str[2]:
        if item in ['str_trig_num','ultr_ran_num']:
            tbclass = getattr(Base.classes,'qita_'+feeder_id)
        elif item in ['equi_acc_mat','equi_acc_wat']:
            tbclass = getattr(Base.classes, 'quan_' + feeder_id)
        else:
            raise IOError
        re = dict(sess.query(tbclass.time_record, getattr(tbclass, item)).filter(tbclass.time_record.between(int(in_str[1][0]), \
                                                               int(in_str[1][1]))).order_by(tbclass.time_record).all())
        if not re:
            re = dict(sess.query(tbclass.time_record, getattr(tbclass, item)).filter(tbclass.time_record<=int(in_str[1][0])).\
                    order_by(tbclass.time_record.desc()).limit(1).all())

        for key,value in re.items():
            if isinstance(value,Decimal):
                re[key]=float(value)
        if len(re) == 1 and int(tuple(re.keys())[0]) < int(in_str[1][0]):      
            re[str(in_str[1][0])] = int(re.pop(int(tuple(re.keys())[0])))
        result[item]=re
    return result

if __name__ == '__main__':
    #re=wxGetSQLHistory(['黄陂/第一舍/第一栏',[1000000000,1400000000],['equi_acc_mat']])
    mqq=['online_stat','act_stat','set_run','feed_num',
                        'aver_age','vacant_time','trig_inter','trig_num',"cali_quan",
                        'wat_fer_rate']
    re = sql_readCurrentStatus(['黄陂/第一舍/第一栏',mqq])
    print(re)