#coding=utf-8
from sanic import response,Blueprint
from mqtt_server.mqtt_server import *
import paho.mqtt.publish as publish
from operation_server.operation_orm import *
from purchase_server.purchase_orm import readDeviceStatus,readUserAuth
from produce_server.prod_orm import switchDeviceStat
from conf import *
import threading
import redis
import time
operation_bp=Blueprint('operation_bp')

# MQTT客户端实例化
hostname = MQTT_HOSTNAME
port = MQTT_PORT
operation_client = mqtt_client(MQTT_CLIENTNAME + "operation", hostname, port)
# ========= 服务器MQTT订阅主题约定 ========= #
# Data/+            一些下位机的累计数据（下位机每天固定时间发布）
# Setting/+         一些随时可能更改的数据
# Alert/+           一些报警信息
# Status/+          一些状态信息
# ComCtrl/#         预留的交互通道
operation_client.connect(['Data/#','Setting/#','Alert/#','Status/#','ComCtrl/activate/+'])
redis_pool = redis.ConnectionPool(host = '127.0.0.1', port = 6379, decode_responses = True)
redis_ex = redis.Redis(connection_pool = redis_pool)
check_time = 5    # 演示设备有效期5s

# ==================== 函数 ==================== #
# 根据判断alias判断权限
def judgeAuthFromAlias(alias):
    alias_split = alias.split('/')
    len_alias_split = len(alias_split)
    if len_alias_split == 2:
        return 'A'
    elif len_alias_split == 3:
        return 'B'
    elif len_alias_split == 4 and alias_split[-1] == '':
        return 'C'
    elif len_alias_split ==4 and alias_split[-1] != '':
        return 'D'

# 判断待添加的alias属于操作人可管理的alias
def judgeUserAuth(user_id,target_alias_list):
    alias_list = mysqlGetUserAlias(user_id)
    alias_split_list = [target_alias[:len(alias_list[0])] for target_alias in target_alias_list]
    for i in alias_split_list:
        if i not in alias_list:
            return False
    return True



# ========================================================= #
# ======================= 猪场管理 ========================= #
# ========================================================= #
# A：老板
# B：猪场管理员
# C：猪舍管理员
# D：设备操作员
# M：卖家销售：可绑定未售出的设备进行演示
# P：卖家管理合同的权限
# S：开发人员权限
# Z：空权限代码：用户最初注册时为此权限

# =========== 新建猪场,猪舍 ============ #
# 验证操作人身份
# -猪场名 farm_name
# -猪舍名 pen_name
@operation_bp.route('/operation/BuildFarm/<build_type>', methods=['POST'])
async def operation_BuildFarm(request,build_type):
    # 从数据库查找操作人权限，并验证是否为老板
    user_id = request['session'].get('user_id')
    tax_payer = mysqlGetUserTaxPayer(user_id)
    user_auth = readUserAuth(user_id)
    if build_type == 'farm' and user_auth == 'A':
        farm_name = request.form.get('farm_name')
        farmName_list = redis_ex.lrange(tax_payer,0,-1)
        # 若猪场名存在
        if farm_name in farmName_list:
            print(farm_name,'猪场已存在！')
            return response.json({'status': 'existed'})
        # 将猪场信息保存至redis
        redis_ex.lpush(tax_payer, farm_name)
        print(farm_name,'猪场新建成功！')
        return response.json({'status': 'success'})
    elif build_type == 'pen' and user_auth in 'AB':
        farm_name = request.form.get('farm_name')
        pen_name = request.form.get('pen_name')
        pen_name_list = pen_name.split(',')
        pen_name_list = list(set(pen_name_list))
        exsit_pen = []
        for i in pen_name_list:
            if i in redis_ex.lrange(tax_payer+'/'+farm_name,0,-1):
                exsit_pen.append(i)
            else:
                redis_ex.rpush(tax_payer + '/' + farm_name, i)
        if exsit_pen != []:
            print('猪舍：',exsit_pen,'已存在')
            return response.json({'status':'existed','exsit_pen':exsit_pen})
        else:
            print('猪舍：',pen_name_list,'新建成功')
            return response.json({'status':'success'})
    else:
        print('无访问权限')
        return response.json({'status':'nopower'})


