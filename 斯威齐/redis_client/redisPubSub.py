import redis

class redisPubSub:
    def __init__(self, host='127.0.0.1', channel='test'):
        self.__conn = redis.Redis(host=host)
        self.chan_sub = channel
        self.chan_pub = channel

    # 发送消息
    def pubMessage(self, msg):
        self.__conn.publish(self.chan_pub, msg)
        return True

    # 订阅
    async def subMessage(self):
        # 打开收音机
        pub = self.__conn.pubsub()
        # 调频道
        pub.subscribe(self.chan_sub)
        # 准备接收
        pub.parse_response()
        return await pub

