from sanic import response,Blueprint
import time
import asyncio
import threading
import redis
import aioredis
import json
from conf import *


websocket_bp=Blueprint("websocket_bp")
# hostname = MQTT_HOSTNAME
# port = MQTT_PORT
# prod_client = mqtt_client(MQTT_CLIENTNAME+"websocket", hostname, port)    #实例化生产场景的MQTT客户端, id为"produce"
# prod_client.connect(["alarm"])  #连接并订阅主题"CPUID"

#-----------------------------------------------------------#
# websockets字典，有新连接时加入到此列表中，检测到某个连接断开是删除
# 用户名作为键名，当前用户的websokcet连接为值
#-----------------------------------------------------------#
class webSockets:
    __webSocketsList = {}
    __webSocketNum = 0

    #添加新连接，并将当前连接的数量加1
    #params：user-用户名（手机号），ws-当前用户的websokcet连接
    def add(self, user, ws):
        self.__webSocketNum = self.__webSocketNum + 1
        print(ws.remote_address)
        self.__webSocketsList[user] = ws

    #从当前连接中删除某个用户
    def remove(self, user):
        self.__webSocketNum = self.__webSocketNum - 1
        self.__webSocketsList.pop(user)

    #打印当前的所有连接
    def print(self, message):
        print(len(self.__webSocketsList))#打印当前websocket连接个数
        for user, ws in self.__webSocketsList.items():
            print('用户名：',user,'用户地址：',ws.remote_address)#打印当前websocket连接IP
            #await ws.send(message)

    #向某用户发送某信息
    #userList-要给列表中的用户发送信息，列表中的用户可能在线，也可能不在线
    # message-要发送的信息
    async def send(self,userList,message):
        outLineUsers=[]
        for user in userList:#遍历真个用户列表
            if user in self.__webSocketsList.keys():#如果当前用户在线就发送信息
                await self.__webSocketsList[user].send(message)
            else:
                outLineUsers.append(user)#如果当前用户不在线就返回当前用户，告诉调用者这些用户未发送信息
        return outLineUsers


webSockets = webSockets()


@websocket_bp.websocket('/websocket/<user>')
async def websockethello(request, ws, user):
    await ws.send('hello')
    webSockets.add(user, ws)
    webSockets.print('调用print接口')
    while str(ws.state) == 'State.OPEN':
        await asyncio.sleep(5)
    webSockets.remove(user)


@websocket_bp.route('/print')
async def httphello(request):
    webSockets.print('调用print接口')
    return response.text('Hello')


#重新开启一个线程->线程中执行的还是各种协程
def websocket_thread_loop_task(loop):
    asyncio.set_event_loop(loop)

    # ---------------------------------------------------------#
    # 订阅报警
    # ---------------------------------------------------------#
    #阻塞版的redis订阅，程序会阻塞在parse_response处，导致此线程无法执行其他的工作
    #订阅下位机的报警消息，下位报警MQTT收到消息后会在利用redis在alarm的主题上发布报警消息
    #子线程的redis订阅到此消息后会用websocket推送给前端
    async def sub_alarm():
        r = redis.Redis(host=REDIS_HOSTNAME,port=REDIS_PORT)
        p = r.pubsub()
        p.subscribe(['alarm'])#订阅所有主题
        p.parse_response()
        while True:
            message = p.parse_response()
            topic, content = message[1].decode('utf-8'), message[2].decode('utf-8')
            print('发布主题：', topic, '发布内容：', content)
            if topic=='alarm':#如果主题是alarm，报警
                #content中的内容是json字符串{SN:报警的位置}
                #根据报警的SN查找数据库中对此设备有操作权限的用户（ABCD）
                #userList=sqlReadUserofSN(SN)
                print('redis订阅的alarm主题接收到的消息：',message)
                userLlist=['13203708051']#模拟读出来的用户列表
                await webSockets.send(userLlist,json.dumps({topic: content}))

    #协程版的redis订阅
    #无消息发布时，程序执行别的工作，一旦订阅的主题收到了消息，就回来执行相应的动作
    async def sub_alarm_async():
        redis = await aioredis.create_redis(
            (REDIS_HOSTNAME, 6379))  # , loop=loop)
        ch = await redis.subscribe('alarm')
        while await ch[0].wait_message():
            msg = await ch[0].get(encoding='utf-8')
            print('订阅主题：alarm', '发布内容：', msg)
            userLlist = ['13203708051']  # 模拟读出来的用户列表
            await webSockets.send(userLlist, json.dumps({'alarm': msg}))

    #---------------------------------------------------------#
    # 查询合同到期时间并推送给用户
    #---------------------------------------------------------#
    async def checkContractExpire():
        pass


    #编写了两个用于测试子线程执行协程函数的测试函数
    # async def printMessage1():
    #     while True:
    #         await asyncio.sleep(2)
    #         print('子线程协程函数1')
    #
    # async def printMessage2():
    #     while True:
    #         await asyncio.sleep(3)
    #         print('子线程协程函数2')

    #需要注册协程的函数都要写在此位置
    future = asyncio.gather(sub_alarm_async())
    #future = asyncio.gather(printMessage1(), printMessage2())
    loop.run_until_complete(future)


if __name__ == "__main__":
    thread_loop = asyncio.new_event_loop()
    t = threading.Thread(target=websocket_thread_loop_task, args=(thread_loop,))
    # t=threading.Thread(target=sub)
    t.setDaemon(True)
    t.start()
    #app.run(host="0.0.0.0", port=9000, workers=1)