# =========== 修改猪场信息 ============ #
# 验证操作人权限
# 修改猪场名
@operation_bp.route('/operation/ModifyFarmInfo', methods=['POST'])
async def operation_modifyFarmInfo(request):
    user_id = request['session'].get('user_id')
    tax_payer = mysqlGetUserTaxPayer(user_id)
    user_auth = readUserAuth(user_id)
    if user_auth != 'A':
        return response.json({'status':'nopower'})
    old_farm_name = request.form.get('old_farm_name')
    new_farm_name = request.form.get('new_farm_name')
    print('old_farm_name:',old_farm_name,'new_farm_name:',new_farm_name)
    # 将修改信息保存至mysql
    status = mysqlChangeFarmName(tax_payer, old_farm_name, new_farm_name)
    if not status:
        print('mysql修改失败')
        return response.json({'status':'warn'})
    # 将修改信息保存至redis
    if not redis_ex.lrem(tax_payer, old_farm_name, 0):
        print('redis修改失败')
        return response.json({'status':'warn'})
    pen_list = redis_ex.lrange(tax_payer+'/'+old_farm_name,0,-1)
    redis_ex.lpush(tax_payer, new_farm_name)
    redis_ex.delete(tax_payer+'/'+old_farm_name)
    for i in pen_list:
        redis_ex.lpush(tax_payer+'/'+new_farm_name,i)
    print('猪场名修改成功')
    return response.json({'status': 'success'})

# =========== 删除猪场or猪舍or设备 ============ #
# 验证身份
# 删除redis
# 删除数据库中的信息
@operation_bp.route('/operation/deleteFarmInfo', methods=['POST'])
async def operation_deleteFarmInfo(request):
    user_id = request['session'].get('user_id')
    tax_payer = mysqlGetUserTaxPayer(user_id)
    alias = request.form.get('alias')
    alias_list = alias.split(',')
    user_auth = readUserAuth(user_id)
    len_of_alias = len(alias_list[0].split('/'))
    print('要删除的alias:',alias_list)
    # 删除多个猪场 [/黄陂/,/江夏/]
    if len_of_alias == 3 and user_auth in 'A':
        status = mysqlDeleteFarm(tax_payer, alias_list)
        if not status:
            print('猪场删除失败！')
            return response.json({'status': 'warn'})
        for i in alias_list:
            farm_name = i.split('/')[1]
            redis_ex.lrem(tax_payer,farm_name)
            redis_ex.delete(tax_payer + '/' + farm_name)
        print(farm_name, '猪场删除成功！')
        return response.json({'status':'success'})
    # 删除猪舍 [/黄陂/第1舍/,/黄陂/第2舍/]
    elif len_of_alias == 4 and user_auth in 'AB' and alias_list[0][-1] == '/':
        status = mysqlDeleteFarm(tax_payer, alias_list)
        if not status:
            return response.json({'status': 'warn'})
        for i in alias_list:
            farm_name = i.split('/')[1]
            pen_name = i.split('/')[2]
            redis_ex.lrem(tax_payer+'/'+farm_name,pen_name)
            print(pen_name, '猪舍删除成功！')
        return response.json({'status': 'success'})
    # 删除猪栏 [/黄陂/第1舍/第1栏,/黄陂/第1舍/第2栏]
    elif len_of_alias == 4 and user_auth in 'AB' and alias_list[0][-1] != '/':
        status = mysqlDeleteFarm(tax_payer, alias_list)
        if not status:
            return response.json({'status': 'warn'})
        print(alias_list, '猪舍删除成功！')
        return response.json({'status': 'success'})
    else:
        print('无访问权限')
        return response.json({'status': 'nopower'})

