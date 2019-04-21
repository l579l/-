#coding=utf-8
from sqlalchemy import create_engine,func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
import json

from conf import *
#转换设备状态函数
from produce_server.prod_orm import switchDeviceStat

engine = create_engine(MYSQL_CONNECT,pool_size=10,max_overflow=3,echo_pool=True)
#engine = create_engine("mysql+pymysql://cc:123123@localhost:3306/zxzldb?charset=utf8",\
#                        pool_size=10,max_overflow=3,echo_pool=True)
Session = sessionmaker(bind=engine)  #订制会话
Base =automap_base()
Base.prepare(engine,reflect=True)

#注册
def mysqlWriteUserInfo(name,passwd,phone,auth):
    sess=Session()
    user = Base.classes.device_user
    try:
        sess.add(user(real_name=name,password=passwd,phone=int(phone),role=auth))
        sess.commit()
    except:
        return 0
    finally:
        sess.close()
    return 1

#检查电话号码是否唯一
def mysqlCheckUserName(phone):
    sess=Session()
    user=Base.classes.device_user
    if sess.query(user.phone).filter_by(phone=phone).all():
        sess.close()
        return True
    sess.close()
    return False

#登陆
def readUserPasswd(phone):
    sess=Session()
    user=Base.classes.device_user
    res=sess.query(user.password).filter_by(phone=phone).all()
    sess.close()
    if res:
        return res[0][0]
    else:
        return False

#查询用户权限
def readUserAuth(phone):
    sess=Session()
    user=Base.classes.device_user
    res=sess.query(user.role).filter_by(phone=phone).one()
    sess.close()
    if res:
        return res[0]
    else:
        return False

#读取设备状态
def readDeviceStatus(deviceSN):
    sess=Session()
    dev=Base.classes.prod_device
    res=sess.query(dev.device_stat).filter_by(deviceSN=deviceSN).one()
    sess.close()
    if res:
        return res[0]
    else:
        return ''

#修改用户信息,modify_dic：{字段：修改值}，可修改字段包括：
# 用户名：'real_name' ;密码：'password';权限：‘role’；工号：'employee_id'。
def mysqlModifyUserInfo(user_id,modify_dic):
    sess=Session()
    user=Base.classes.device_user
    try:
        sess.query(user).filter_by(phone=user_id).update(modify_dic)
        sess.commit()
    except:
        sess.rollback()
        return False
    finally:
        sess.close()
    return True

# ============= 添加合同信息 ================= #
# 输入：CompanyInfo(字典)
# -contract_num             合同号
# -tax_payer                纳税人识别号
# -company_name             公司名
# -company_addr             公司地址
# -legal_person             法人
# -legal_person_phone(NULL) 法人电话（可选）
# -principal_person         合同负责人
# -principal_person_phone   合同负责人电话
# -company_id               公司的纳税人识别号（唯一标示）
# -contract_date            购买日期
# -dev_activate_date        设备激活日期（可选）
# -dev_deadline_date        失效日期 （可选）
# -expiry_time              设备有效期
# -purcha_num               购买的设备数量
# 输出：True or False
def mysqlAddContractInfo(CompanyInfo):
    sess=Session()
    contract_info = Base.classes.contract_info
    #try:
    sess.add(contract_info(**CompanyInfo))
    sess.commit()
    #except:
    sess.close()
    return True

# 添加购买设备的SN，同时改变设备状态
# 输入：DeviceSN_list（列表）
# 输出：True or False
def mysqlPurchaseDevice(contract_num,deviceSN_list):
    sess = Session()
    setting_info = Base.classes.dev_setting_info
    status_info = Base.classes.dev_status_info
    try:
        for deviceSN in deviceSN_list:
            print(deviceSN)
            sess.add(setting_info(deviceSN=deviceSN,contract_num=contract_num))
            sess.add(status_info(deviceSN=deviceSN, contract_num=contract_num))
            switchDeviceStat(deviceSN,'B')
            sess.commit()
    except:
        sess.rollback()
        sess.close()
        return False
    sess.close()
    return True

# 查看合同信息
# 输入：合同号（字符串）
# 输出：合同信息（字典）
def mysqlGetContractInfo(contract_num):
    sess=Session()
    contract_info = Base.classes.contract_info
    #try:
    res=sess.query(contract_info).filter_by(contract_num=contract_num).all()[0]
    #except:
    #sess.close()
    #return False
    sess.close()
    return {'contract_num':res.contract_num,
            'tax_payer': res.tax_payer,
            'company_name':res.company_name,
            'company_addr':res.company_addr,
            'legal_person':res.legal_person,
            'legal_person_phone':res.legal_person_phone,
            'principal_person':res.principal_person,
            'principal_person_phone':res.principal_person_phone,
            'contract_date':res.contract_date,
            'dev_activate_date':res.dev_activate_date,
            'dev_deadline_date':res.dev_deadline_date,
            'expiry_time':res.expiry_time,
            'purcha_num':res.purcha_num
            }

# 获取合同号
def mysqlGetContractNum():
    sess=Session()
    contract_info = Base.classes.contract_info
    res=sess.query(contract_info.contract_num).all()
    sess.close()
    return [con_num[0] for con_num in res]

# 删除合同
# 输入合同号
# 输出 True or False
def mysqlDeleteContract(contract_num):
    return True

def mysqlModifyContract(modify_info):
    return True