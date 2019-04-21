# coding=utf-8
from sqlalchemy import create_engine,func,and_
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
# 转换设备状态函数
from produce_server.prod_orm import switchDeviceStat
import json
from conf import *
print("operation_server连接数据库")

engine = create_engine(MYSQL_CONNECT,pool_size=10,max_overflow=3,echo_pool=True)
# engine = create_engine("mysql+pymysql://cc:123123@localhost:3306/zxzldb?charset=utf8",\
#                        pool_size=10,max_overflow=3,echo_pool=True)
Session = sessionmaker(bind=engine)  #订制会话
Base = automap_base()
Base.prepare(engine,reflect=True)


# 输入公司的纳税人识别号，  获取该公司名下所有的合同号
def mysqlGetCompanyContract(tax_payer):
    sess = Session()
    contract = Base.classes.contract_info
    res = sess.query(contract.contract_num).filter_by(tax_payer=tax_payer).all()
    sess.close()
    if res:
        return res
    else:
        raise Exception('该纳税人识别号：'+tax_payer+' 公司没有添加合同')


#输入纳税人识别号，获取公司名下的所有员工
def mysqlGetCompanyMember(tax_payer):
    sess = Session()
    user = Base.classes.device_user
    res = sess.query(user.phone).filter_by(tax_payer=tax_payer).all()
    sess.close()
    if res:
        return res
    else:
        raise Exception('该纳税人识别号：'+tax_payer+' 公司没有添加员工')


# 修改猪场名
# 输入：用户id，旧猪场名，新猪场名
# 输出：True（修改成功） or False（修改失败）
def mysqlChangeFarmName(tax_payer, oldfarmname, newfarmname):
    sess = Session()
    for obj,tb_attr in {'dev_setting_info':'contract_num','dev_status_info':'contract_num',\
        'user_link_dev':'phone'}.items():
        tb_obj=getattr(Base.classes,obj)
        if obj== 'user_link_dev':
            choose_cond = mysqlGetCompanyMember(tax_payer)
        else:
            choose_cond = mysqlGetCompanyContract(tax_payer)
        for cond in choose_cond:
            alias_tmp = sess.query(tb_obj.alias).filter(and_(getattr(tb_obj,tb_attr)==cond[0],tb_obj.alias.like('/' + oldfarmname + '%'))).all()
            alias_list = [i[0] for i in alias_tmp]
            # print(alias_list)
            for alias in alias_list:
                new_alias = '/' + newfarmname + '/' + alias.split('/',2)[2]
                res = sess.query(tb_obj).filter(and_(getattr(tb_obj,tb_attr)==cond[0],tb_obj.alias==alias)).update({'alias':new_alias})
                if not res:
                    sess.close()
                    return False
    #报错回滚：sess.rollback()
    sess.commit()
    sess.close()
    return True


# 添加设备SN，不改变设备状态
# 输入：设备SN，设备将要添加的地址（‘黄陂/第1舍’ or ‘demonstration’）
#       若要添加的地址为demonstration,则1小时候自动解绑
#       若要添加的地址为黄陂/第1舍,保存在数据库中的别名为黄陂/第1舍/第n栏，n依次增加
# 输出：True（成功） or False（失败）
def mysqlAddDeviceSN(deviceSN, alias):
    sess=Session()
    setting_info = Base.classes.dev_setting_info
    status_info = Base.classes.dev_status_info
    try:
        res1=sess.query(setting_info).filter_by(deviceSN=deviceSN).update({'alias':alias})
        res2=sess.query(status_info).filter_by(deviceSN=deviceSN).update({'alias': alias})
        # print('res1',res1,'res2',res2)
        sess.commit()
        # switchDeviceStat(deviceSN, newDeviceStatus)
    except:
        sess.rollback()
        sess.close()
        return False
    sess.close()
    if res1 and res2:
        return True
    return False


# 解绑设备
# 输入：设备SN
# 输出：True（解绑成功）or False（解绑失败）
def mysqlUnbindDeviceSN(deviceSN,newDeviceStatus):
    sess = Session()
    setting_info = Base.classes.dev_setting_info
    status_info = Base.classes.dev_status_info
    try:
        res1 = sess.query(setting_info).filter_by(deviceSN=deviceSN).update({'alias': 'NULL'})
        res2 = sess.query(status_info).filter_by(deviceSN=deviceSN).update({'alias': 'NULL'})
        sess.commit()
        switchDeviceStat(deviceSN, newDeviceStatus)
    except:
        sess.rollback()
        sess.close()
        return False
    sess.close()
    if res1 and res2:
        return True
    return False


# 查看用户所属公司的纳税人识别号
# 输入：user_id（字符串）
# 输出：tax_payer（字符串）
def mysqlGetUserTaxPayer(user_id):
    sess=Session()
    user=Base.classes.device_user
    res=sess.query(user.tax_payer).filter_by(phone=user_id).one()
    sess.close()
    if res:
        return res[0]
    else:
        return False


# 查看猪舍下有哪些栏和设备
# 输入：tax_payer（字符串）纳税人识别号
#      alias(列表)： ['/黄陂/第1舍/第1栏','/黄陂/第1舍/第2栏']
# #                 ['/黄陂/第1舍/','/黄陂/第2舍/']
# #                 ['/黄陂/','/汉口/']
# #                 ['/']
# 输出：[(deviceSN:alias)](元组列表)
def mysqlGetStyInfo(tax_payer,alias_list,query_list):
    sess = Session()
    setting_info = Base.classes.dev_setting_info
    contract = mysqlGetCompanyContract(tax_payer)
    res = []
    attr_list=[]
    for attr in query_list:
        attr_list.append(getattr(setting_info,attr))
    for alias in alias_list:
        for contract_num in contract:
            res += sess.query(*tuple(attr_list)).\
                       filter(and_(setting_info.contract_num==contract_num[0],setting_info.alias.like(alias + '%'))).all()
    # print(res)
    sess.close()
    return res