# =========== 查看猪场,猪舍,猪栏（设备） ============ #
#根据用户权限只显示其可控制的猪场、猪舍、猪栏
@operation_bp.route('/operation/GetFarmInfo/<get_type>', methods=['POST'])
async def operation_getFarmInfo(request,get_type):
    user_id = request['session'].get('user_id')
    tax_payer = mysqlGetUserTaxPayer(user_id)
    user_auth = readUserAuth(user_id)
    if get_type == 'farm':
        res = {}
        if user_auth == 'A':
            res['farm_list'] = redis_ex.lrange(tax_payer, 0, -1)
        else:
            alias_list = mysqlGetUserAlias(user_id)
            res['farm_list'] = list(set([alias.split('/')[1] for alias in alias_list]))
        res['status'] = 'success'
        print('猪场:',res['farm_list'])
        return response.json(res)
    elif get_type == 'pen':
        farm_name = request.form.get('farm_name')
        res = {}
        if user_auth in 'AB':
            res['pen_list'] = redis_ex.lrange(tax_payer + '/' + farm_name, 0, -1)
        else:
            alias_list = mysqlGetUserAlias(user_id)
            for alias in alias_list:
                if farm_name not in alias:
                    alias_list.pop(alias)
            res['pen_list'] = list(set([alias.split('/')[2] for alias in alias_list]))
        res['status'] = 'success'
        print('猪舍:', res['pen_list'])
        return response.json(res)
    elif get_type == 'sty':
        farm_name = request.form.get('farm_name')
        pen_name = request.form.get('pen_name')
        res = {}
        if user_auth in 'ABC':
            status = mysqlGetStyInfo(tax_payer,['/' + farm_name + '/' + pen_name + '/'],['deviceSN','alias'])
            res['device_list'] = [device + (readDeviceStatus(device[0]),) for device in status]
        else:
            alias_list = mysqlGetUserAlias(user_id)
            for alias in alias_list:
                if farm_name+'/'+pen_name not in alias:
                    alias_list.pop(alias)
            res['pen_list'] = list(set([alias.split('/')[3] for alias in alias_list]))
        res['status'] = 'success'
        print('猪栏:', res['device_list'])
        return response.json(res)


# ========== 添加员工 ============= #
# 添加员工的权限add_userAuth
# 验证待添加账号权限为Z，方可添加
# 验证待添加的alias属于操作人可管理的alias
# 验证用户输入的auth合理
# 将员工和公司纳税人识别号及alias绑定，同时赋予相应的权限，保存至数据库
@operation_bp.route('/operation/addMember', methods=['POST'])
async def operation_addmember(request):
    user_id = request['session'].get('user_id')     # 操作人员的user_id
    user_auth = readUserAuth(user_id)               # 操作人员的权限
    target_userID = request.form.get('add_userID')               # 待添加员工的user_id
    if user_auth in 'AB':
        add_userAuth = readUserAuth(target_userID)
        # 若待添加员工的权限为Z，方可添加
        if add_userAuth == 'Z':
            # 根据alias判断待赋予员工的权限
            target_alias_list = json.loads(request.form.get('alias'))           # 待绑定的alias列表
            target_userAuth_judge = judgeAuthFromAlias(target_alias_list[0])    # 根据alias判断的权限
            target_userAuth_real = request.form.get('add_userAuth') # 前端发来实际的权限
            print('判断的auth：',target_userAuth_judge,'实际的auth：',target_userAuth_real)
            # 验证前端发来的权限合理
            # 验证待添加的alias属于操作人可管理的alias,
            if target_userAuth_judge <= target_userAuth_real and judgeUserAuth(user_id,target_alias_list):
                # 获取用户纳税人识别号
                tax_payer = mysqlGetUserTaxPayer(user_id)
                # 将员工信息添加到对应猪场or猪舍下，并赋予对应的权限
                status = mysqlAddMember(target_userID, tax_payer, target_alias_list, target_userAuth_real)
                if not status:
                    return response.json({'status':'warn'})
                return response.json({'status':'success'})
    elif user_auth == 'P':
        tax_payer = request.form.get('tax_payer')
        print('userid:',user_id,'纳税人识别号:',tax_payer)
        status = mysqlAddMember(target_userID,tax_payer,alias_list=['/'],user_auth='A')
        if not status:
            return response.json({'status':'warn'})
        return response.json({'status':'success'})
    else:
        return response.json({'status':'nopower'})

