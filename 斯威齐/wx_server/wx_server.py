from sanic import response,Blueprint
from crypto.crypto import *
from mysql_api.mysql_orm_api import *
import json
import time
import requests
from mqtt_server.mqtt_server import *
import os
from conf import *

wx_bp=Blueprint('wx_bp')
hostname = MQTT_HOSTNAME
port = MQTT_PORT
set_client = mqtt_client(MQTT_CLIENTNAME+"set", hostname, port)
set_client.connect(["get/#"])

#=========================验证时间戳===========================#
# 检查时间的有效性,输入接收到的时间戳，
# 判断接收到的时间戳距离当前的时间的距离，
# 在五分钟内有效(300s)【暂定】
def checkTimestamp(time1):
    nowTime=int(time.time())
    diffTime=nowTime-int(time1)
    if diffTime<1000:#如果时间不超过300s，则认为时间有效，返回True，否则返回False
        return True
    return False

#=========================验签===========================#
# 检查数字签名的有效性，
# 输入需要签名的内容和签名，
# 正确返回ture，错误返回false
def checkSignature(message,sign):
    if RSAVerifySign(message,sign):
        return True
    return False

#=========================验证权限==========================#
#验证权限，输入userID和位置别名，根据userID读取数据库，根据数据库中保存的位置
#和输入的位置做对比，如果匹配，则认为有权限设置
#数据库中保存的用户可操作设备格式（如某人可操作黄陂第一栋的全部和第二栋的前三舍）：
#黄陂/第一栋；黄陂/第二栋/第一舍,第二舍,第三舍
def checkUserPrivilege(userID,alias):
    return True

#=========================验证键名字段==========================#
#验证键名是否合法
def checkKeys(keys_name,route):
    wxset_key=['vacant_time','cali_quan','wat_fer_rate','trig_num','trig_inter',
                'pow_par','weight_per_circ','feed_num','aver_age','feed_line_ctrl']
    wxgetHistory_key=['equi_acc_mat','equi_acc_wat']
    key=list(keys_name)
    if route=='/wxset':
        for i in key:
            if i not in wxset_key:
                return False
        return True
    if route=='/wxgetHistory':
        for i in key:
            if i not in wxgetHistory_key:
                return False
        return True

#===========================测试路由===========================#
@wx_bp.route('/wx_hello')
async def hello(resquest):
    print("请求wx_bp测试路由")
    return response.text("看到此信息说明wx_bp测试成功")

#===========================中间件===========================#
# 用于处理接收的请求中的通用内容
# 时间戳、验签、验证权限
# 每个路由都需要经过中间件来进行处理，
@wx_bp.middleware('request')
async def handle_request_post_wxset(request):
    route_name=['/wxset','/wxgetHistory','wxgetCurrent']
    if request.url[request.url.rfind('/'):] in route_name:
        print("中间件处理wxset")
        sendtime=request.headers.get('Timestamp')#读取时间戳
        if checkTimestamp(AESdecrypt(sendtime)):#验证时间戳,如果时间有效继续执行
            zxdata=request.form.get('zxdata')#读取信息zxdata
            zxdata=AESdecrypt(zxdata)#解密字符串，得到的是json字符串
            sendSignature=AESdecrypt(request.headers.get('Signature'))#读取数字签名
            if checkSignature(zxdata,sendSignature):#验签，如果对继续执行
                zxdata=json.loads(zxdata)
                userID=AESdecrypt(request.headers.get('UserID'))
                alias=zxdata['alias']
                if checkUserPrivilege(userID,alias):#权限暂时默认都为正确()
                    pass
                    print('中间件成功处理zxdata')
                else:
                    return response.json({'zxcode':'zx006'})
            else:#验签失败，返回zx001
                return response.json({'zxcode':'zx001'})
        else:#如果时间无效，返回zx001
            return response.json({'zxcode':'zx002'})


@wx_bp.route('/wxset',methods=["POST"])
async def handle_wxset(request):
    print("请求设置参数")
    zxdata=json.loads(AESdecrypt(request.form.get('zxdata')))
    if checkKeys(zxdata['set'].keys(),'/wxset'):
        if(len(zxdata['alias'])==1 and zxdata['alias'][0][-1] == '/'):
            alias=sql_readAliasMessage(zxdata['alias'][0])
        else:
            alias=zxdata['alias']
        set_info=zxdata['set']
        #print("异步开始")
        print(set_info)
        mqtt_status = await set_client.mqtt_set(alias,set_info,time_limit=15)#await
        if 'success'== mqtt_status:
            print("设置成功")
            sql_writeSetMessage(alias,set_info,AESdecrypt(request.headers.get('UserID')),
                                AESdecrypt(request.headers.get('Timestamp')))
            print('写入数据库成功')
            return response.json({'zxcode':'zx000'})
        else:
            print("设置失败",mqtt_status) #mqtt_status:list
            alias_success = set(alias)-set(mqtt_status)
            sql_writeSetMessage(alias_success,set_info,AESdecrypt(request.headers.get('UserID')),
                                AESdecrypt(request.headers.get('Timestamp')))
            return response.json({'zxcode':'zx000'})
    else:
        return response.json({'zxcode':'zx004'})


@wx_bp.route('/wxgetHistory',methods=["POST"])
async def wxgetHistory(request):
    zxdata=json.loads(AESdecrypt(request.form.get('zxdata')))
    if checkKeys(zxdata['request_keys'],'/wxgetHistory'):
        data=sql_readHistoryMessage([zxdata['alias'],zxdata['during'],zxdata['request_keys']])
        return response.json({'zxcode':AESencrypt(json.dumps(data))})
    else:
        return response.json({'zxcode':'zx004'})


@wx_bp.route('/wxgetCurrent',methods=["POST"])
async def wxgetCurrent(request):
    zxdata=json.loads(AESdecrypt(request.form.get('zxdata')))
    wxgetCurrent_keys=['online_stat','act_stat','pow_par','set_run','feed_num',\
                        'aver_age','vacant_time','trig_inter','trig_num',"cali_quan",\
                        'wat_fer_rate','weight_per_circ']
    data=sql_readCurrentStatus([zxdata['alias'],wxgetCurrent_keys])
    return response.json({'zxcode':AESencrypt(json.dumps(data))})

    