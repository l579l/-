import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import asyncio
import time
import datetime
from produce_server.prod_orm import *
#from redis_client.redisPubSub import redisPubSub
from my_logging.myLogging import myLogging
import redis

#redisPub=redisPubSub()
log=myLogging()
redisClient=redis.Redis(host=REDIS_HOSTNAME,port=REDIS_PORT)

class mqtt_client():
    def __init__(self, client_id, hostname, port):
        self.client_id = client_id      # 客户端的id
        self.message_pubed = {}         # {31231:{'111111112/黄陂/第1舍/第1栏/trig_num': 5}}
        self.hostname = hostname
        self.port = port
        self.auth = {'username': "WUHANLIGONGDAXUE", 'password': "123123"}
        self.client = mqtt.Client(client_id=client_id)
        self.flow_num = 0   # 记录当天出产设备流水号000~999
        self.date_num = ''  # 记录当天日期18431,表示2018年第43周星期1

    # 向下位机转发设置信息
    def mqtt_pub(self, address, attribute):
        msgs = []
        attribute['CmdCode'] = 1
        # self.message_pubed[pub_time] = {}
        for i in address:
            msgs.append({'topic': 'Cmd/' + i, 'payload': json.dumps(attribute), 'qos': 1, 'retain': 0})
        print('message_pubed',self.message_pubed)
        try:
            publish.multiple(msgs,
                             hostname=self.hostname,
                             port=self.port,
                             auth=self.auth,
                             keepalive=60,
                             client_id="",
                             # will = will,
                             protocol=mqtt.MQTTv311)
        except:
            print('publish failed')

    # 判断设置是否成功
    async def mqtt_set(self, alias, set_info, pub_time, time_limit):
        print('alias',alias)
        print('set_info',set_info)
        # pub_time = time.time()
        self.mqtt_pub(alias, set_info)
        while self.message_pubed[str(pub_time)]:
            # 若时间超过time_limit
            if time.time() - pub_time > time_limit:
                alias = set(i[0:i.rfind('/')] for i in self.message_pubed[str(pub_time)].keys())
                self.message_pubed.pop(str(pub_time))
                return [i.split('/',1)[1] for i in alias]
            await asyncio.sleep(2)
            # time.sleep(5)
        self.message_pubed.pop(str(pub_time))
        return 'success'

    # MQTT客户端连接，并订阅主题
    def connect(self,subtopic):
        def on_connect(client, userdata, rc, _):
            for i in subtopic:
                client.subscribe(i)
            print("MQTT Client: " + self.client_id + " 连接成功")

        def on_publish(client, userdata, mid):
            print('publish success')

        def on_message(client, userdata, msg):
            # 根据CPUID生成deviceSN
            if msg.topic == "CPUID":
                # ======================= 测试用 =============================
                if len(msg.payload.decode("utf-8")) == 3:                   #
                    self.flow_num = int(msg.payload.decode("utf-8"))        #
                    return 0
                # ===========================================================
                CPUID = msg.payload.decode("utf-8")
                # 查询数据库是否有该CPUID或有, 则将其对应的SN转发到下位机, 否则生成新的SN
                CPUID_label = checkcpuID(CPUID)
                if CPUID_label:
                    # 数据库查找对应CPUID的SN, 转发给下位机
                    DeviceSN = readProdCPUID(CPUID)
                    publish.single("DeviceID/" + CPUID, payload=DeviceSN + str(1), hostname=self.hostname, port=self.port, qos=1)
                    print("设备已存在，无需重新生成SN")
                else:
                    # 根据日期生成SN的前5位
                    date_tuple = datetime.datetime.now().isocalendar()
                    date_num = str(date_tuple[0])[-2:] + '{0:0>2}'.format(str(date_tuple[1])) + str(date_tuple[2])
                    # 根据日期流水号生成SN, 若第二天则流水号清0
                    if self.date_num != date_num:
                        self.flow_num = 0
                        self.date_num = date_num
                    DeviceSN = date_num + '{0:0>3}'.format(str(self.flow_num))
                    # 流水号加1
                    self.flow_num += 1
                    # 将CPUID, DeviceSN保存至数据库, 返回结果0 or 1
                    write_label = writeDeviceSN(CPUID, DeviceSN)
                    #redisClient.sadd('noPrintDeviceSNSet',DeviceSN+':0')
                    #redisClient.hset('deviceSN:CPUID', DeviceSN, CPUID)
                    # redisPub.pubMessage(json.dumps({DeviceSN:CPUID}))
                    #-----------------------------
                    # 将生成的DeviceSN和数据库保存的结果转发给对应CPUID的下位机
                    publish.single("DeviceID/"+CPUID, payload=DeviceSN + str(write_label), hostname=self.hostname, port=self.port, qos=1)
                    print("DeviceSN: " + DeviceSN + " is produced by CPUID: " + CPUID)
            # 接收设置信息
            elif 'Setting/' in msg.topic:
                msg_topic = msg.topic.split('/', 1)[-1]
                msg_payload = json.loads(msg.payload.decode('utf-8'))
                print('msg_topic',msg_topic)
                for j in self.message_pubed.copy():
                    for i in msg_payload:
                        if msg_topic + '/' + i  in self.message_pubed[j]:
                            # 若参数修改正确
                            if msg_payload[i] == self.message_pubed[j][msg_topic + '/' + i]:
                                self.message_pubed[j].pop(msg_topic + '/' + i)
                            else:
                                print(msg.topic + '/' + i + ' set error')
            # 接收报警信息
            elif 'Alert/' in msg.topic:
                print(msg.payload)
                r=redis.Redis()
                r.publish('alarm',msg.payload)
            # 接收下位机激活信息
            elif 'ComCtrl/activate/' in msg.topic:
                new_status = msg.payload.decode('utf-8')
                deviceSN = msg.topic.split('/')[-1]
                switchDeviceStat(deviceSN,new_status)
                print('deviceSN:',deviceSN,'new_status',new_status)
                # 数据库保存激活时间
            # 接收下位机累积参数信息
            elif 'Data/' in msg.topic:
                deviceSN = msg.topic.split('/')[-1]
                msg = json.loads(msg.payload.decode('utf-8'))
                print('deviceSN:',deviceSN,'msg',msg)
                # 将信息保存至数据库




        # self.client.username_pw_set("tengxiang", "123123")
        self.client.on_connect = on_connect
        self.client.on_message = on_message

        try:
            self.client.connect(self.hostname, port=self.port, keepalive=60)
            print("Looping....")
        except:
            print("MQTT Broker is not online. Connect later.")
        self.client.loop_start()

    # 取消MQTT客户端的连接
    def disconnect(self):
        def on_disconnect(client, userdata, rc):
            print("mqtt disconnected")
        self.client.on_disconnect = on_disconnect
        self.client.disconnect()

