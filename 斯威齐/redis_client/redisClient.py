import redis
import aioredis

class redisClient():
    def __init__(self,hostname,port):
        # self.redis_ex = redis.Redis(host=hostname,port=port,decode_responses=True)
        self.redis_pool = redis.ConnectionPool(host=hostname,port=port,decode_responses=True)
        self.redis_ex = redis.Redis(connection_pool=self.redis_pool)
        self.keys = self.redis_ex.keys()

    def set_value(self,key,value,ex):
        self.redis_ex.set(name=key,value=value,ex=ex)

    def get_value(self,key):
        return self.redis_ex.get(name=key)

    def get_keys(self):
        return self.redis_ex.keys()

    def set_list(self,key,value_list):
        self.redis_ex.rpush(key,value_list)

    def get_list(self,key):
        return self.redis_ex.lrange(key,0,-1)

    def delete_listValue(self,key,value):
        self.redis_ex.lrem(key,value)