# ========== 删除员工（主动退出？） ============= #
# 操作人权限user_auth为A或B
# 待删除员工的权限delete_userauth
# 根据alias判断用户是否有权限删除该员工
# 删除数据库中员工的信息,并改变其权限
@operation_bp.route('/operation/deleteMember', methods=['POST'])
async def operation_deletemember(request):
    user_id = request['session'].get('user_id')
    user_auth = readUserAuth(user_id)
    delete_userID = request.form.get('delete_userID')   # 将被删除的员工的user_id
    # 验证用户是否属于同一公司
    operation_tax_payer = mysqlGetUserTaxPayer(user_id)
    delete_tax_payer = mysqlGetUserTaxPayer(delete_userID)
    delete_alias_list = mysqlGetUserAlias(delete_userID)
    # 验证操作人有权限删除员工
    if operation_tax_payer == delete_tax_payer and user_auth in 'AB' and judgeUserAuth(user_id,delete_alias_list):
        # 删除该公司下的某一员工信息，并将用户的权限改为Z（不属于任何公司）
        status = mysqlDeleteUser(delete_userID)
        if not status:
            return response.json({'status': 'warn'})
        return response.json({'status': 'success'})
    else:
        return response.json({'status': 'nopower'})

# ========== 修改员工 ============= #
@operation_bp.route('operation/modifyMember/<type>',methods=['POST'])
async def operation_modifyMember(request,type):
    user_id = request['session'].get('user_id')  # 操作人员的user_id
    user_auth = readUserAuth(user_id)  # 操作人员的权限
    target_userID = request.form.get('target_userID')  # 待修改员工的user_id
    alias = request.form.get('alias')  # 待修改的alias
    # 验证操作用户权限为A或B
    # 验证待添加或删除的alias属于操作人可管理的alias,
    if user_auth in 'AB' and judgeUserAuth(user_id, alias):
        status = mysqlModifyUserAlias(type,target_userID,alias)
        if not status:
            return response.json({'status': 'warn'})
        return response.json({'status': 'success'})
    else:
        return response.json({'status':'nopower'})

# ========== 查看员工 ============= #
# 根据auth和公司的纳税人识别号查看员工信息
# 返回{user_id:{'黄陂':{'第1舍':['第1栏','第2栏']}}}
@operation_bp.route('/operation/getMember/<auth:[A-D]+>', methods=['GET'])
async def operation_getMember(request,auth):
    user_id = request['session'].get('user_id')
    tax_payer = mysqlGetUserTaxPayer(user_id)
    res = mysqlGetUserInfo(tax_payer, auth)
    return response.json({'status':'success','res':res})

# ========================================================= #
# ======================= 设备管理 ========================= #
# ========================================================= #
# A（出厂状态）
# B（售出但设备未投入使用）
# C0（设备已绑定，未激活）
# C1（设备已绑定，已激活）
# D（设备过期）

