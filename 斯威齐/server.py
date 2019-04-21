from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sanic import Sanic,response
from sanic_session import Session, InMemorySessionInterface
import json
#===============自定义的函数==============#
from wx_server.wx_server import wx_bp
# from mqtt_server_V0.mqtt_server import *
from produce_server.produce_server import prod_bp,produce_websocket_loop
from purchase_server.purchase_server import purchase_bp
from operation_server.operation_server import operation_bp
from websocket_server.websocket_server import *
from conf import *

app= Sanic()
app.blueprint(wx_bp)#wx端接口
# app.blueprint(mqtt_bp)#mqtt服务
app.blueprint(prod_bp)#生产场景
app.blueprint(purchase_bp)#购买场景
app.blueprint(operation_bp)
app.blueprint(websocket_bp)
session = Session(app,interface=InMemorySessionInterface(expiry=3600,sessioncookie=True))
#sessioncookie=True后端的session会自动过期，会话保持1小时

# ========================== 中间件 ========================== #
# 用于验证用户的登录状态
@app.middleware('request')
async def handle_request(request):
    #print(session.interface.session_store)
    if request.url.split('/')[3] == 'operation' and not request['session'].get('user_id'):
        print('会话超时')
        return response.json({'status': 'timeout'})  # 会话过时, 重定向到登录界面

@app.middleware('response')#用于处理跨域的问题，只要是响应，都会经过此中间件，加上用于跨域的头
async def handle_reponse_wx(request,response):
    # 若不同的客户端登陆同一个账号，删除上一个客户端的会话
    if request.url.split('/')[-2] == 'login':
        session_items = session.interface.session_store.items()     # 此时user_id还未保存至session存储
        user_id = request['session']['user_id']
        session_id = request.cookies['session']
        print('session_id:',session_id,'user_id:',user_id)
        print('session_items',session_items)
        for i in list(session_items):
            if json.loads(i[-1]).get('user_id') == user_id:
                del session.interface.session_store[i[0]]
    response.headers["Access-Control-Allow-Origin"] = '*'
    response.headers["Access-Control-Allow-Methods"] = "POST,GET,OPTIONS"
    response.headers["Access-Control-Expose-Headers"] = "Set-Cookie,token"
    response.headers["Access-Control-Allow-Headers"] = "Set-Cookie,token"
    response.headers["Access-Control-Allow-Credentials"] = "true"

@app.route('/')
async def handle_index(request):
    print(type(request.form))
    print("欢迎进入猪哥靓管理系统")
    return response.text("欢迎进入猪哥靓管理系统")

if __name__=="__main__":
    thread_loop1 = asyncio.new_event_loop()
    t1 = threading.Thread(target=websocket_thread_loop_task, args=(thread_loop1,))
    t1.setDaemon(True)
    t1.start()

    thread_loop2 = asyncio.new_event_loop()
    t2 = threading.Thread(target=produce_websocket_loop, args=(thread_loop2,))
    t2.setDaemon(True)
    t2.start()

    app.run(host=WEB_HOSTNAME,port=WEB_PORT,workers=1)
