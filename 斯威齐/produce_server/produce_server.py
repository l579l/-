#coding=utf-8
from sanic import response,Blueprint
from produce_server.prod_orm import readProdUser,readProdTime,readProdDeviceSN,switchPrintStat,readProdNoPrint
from mqtt_server.mqtt_server import *
from produce_server.make_qr import make_base64
import qrcode
import asyncio
import json
import base64
import aioredis
import redis
import re
from my_logging.myLogging import myLogging

#redisSub=redisPubSub()
log=myLogging()

prod_client = mqtt_client(MQTT_CLIENTNAME+"produce", MQTT_HOSTNAME, MQTT_PORT)    #实例化生产场景的MQTT客户端, id为"produce"
prod_client.connect(["CPUID",'alarm/'])  #连接并订阅主题"CPUID"
redisClient=redis.Redis(host=REDIS_HOSTNAME,port=REDIS_PORT)
prod_bp=Blueprint("prod_bp")

#===========================测试路由===========================#
@prod_bp.route('/prod_hello')
async def prod_hello(request):
    print("请求prod_bp测试路由")
    return response.text("看到此信息说明prod_bp测试成功")


#===========================登录路由===========================#
@prod_bp.route('/login',methods=['POST'])
async def prod_login(request):
    """
    生产场景登录接口，POST方法，用户名和密码直接写到数据库中，
    无需注册，直接登录即可
    :param request:
    request[username]:用户名
    request[passwd]:登录密码

    :return:
    response["reqStatus"]:登录状态
        userError:用户名错误
        passwdError：密码错误
        success：登录成功
    """
    print("请求login路由")
    username=request.form.get('username')
    passwd=request.form.get('passwd')
    result=readProdUser()
    print("用户名：%s，密码:%s"%(username,passwd))
    print(result)
    if username != result['username']:
        return response.json({"reqStatus":'userError'})
    if passwd != result['passwd']:
        return response.json({"reqStatus":'passwdError'})
    return response.json({"reqStatus":'success'})

#===========================查找路由===========================#
@prod_bp.route('/search',methods=['POST'])
async def prod_search(request):
    """
    生产场景，查找设备接口，
    根据生产时间查找设备，根据deviceSN查找设备
    :param request:
    if request[condition]==time:如果查找条件是时间，则：
        request[startTime]:要查找时间段的开始时间
        request[endTime]:要查找时间段的结束时间
        :return:
        {sn1:cpuid1,sn2:cpuid2,...}

    if request[condition]==DeviceSN:
        request[DeviceSN]:要查找的DeviceSN
        :return:
        {sn:cpuid}
    """
    condition=request.form.get('condition')
    if condition=='Time':
        print("请求查询Time")
        startTime=request.form.get('startTime')
        endTime=request.form.get('endTime')
        print(startTime,' ',endTime)
        #print(str(startTime)+':'+str(startTime))
        result=readProdTime(startTime,endTime)
        print(result)
        return response.json(result)

    if condition=='DeviceSN':
        print("请求查询DeviceSN")
        DeviceSN=request.form.get('DeviceSN')
        print(DeviceSN)
        pattern=re.compile(r'^\d{8}$')
        if pattern.match(DeviceSN):
            result=readProdDeviceSN(DeviceSN)
            if result:
                return response.json({DeviceSN:result})
            else:
                return response.json({'status':'deviceSNNoExist'})
        else:
            return response.json({'status':'deviceSNError'})

#===========================查找没有打印的设备===========================#
@prod_bp.route('/searchNoPrint',methods=['GET'])
async def prod_searchNoPrint(request):
    """
    用户（前端）第一次登录账户请求苦衷所有为未打印标签的设备
    :param request:
    :return:
        {sn1:cpuid1,sn2:cpuid2,...}
    """
    noPrintDeviceSNs=redisClient.smembers('noPrintDeviceSNSet')
    if noPrintDeviceSNs:
        noPrintDeviceSNs=[i[0:8] for i in noPrintDeviceSNs]
        cpuidList=redisClient.hmget('deviceSN:CPUID',noPrintDeviceSNs)
        return response.json(dict(zip(noPrintDeviceSNs,cpuidList)))
    else:
        DeviceSNList=readProdNoPrint()
        pipe=redisClient.pipeline()
        for i,j in DeviceSNList.items():
            pipe.sadd('noPrintDeviceSNSet',i+":1")
            pipe.hset('deviceSN:CPUID',i,j)
        pipe.execute()
    return response.json(DeviceSNList)

#=============================websocket接口===========================#
# websocket接口，用于处理websocket连接，如果有了连接就添加到列表中
# 如果检测不到连接就删除此websocket对象
#=====================================================================#