# =========== 绑定设备 ============ #
# 验证操作人所属公司是否和设备所属公司相同
# 验证设备是否已经绑定
# 设备将要绑定的地址('/黄陂/第1舍/第1栏'）
# 将deviceSN与设备别名绑定，保存至数据库
# 不修改设备状态码，此时设备处于不可用状态
# 要求卖家端能实现自动解绑
@operation_bp.route('/operation/addDeviceSN', methods=['POST'])
async def operation_addDeviceSN(request):
    user_id = request['session'].get('user_id')
    user_auth = readUserAuth(user_id)
    deviceSN = request.form.get('deviceSN')
    device_status = readDeviceStatus(deviceSN)

    alias = request.form.get('alias')     # 设备将要绑定的地址'/黄陂/第1舍/第一栏'
    print('deviceSN:', deviceSN,'alias:',alias)
    # 如果是卖家销售的权限
    if user_auth == 'M' and device_status == 'A':
        if redis_ex.get(deviceSN):
            return response.json({'status':'deviceHasBinded'})   # 设备已被绑定
        else:
            redis_ex.set(name=deviceSN, value=user_id, ex=30)
            return response.json({'status':'success'})
    # 如果是买家设备管理人的权限ABC
    elif user_auth in 'ABC' and device_status[0] == 'C':
        # 判断设备所属公司和user_id所属公司是否一致,
        # 判断设备将要绑定的alias是否属于该用户可控范围
        taxPayer_user = mysqlGetUserTaxPayer(user_id)
        taxPayer_device = mysqlGetDeviceTaxPayer(deviceSN)
        if taxPayer_user != taxPayer_device and not judgeUserAuth(user_id,[alias]):
            print('无操作权限')
            return response.json({'status':'nopower'})
        # 验证设备是否已经绑定
        dev_status = mysqlGetDeviceAlias(deviceSN)
        if dev_status:
            print('设备已经绑定')
            return response.json({'status':'deviceHasBinded'})
        # 判断同一公司下alias是否已存在
        status = mysqlGetStyInfo(taxPayer_user,[alias],['alias'])
        # 若存在
        if status:
            print('alias:',alias,'已存在')
            return response.json({'status':'aliasexist'})
        # 若满足，将绑定的信息保存至数据库
        status =  mysqlAddDeviceSN(deviceSN, alias)
        if not status:
            print('绑定失败,写入数据库失败')
            return response.json({'status':'warn'})
        print('绑定成功')
        # 绑定成功后，将猪场唯一标识hogpenID（纳税人识别号+猪场名）发送给下位机，不管下位机是否开机
        HogpenID = taxPayer_user + alias  # HogpenID：2314141242/黄陂/第1舍/第1栏
        publish.single("ComServer/Hogpen/" + deviceSN, payload=HogpenID, hostname=hostname, port=port, qos=1)
        return response.json({'status':'success'})
    else:
        print('设备无法被绑定')
        return response.json({'status':'cannotBind'})   #设备无法被绑定（可能是权限问题，或设备已被绑定）


# ============ 启用设备 ============ #
# 验证操作人所属公司是否和设备所属公司相同
# 验证用户是否可操作该设备
# 若满足以上条件，将设备状态变为C1,，此时设备可用
@operation_bp.route('/operation/bindDeviceSN', methods=['POST'])
async def operation_bindDeviceSN(request):
    user_id = request['session'].get('user_id')
    user_auth = readUserAuth(user_id)
    deviceSN_list = request.form.get('deviceSN').split(',')
    print('待激活设备:',deviceSN_list)
    if user_auth in 'ABC':
        res = []
        # 判断设备所属公司和user_id所属公司是否一致
        taxPayer_user = mysqlGetUserTaxPayer(user_id)
        taxPayer_device = mysqlGetDeviceTaxPayer(deviceSN_list[0])
        if taxPayer_user != taxPayer_device:
            print('无操作权限')
            return response.json({'status': 'nopower'})
        # 验证用户是否可以操作设备
        for deviceSN in deviceSN_list:
            alias = mysqlGetDeviceAlias(deviceSN)
            status = judgeUserAuth(user_id, [alias])
            if status:
                switchDeviceStat(deviceSN,'C1')
            else:
                res.append(alias)
        if res:
            print(res,'中的设备无权操作')
            return response.json({'status':'warn','res':res})
        print('设备激活成功')
        return response.json({'status':'success'})
    else:
        print('无操作权限')
        return response.json({'status':'nopower'})