# 删除猪场，猪舍，猪栏
def mysqlDeleteFarm(tax_payer,alias_list):
    sess = Session()
    for alias in alias_list:
        for obj,tb_attr in {'dev_setting_info':'contract_num','dev_status_info':'contract_num',\
            'user_link_dev':'phone'}.items():
            tb_obj=getattr(Base.classes,obj)
            if obj== 'user_link_dev':
                choose_cond = mysqlGetCompanyMember(tax_payer)
            else:
                choose_cond = mysqlGetCompanyContract(tax_payer)
            for cond in choose_cond:
                query_res = sess.query(tb_obj).filter(and_(getattr(tb_obj,tb_attr)==cond[0],tb_obj.alias.like(alias+'%')))
                if query_res.all():
                    query_res.update({'alias':'NULL'},synchronize_session=False)

    #报错回滚：sess.rollback()
    sess.commit()
    sess.close()
    return True


# 查看设备所属公司的纳税人识别号
# 输入：deviceSN（字符串）
# 输出：tax_payer（字符串）
def mysqlGetDeviceTaxPayer(deviceSN):
    sess = Session()
    setting_info = Base.classes.dev_setting_info
    contract_info = Base.classes.contract_info
    res1 = sess.query(setting_info.contract_num).filter_by(deviceSN=deviceSN).one()
    res2 = sess.query(contract_info.tax_payer).filter_by(contract_num=res1[0]).one()
    sess.close()
    if res2:
        return res2[0]
    else:
        return False


# 查看设备对应的别名
def mysqlGetDeviceAlias(deviceSN):
    sess = Session()
    status_info = Base.classes.dev_status_info
    res = sess.query(status_info.alias).filter_by(deviceSN=deviceSN).one()
    sess.close()
    if res and res != 'NULL':
        return res[0]
    else:
        return False

# # 查看user和alias是否关联
# # 输入：alias(列表)
# #      user_id(字符)
# # 输出：True or False
# def mysqlCheckUserAlias(user_id,alias):
#     sess = Session()
#     user_link_dev = Base.classes.user_link_dev
#     res = sess.query(user_link_dev).filter(and_(user_link_dev.phone==user_id,user_link_dev.alias.like(alias+'%'))).all()
#     sess.close()
#     # if res:
#     #     return False
#     return True


# 测试用
def switchUserStat(user_id, status):
    sess = Session()
    user = Base.classes.device_user
    sess.query(user).filter_by(phone=user_id).update({user.role: status})
    sess.commit()
    sess.close()
    return True


# 添加员工：绑定纳税人识别号，绑定alias，绑定权限
# 输入：待添加人用户id，待加入公司的纳税人识别号tax_payer，待添加的alias列表，待赋予的权限
# 输出：True(成功) or False（失败）
def mysqlAddMember(user_id, tax_payer, alias_list, user_auth):
    sess = Session()
    dev_user = Base.classes.device_user
    user_link = Base.classes.user_link_dev
    try:
        sess = add(dev_user(phone=user_id, tax_payer=tax_payer, role=user_auth))
        for alias in alias_list:
            sess.add(user_link(alias=alias))
        sess.commit()
    except:
        sess.rollback()
        sess.close()
        return False
    sess.close()
    return True


# 删除员工：删除user的tax_payer，删除user下的alias，将其权限改为Z
# 输入：待删除人的id
# 输出：True（成功）or False（失败）
def mysqlDeleteUser(delete_userid):
    sess = Session()
    user1 = Base.classes.device_user
    user2 = Base.classes.user_link_dev
    try:
        res1 = sess.query(user1).filter_by(phone=delete_userid).update({'tax_payer': 'NULL'},{'role':'Z'})
        res2 = sess.query(user2).filter_by(phone=delete_userid).update({'alias':'NULL'})
        sess.commit()
    except:
        sess.rollback()
        sess.close()
        return False
    sess.close()
    if res1 and res2:
        return True
    else:
        return False


# 根据user_id查找用户可操控的alias
# 输入：user_id
# 输出：alias列表
def mysqlGetUserAlias(user_id):
    sess = Session()
    user = Base.classes.user_link_dev
    res = sess.query(user.alias).filter_by(phone=user_id).all()
    sess.close()
    if res != 'NULL'and res:
        return res
    else:
      # raise Exception('该用户：' + user_id + ' 没有可操控的alias')
        return False


# 根据公司纳税人识别号查看用户信息
# 输入：纳税人识别号
# 输出：用户信息[(user_id,alias),...]
def mysqlGetUserInfo(tax_payer,auth):
    sess = Session()
    user_info = []
    dev_user = Base.classes.device_user
    user_link = Base.classes.user_link_dev
    res1 = sess.query(dev_user.phone).filter_by(and_(tax_payer==tax_payer,role==auth)).all()
    if res1:
        for cond1 in res1:
            res2 = sess.query(user_link.alias).filter_by(phone==cond1).all()
            if res2:
                for cond2 in res2:
                    a = (cond1,cond2)
                    user_info.append(a)
            else:
                sess.close()
                return False
        sess.close()
        return user_info
    else:
        sess.close()
        return False