class webSockets:
    __webSocketsList = []
    __webSocketNum = 0

    def add(self, ws):
        self.__webSocketNum = self.__webSocketNum + 1
        print(ws.remote_address)
        self.__webSocketsList.append(ws)

    #从当前连接中删除某个用户
    def remove(self, ws):
        self.__webSocketNum = self.__webSocketNum - 1
        self.__webSocketsList.remove(ws)

    #打印当前的所有连接
    def print(self, message):
        print(len(self.__webSocketsList))#打印当前websocket连接个数
        for ws in self.__webSocketsList:
            print('用户地址：',ws.remote_address)#打印当前websocket连接IP

    async def send(self,message):
        for ws in self.__webSocketsList:#如果当前用户在线就发送信息
            try:
                await ws.send(message)
            except:
                print("当前websocket连接",ws.remote_address,"不在线，发送有问题")

webSockets = webSockets()

@prod_bp.websocket('/socketNoPrintAuto')
async def prod_searchNoPrint_socket(request,ws):
    print(ws.remote_address,"连接socket")
    i=0
    webSockets.add(ws)
    while str(ws.state) == 'State.OPEN':
        await asyncio.sleep(5)
        data= await ws.recv()
        print("websocket接收内容：",data)
    webSockets.remove(ws)

def produce_websocket_loop(loop):
    asyncio.set_event_loop(loop)
    redisClient = redis.Redis(host=REDIS_HOSTNAME, port=REDIS_PORT)

    async def sendToClient():
        while True:
            noPrintDeviceSNs = redisClient.smembers('noPrintDeviceSNSet')
            sendDevices=[]
            pipe=redisClient.pipeline()
            for i in noPrintDeviceSNs:
                i=i.decode('utf-8')
                if i[-1]=='0':
                    print("状态位为0的设备:",i)
                    sendDevices.append(i[0:8])
                    pipe.sadd('noPrintDeviceSNSet',i[0:8]+":1")
                    pipe.srem('noPrintDeviceSNSet', i)
            pipe.execute()
            await webSockets.send(json.dumps(sendDevices))
            await asyncio.sleep(10)

    async def sendToClient1():
        while True:
            print("生产场景websocket子线程正常运行")
            await asyncio.sleep(10)

    future = asyncio.gather(sendToClient(),sendToClient1())
    loop.run_until_complete(future)


@prod_bp.websocket('/socketNoPrint')
async def prod_searchNoPrint_socket(request,ws):
    print(ws.remote_address,"连接socket")
    i=0
    while True:
        DeviceSNList=readProdNoPrint()
        #print(await redisSub.subMessage().parse_response()[2].decode('utf-8'))
        sendMessage=json.dumps(DeviceSNList)#+str(i)
        print('socketSend:----',sendMessage)
        await ws.send(sendMessage)
        data=await ws.recv()
        print("websocket接收内容：",data)
        await asyncio.sleep(20)
        i=i+1
        print('websocket:',i)

@prod_bp.websocket('/socketNoPrint/V2')
async def prod_searchNoPrint_socket(request,ws):
    print(ws.remote_address,"连接socket")
    redis = await aioredis.create_redis(('localhost', 6379))
    ch = await redis.subscribe('test')
    # while True:
    while await ch[0].wait_message():
        msg = await ch[0].get(encoding='utf-8')
        print(msg)

@prod_bp.websocket('/socketNoPrint/V3')
async def prod_searchNoPrint_socket(request,ws):
    print(ws.remote_address,"连接socket")
    i=0
    while True:
        DeviceSNList=readProdNoPrint()
        sendMessage = {}
        #print(await redisSub.subMessage().parse_response()[2].decode('utf-8'))
        for i in DeviceSNList:
            sendMessage[i] = make_base64(i)
        sendMessage_json = json.dumps()#+str(i)
        print('socketSend:----',sendMessage_json)
        await ws.send(sendMessage_json)
        await asyncio.sleep(20)
        i=i+1
        print('websocket:',i)

@prod_bp.route('/printQRCode',methods=['POST'])
async def prod_printQRCode(request):
    """
    根据设备的SN获取打印二维码
    :param request:
        request[DeviceSNList] : 请求打印设备SN的列表
    :return:
        {SN1:IMG1,SN2,IMG2,...}
    """
    DeviceSNList=request.form.get('DeviceSNList')
    DeviceSNList=eval(DeviceSNList)
    img={}
    for i in DeviceSNList:
        img[i]=await make_base64(i+readProdDeviceSN(i))
        #img[i]=makeQrcode(i,readProdDeviceSN(i))
    return response.json(img)

   
@prod_bp.route('/switchPtintStatus',methods=['POST'])
async def prod_switchPtintStatus(request):
    """
    转换打印状态
    :param request:
    :return:
    """
    DeviceSNList=request.form.get('DeviceSNList')
    DeviceSNList=eval(DeviceSNList)
    print("转换状态：",DeviceSNList)
    if switchPrintStat(DeviceSNList):
        return response.json({'reqStatus':'sucess'})
    return response.json({'reqStatus':'error'})