# ============ 禁用设备 ============ #
# 验证user_id所属公司和设备所属公司是否一致
# 验证用户是否有权限操作该设备
# 满足以上条件，将设备状态码变为C0，设备禁用
@operation_bp.route('/operation/unbindDeviceSN', methods=['POST'])
async def operation_unbindDeviceSN(request):
    user_id = request['session'].get('user_id')
    user_auth = readUserAuth(user_id)
    deviceSN_list = request.form.get('deviceSN').split(',')
    # 如果是卖家销售人员,且设备归属于操作人
    # if user_auth == 'M' and redis_ex.get(deviceSN_list) == user_id:
    #     # 解绑设备
    #     redis_ex.delete(deviceSN_list)
    #     return response.json({'status': 'success'})
    print('待取消激活的设备:',deviceSN_list)
    # 如果是买家设备管理人员ABC
    if user_auth in 'ABC':
        res = []
        # 判断设备所属公司和user_id所属公司是否一致
        taxPayer_user = mysqlGetUserTaxPayer(user_id)
        taxPayer_device = mysqlGetDeviceTaxPayer(deviceSN_list[0])
        if taxPayer_user != taxPayer_device:
            print('无操作权限')
            return response.json({'status': 'nopower'})
        # 验证用户是否可以操作设备
        for deviceSN in deviceSN_list:
            alias = mysqlGetDeviceAlias(deviceSN)
            status = judgeUserAuth(user_id, [alias])
            if status:
                switchDeviceStat(deviceSN,'C0')
            else:
                res.append(alias)
        # 若存在不可操作的设备，将其alias返回给前端
        if res:
            print(res, '中的设备无权操作')
            return response.json({'sttaus':'warn','res':res})
        print('取消激活成功')
        return response.json({"status":'success'})
    else:
        print('无操作权限')
        return response.json({'status':'nopower'})

# ============ （更换设备？） ============= #
@operation_bp.route('/operation/changeDeviceSN', methods=['POST'])
async def operation_changeDeviceSN(request):
    return response.text('1')

# =========== 控制设备参数 ============= #
# alias:  ['/黄陂/第1舍/第1栏','/黄陂/第1舍/第2栏']
#         ['/黄陂/第1舍/','/黄陂/第2舍/']
#         ['/黄陂/','/汉口/']
#         ['/']
# set_info: {参数：值}
# 验证用户是否可操作该alias
# 获取tax_payer以及该alias下所有的设备别名组成taxPayer_alias_list
# taxPayer_alias_list：['111111111/黄陂/第1舍/第1栏','111111111/黄陂/第1舍/第2栏']
# 根据taxPayer_alias_list生成alias_info
# 若操作对象是舍或猪场，alias_info：['111111111/黄陂/第1舍/']
# 若操作对象是多个设备，alias_info：['111111111/黄陂/第1舍/第1栏']
# 将alias_info作为MQTT的主题名，set_info作为消息发布
@operation_bp.route('/operation/set', methods=['POST'])
async def operation_set(request):
    user_id = request['session'].get('user_id')
    alias_list = json.loads(request.form.get('alias'))
    set_info = json.loads(request.form.get('set_info'))
    # msg = request.json
    # alias_list = json.loads(msg['alias'])
    # set_info = json.loads(msg['set_info'])

    # 验证用户和alias是否关联
    # for alias in alias_list:
    #     if not judgeUserAuth(user_id,[alias]):
    #         return response.json({'status':'nopower'})
    # 获取要设置的taxPayer_alias，和要设置的参数
    tax_payer = mysqlGetUserTaxPayer(user_id)
    print('alias_list',alias_list,'set_info',set_info)
    deviceSN_alias = mysqlGetStyInfo(tax_payer, alias_list, ['deviceSN','alias'])  # [('18476000','/黄陂/第1舍/第1栏')]
    print('deviceSN_alias',deviceSN_alias)
    taxPayer_alias_list = [tax_payer + i[1] for i in deviceSN_alias]     # ['111111111/黄陂/第1舍/第1栏']
    print('taxPayer_alias_list',taxPayer_alias_list)
    # 若操作对象是舍或猪场，alias_info：['111111111/黄陂/第1舍/']
    # 若操作对象是多个设备，alias_info：['111111111/黄陂/第1舍/第1栏']
    if alias_list[0] != '/':
        # 对一舍中的一台或多台饲喂器设置
        alias_info = taxPayer_alias_list
    else:
        # 对舍或猪场批量操作
        alias_info = list(set([i[0:i.rfind('/')] for i in taxPayer_alias_list]))
    print('alias_info',alias_info)
    pub_time = time.time()
    operation_client.message_pubed[str(pub_time)] = {}
    for i in taxPayer_alias_list:
        for j in set_info:
            operation_client.message_pubed[str(pub_time)][i+'/'+j] = set_info[j]
    mqtt_status = await operation_client.mqtt_set(alias_info, set_info, pub_time, time_limit=5)
    if mqtt_status == 'success':
        print("设置成功")
        # sql_writeSetMessage(alias_info, set_info, AESdecrypt(request.headers.get('UserID')),
        #                     AESdecrypt(request.headers.get('Timestamp')))
        print('写入数据库成功')
        return response.json({'status': 'success'})
    else:
        print("设置失败", mqtt_status)  # mqtt_status:list
        # alias_success = set(alias_info) - set(mqtt_status)
        # sql_writeSetMessage(alias_success, set_info, AESdecrypt(request.headers.get('UserID')),
        #                     AESdecrypt(request.headers.get('Timestamp')))
        return response.json({'status': 'error', 'alias':mqtt_status})

    # alias = request.form.get('alias')
    # if (len(alias) == 1 and alias[0][-1] == '/'):
    #     alias_info = sql_readAliasMessage(alias[0])
    # else:
    #     alias_info = alias
    # set_info = request.form.get('set')
    # mqtt_status = await operation_client.mqtt_set(alias_info, set_info, time_limit=15)
    # if 'success' == mqtt_status:
    #     print("设置成功")
    #     # sql_writeSetMessage(alias_info, set_info, AESdecrypt(request.headers.get('UserID')),
    #     #                     AESdecrypt(request.headers.get('Timestamp')))
    #     print('写入数据库成功')
    #     return response.json({'status': 'success'})
    # else:
    #     print("设置失败", mqtt_status)  # mqtt_status:list
    #     alias_success = set(alias_info) - set(mqtt_status)
    #     # sql_writeSetMessage(alias_success, set_info, AESdecrypt(request.headers.get('UserID')),
    #     #                     AESdecrypt(request.headers.get('Timestamp')))
    #     return response.json({'status': 'error'})


