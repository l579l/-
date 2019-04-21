#coding=utf-8
from sqlalchemy import create_engine,func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
import json
from conf import *

engine = create_engine(MYSQL_CONNECT,pool_size=10,max_overflow=3,echo_pool=True)
# engine = create_engine("mysql+pymysql://cc:123123@localhost:3306/zxzldb_new?charset=utf8",\
#                        pool_size=10,max_overflow=3,echo_pool=True)
Session = sessionmaker(bind=engine)  #订制会话
Base =automap_base()
Base.prepare(engine,reflect=True)

#获取最大deviceSN,测试用
def getMaxDeviceSN():
    sess=Session()
    dev = Base.classes.prod_device
    res=sess.query(func.max(dev.deviceSN)).one()
    sess.close()
    return res[0]

#切换设备当前位置状态，分A,B,C,D,表示设备贴标签,
def switchDeviceStat(deviceSN,status):
    sess=Session()
    dev = Base.classes.prod_device
    sess.query(dev).filter_by(deviceSN=deviceSN).update({dev.device_stat:status})
    sess.commit()
    sess.close()
    return True


#读取prod_user表，返回用户名和密码
def readProdUser():
    sess = Session()
    user = Base.classes.device_user
    if sess.query(func.count('*')).select_from(user).filter_by(role='L').scalar() != 1:
        raise Exception("prod_user表异常,行数超过一行！\n")
    res=sess.query(user).filter_by(role='L').first()
    sess.close()
    return {'username':res.real_name,'passwd':res.password}

#插入，将deviceSN和cpuID插入数据库
def writeDeviceSN(cpuID,deviceSN):
    sess=Session()
    dev = Base.classes.prod_device
    try:
        sess.add(dev(cpuID=cpuID,deviceSN=deviceSN,print_stat=0,device_stat='A'))
        sess.commit()
    except:
        return 0
    sess.close()
    return 1

#查询是否包含某cpuID
def checkcpuID(cpuID):
    sess=Session()
    dev = Base.classes.prod_device
    res = sess.query(dev).filter_by(cpuID=cpuID).all()
    sess.close()
    if res:
        return True
    return False

#查询，输入cpuID查询对应deviceSN
def readProdCPUID(cpuID):
    sess = Session()
    dev = Base.classes.prod_device
    res = sess.query(dev.deviceSN).filter_by(cpuID=cpuID).all()
    sess.close()
    if res:
        return res[0][0]
    else:
        return ''

#查询，输入deviceSN查询对应cpuID
def readProdDeviceSN(deviceSN):
    sess = Session()
    dev = Base.classes.prod_device
    res = sess.query(dev.cpuID).filter_by(deviceSN=deviceSN).all()
    sess.close()
    if res:
        return res[0][0]
    else:
        return ''

#查询，输入时间段，返回该范围内cpuID和deviceSN
def readProdTime(startTime,endTime):
    #print(startTime,' ',endTime)
    sess = Session()
    dev = Base.classes.prod_device
    res = sess.query(dev.deviceSN,dev.cpuID).\
          filter(dev.prod_date.between(startTime,endTime)).\
          order_by(dev.prod_date).all()
    sess.close()
    if res:
        return dict(res)
    else:
        return {}

#读未打印设备的deviceSN和cpuID
def readProdNoPrint():
    sess = Session()
    dev = Base.classes.prod_device
    res = sess.query(dev.deviceSN,dev.cpuID).filter_by(print_stat=0).all()
    sess.close()
    if res:
        return dict(res)
    else:
        return {}

#切换设备打印状态，0：未打印，1：已打印
def switchPrintStat(deviceSNList):
    sess=Session()
    print("传给数据库转换状态接口的列表：",deviceSNList)
    dev = Base.classes.prod_device
    try:
        for deviceSN in deviceSNList:
            sess.query(dev).filter_by(deviceSN=deviceSN).update({dev.print_stat:1})
        sess.commit()
    except:
        sess.rollback()
        return False
    finally:
        sess.close()
    return True

if __name__=="__main__":
    ##res=readProdUser()
    #DeviceSN: 18435023 is produced by CPUID: UF31SosH8wg4vXEh5c0ipzPY
    deviceSN='18435023';cpuID='UF31SosH8wg4vXEh5c0ipzPY'
    ##print(writeDeviceSN(cpuID,deviceSN))
    ##print(chechDeviceSN('UF31SosH8wg4vXEh5c0ipzPY'))
    ##print(readProdCPUID(deviceSN))
    #res=readProdDeviceSN('2018-10-26 17:12:07','2018-10-26 17:13:07')
    # print(switchDeviceS-Stat('RMLnFbBW8imq67Kc5kHtSP1C','E'))
    #res=readProdCPUID
    #print(res)