# =======  test  ======= #
@operation_bp.route('/switchDeviceStat', methods=['POST'])
async def handle_switchDeviceStat(request):
    deviceSN = request.form.get('deviceSN')
    newstat = request.form.get('newstat')
    print('设备SN is',deviceSN,'新的状态码为',newstat)
    switchDeviceStat(deviceSN,newstat)
    return response.text('success')

@operation_bp.route('/switchUserStat', methods=['POST'])
async def handle_switchDeviceStat(request):
    user_id = request.form.get('user_id')
    newstat = request.form.get('newstat')
    print('设备SN is',user_id,'新的状态码为',newstat)
    switchUserStat(user_id,newstat)
    return response.text('success')

# 接口弃用
# ========== 自动解绑 ============= #
# 每5s检查哪些设备超出有效期
# 若有将设备解绑，同时恢复设备状态
# def judgeExpirytime():
#     # 查看当前未过期的演示设备SN
#     exist_snList = redis_ex.keys()
#     # 查看所有设备SN
#     all_snList = redis_ex.lrange('deviceSN_list',0,-1)
#     # 找出已超出有效期的演示设备
#     expired_snList = set(exist_snList) ^ set(all_snList)
#     # 删除deviceSN_list中已过期的键值, 同时在数据库中解绑
#     for i in expired_snList:
#         redis_ex.lrem('deviceSN_list', i)
#         # 在数据库中解绑设备, 并改变设备的状态
#         mysqlUnbindDevice(i,'A')
#         print('设备:'+i+' 自动解绑成功')
#     timer = threading.Timer(check_time, judgeExpirytime)
#     # print('当前线程数', format(threading.activeCount()))
#     timer.start()