#coding=utf-8
from sanic import response,Blueprint
import asyncio
import json
import base64
from my_logging.myLogging import myLogging
from VerificationCode.VerificationCode import getVerificationCode
import random
import bcrypt
import jwt
import datetime,time
from purchase_server.purchase_orm import *
# from redis_client.redis_class import *
from purchase_server.sendSMS import sendSMS
import python_jwt as pyjwt, jwcrypto.jwk as jwk
from conf import *



purchase_bp=Blueprint('purchase_bp')
log=myLogging(name="purchase")
# redis = redis_class("127.0.0.1",6379)（弃用）
key = jwk.JWK.generate(kty='oct',size=256)

def getRandomInt(num):
    temp=''
    for i in range(num):
        temp=temp+chr(random.randint(48,57))
    return temp

def getRandomChar(num):
    charList=[' A ',' B ',' C ',' D ',' E ',' F ',' G ',
              ' H ',' J ',' K ',' L ',' M ',' N ',' P ',
              ' Q ',' R ',' S ',' T ',' U ',' V ',' W ',
              ' Y ',' a ',' b ',' c ',' d ',' e ',
              ' f ',' g ',' h ',' i ',' j ',' k ',' m ',
              ' n ',' p ',' q ',' r ',' s ',' t ',' u ',
              ' v ',' w ',' y ',' 2 ',' 3 ',' 4 ',
              ' 5 ',' 6 ',' 7 ',' 8 ',' 9 ']
    temp=''
    for i in range(num):
        temp=temp+chr(random.randint(0,len(charList)))
    return temp

@purchase_bp.route('/purchase_hello')
async def purchase_hello(request):
    log.info("请求purchase_hello")
    log.debug("请求purchase_hello")
    print("请求purchase_hello")
    return response.text("看到此信息说明purchase_bp测试成功")

# ========================================================= #
# ======================= 购买场景 ========================= #
# ========================================================= #

# ================ 填写合同 ==================== #
# -公司名
# -公司地址
# -法人
# -法人的电话号码（可选）
# -合同负责人及其电话
# -公司老板id
# -公司纳税人识别号（唯一标识）
# -设备购买日期及其时限
# -设备购买数量
@purchase_bp.route('/purchase/addContract',methods=['POST'])
async def handle_purchase_addContract(request):
    # 验证会话是否过期
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status': 'timeout'})
    user_id = request['session'].get('user_id')
    # 验证操作人身份权限为P
    if readUserAuth(user_id) == 'P':
        parse_request = dict([(i,j[0]) for (i,j) in request.form.items()])
        status = mysqlAddContractInfo(parse_request)
        if not status:
            print('添加合同失败')
            return response.json({'status':'warn'})
        print('添加合同成功')
        return response.json({'status':'success'})

# ============== 获取合同号 ============== #
# 获取用户下所有合同号
@purchase_bp.route('/purchase/getContractNum',methods=['GET'])
async def handle_purchase_getContractNum(request):
    # 验证会话是否过期
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status': 'timeout'})
    # 验证操作人权限为P
    if readUserAuth(user_id) == 'P':
        res = mysqlGetContractNum()
        print('该用户下的合同号是：',res)
        return response.json({'contractNum':res})

# ============= 查看合同 ============== #
@purchase_bp.route('/purchase/getContract/<contract_num>',methods=['GET'])
async def handle_purchase_getcontract(request,contract_num):
    # 验证会话是否过期
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status': 'timeout'})
    # 验证操作人身份权限为P
    if readUserAuth(user_id) == 'P':
        res = mysqlGetContractInfo(contract_num)
        if res:
            res['status'] = 'success'
            print('合同信息为：',res)
            return response.json(res)
        else:
            print('合同信息为找到')
            return response.json({'status':'warn'})

# ============= 删除合同 ============== #
@purchase_bp.route('/purchase/deleteContract/<contract_num>',methods=['GET'])
async def handle_purchase_deleteContract(request,contract_num):
    # 验证会话是否过期
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status': 'timeout'})
    # 验证操作人身份权限为P
    if readUserAuth(user_id) == 'P':
        status = mysqlDeleteContract(contract_num)
        if not status:
            return response.json({'status':'warn'})
        return response.json({'status':'success'})

# ============== 修改合同 ============== #
@purchase_bp.route('/purchase/modifyContract',methods=['POST'])
async def handle_purchase_modifyContract(request):
    # 验证会话是否过期
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status': 'timeout'})
    # 验证操作人身份权限为P
    if readUserAuth(user_id) == 'P':
        modify_info = request.form.get('modify_info')
        status = mysqlModifyContract(modify_info)
        if not status:
            return response.json({'status':'warn'})
        return response.json({'status':'success'})

# ============= 购买设备 ============== #
@purchase_bp.route('/purchase/purchaseDevice',methods=['POST'])
async def handle_purchase_purchaseDevice(request):
    # 验证会话是否过期
    # user_id = request['session'].get('user_id')
    # if not user_id:
    #     print('会话超时')
    #     return response.json({'status': 'timeout'})
    # # 验证操作人权限
    # if readUserAuth(user_id) != 'P':
    #     print('该用户权限不足')
    #     return response.json({'status':'nopower'})
    deviceSN_list = request.form.get('deviceSN_list').split(',')
    contract_num = request.form.get('contract_num')
    # 验证设备的数量是否和合同一致？
    # 验证购买的设备的状态码是否是未售出状态？
    # 验证完成，保存至数据库
    status = mysqlPurchaseDevice(contract_num,deviceSN_list)
    if not status:
        print('保存数据库出错')
        return response.json({'status':'warn'})
    print('购买设备成功')
    return response.json({'status':'success'})

# ============= 删除设备？ ================ #
##################################################################
# 注册过程：
# 用户点击新用户注册按钮，前段显示注册页面
# 用户输入手机号，然后点击获取验证码，此时访问'/purchase/getSMSCode/<tel>'
# 后端调用API向手机号发送生成的6位随机数，并将随机数写到前段cookie中【暂定】
# 用户收到动态码之后填写表单发送到后端'/purchase/signIn'
# 后端根据表单中的验证码和cookie中的验证码来进行用户身份验证
# 身份验证通过之后前端显示填写用户信息的页面，将用户信息发送到后端
# 或者身份验证不通过（验证码失效，手机号无效之类的）
##################################################################

# 获取短信验证码
@purchase_bp.route('/purchase/getSMSCode/<tel:[0-9]{11}[L,N]+>')
async def handle_SMSCode(request,tel):
    # tel的前11位数字表示手机号，最后一位L表示注册状态，N表示一般状态(登录...)。
    # 注册界面的获取验证码：检查数据库手机号是否存在，
    #                    若存在返回，
    #                    不存在发送短信验证码，并将短信验证码保存在redis中(有效期10分钟)。
    # 其他界面的获取短信验证码：直接发送短信验证码，并将短信验证码保存在redis中
    if tel[-1] == 'L' and mysqlCheckUserName(tel[:-1]):     # L状态下tel已存在, 返回错误
        return response.json({'status':'telhasregisted'})
    if tel[-1] == 'N' and not mysqlCheckUserName(tel[:-1]): # N状态下tel不存在, 返回错误
        return response.json({'status':'telnotexist'})
    SMSCode=getRandomInt(6)
    # print(sendSMS(tel[:-1],SMSCode))
    print('手机号:',tel[:-1],'生成的验证码:',SMSCode)
    res = response.json({'tel': tel[:-1],'SMSCode':SMSCode,'status':'success'})
    # redis.set_value(tel[:-1], SMSCode, 600)
    request['session'][tel[:-1]] = SMSCode
    return res

# 注册
@purchase_bp.route('/purchase/signUp',methods=['GET','POST','OPTIONS'])
async def purchase_signUp(request):
    # 用户填写验证码发送到后端接口
    # 读取用户填写的验证码和session中的验证码进行验证,
    # 验证成功返回给前端，然后前端刷新填写用户信息页面
    user_id = request.form.get('tel')  # 用户的手机号，作为uesr_id【用户的唯一标识】
    cSMSCode = request["session"].get(user_id)
    fSMSCode = request.form.get('SMSCode') #用户填写的验证码
    print('cookiesSMSCode:', cSMSCode, '用户填写SMSCode:', fSMSCode)
    if cSMSCode != fSMSCode: #先验证验证码，验证码错误返回错误
        print("短信验证码填写错误")
        return response.json({'status': 'error'})#验证码正确的话接着往下走
    # 将用户信息写入数据库
    # 用户填写密码，昵称等信息写入数据库【日后用户可使用手机号+密码登录】
    # user_id=request.form.get('tel')#用户的手机号，作为uesr_id【用户的唯一标识】
    del request['session'][user_id]
    passwd = request.form.get('passwd')
    user_name = request.form.get('userName')#用户名【昵称】
    user_auth = request.form.get('userAuth')  # 作为条件由用户选择，可以是单选,选择卖家还是买家
    print('username:',user_name,'userId:',user_id,'passwd:',passwd,'userAuth:',user_auth)
    passwd_hash=bcrypt.hashpw(passwd.encode('utf-8'),bcrypt.gensalt())
    if user_auth == 'M' or user_auth == 'Z':
        status = mysqlWriteUserInfo(name=user_name, passwd=passwd_hash, phone=user_id, auth=user_auth)
        if not status:
            print("注册失败")
            return response.json({'status': 'warn'})
        print("注册成功")
        return response.json({'status': 'success'})

####【接口暂时废弃】
@purchase_bp.route('purchase/signIn/userInfo',methods=['POST'])
async def purchase_signIn_userInfo(request):
    #将用户信息写入数据库
    #用户填写密码，昵称等信息写入数据库【日后用户可使用手机号+密码登录】
    user_id=request.form.get('tel')
    passwd=request.form.get('passwd')
    user_name=request.form.get('userName')
    user_auth=request.form.get('userAuth')#作为条件由用户选择，可以是单选,选择卖家还是买家
    if user_auth=='H':#卖家销售（此账号用于演示）
        user_num=request.form.get('userNum')#填写自己的工号表明自己确实属于卖家
        #将用户信息和权限写入数据库
    else:#如果不是卖家就是买家用户自己注册，此时不需要工号，写数据库时权限默认为空
        pass    #由后续的操作为当前注册账号分配权限
    pass

##################################################################
# 登录过程
# 用户登录页面，进入登录页面自动请求验证码'/getVerificationCode'
# 后端生成验证码，将图片返回给前端，验证码写入cookie中
# 前端填写登录表单【手机号，密码，验证码】发送到后端'/purchase/login'
# 后端判断验证码是否正确，手机号和密码是否正确
# 若正确，生成token写入cookie【或直接返回】，返回验证成功的状态
# 若不正确，返回错误代码
# token：
# token中包含用户id【手机号】和用户权限代码
# 以后需要登录才能进行的操作访问路由时需携带token，后端首先验证token的合法性，然后验证用户权限，
# 若token验证成功则进行相应的操作，如果不成则返回相应的错误代码
##################################################################
# 获取图形验证码
@purchase_bp.route('/getVerificationCode')
async def handle_verificationCode(request):
    #生成验证码图片和验证码，图片发送到前端，验证码写入cookie
    VerificationCode,img=await getVerificationCode()
    print('VerificationCode',VerificationCode)
    res=response.json({'img':img,'VerificationCode':VerificationCode})
    request['session']['VerificationCode'] = VerificationCode
    return res

# 登录
@purchase_bp.route('/purchase/login/<mode:[0,1]+>',methods=['POST'])
async def handle_purchase_login(request,mode):
    # mode0:(密码登录)账号+密码+图形验证码登录
    if mode == '0':
        # token = request.cookies.get('token')
        token = request.headers.get('token')
        # 手动登录（无token登录）, 验证短信验证码, 验证用户名和密码,
        # 若验证成功生成token, 放在响应头中
        if token == None:
            # 先验证图形验证码
            cVerificationCode = request['session'].get('VerificationCode')
            fVerificationCode = request.form.get('VerificationCode')
            if not fVerificationCode:
                print("图形验证码失效")
                return response.json({'status': 'error'})
            print('生成的验证码: ', cVerificationCode, '用户填写的验证码: ', fVerificationCode)
            if cVerificationCode.lower() != fVerificationCode.lower():
                print("图形验证码填写错误")
                return response.json({'status': 'error'})  # 图形验证码填写错误
            # 图形验证码验证成功后，对user_id和passwd验证
            user_id = request.form.get('tel')
            passwd = request.form.get('passwd')
            print('用户名：',user_id,'密码：',passwd)
            #读数据库, 查询对应用户名的密码, 若未查到, 返回登录失败
            passwd_hash = readUserPasswd(user_id)
            # 如果密码存在说明用户名正确
            # 然后验证密码是否正确，只有两个都正确才返回正确，否则返回登录失败【但是用户名或密码错误未知】
            if passwd_hash and bcrypt.checkpw(passwd.encode('utf-8'),passwd_hash.encode('utf-8')):
                # 生成jwt放入响应头中
                # token说明，有效期30天，可在days属性中更改
                ip = request.form.get('ip')
                token = pyjwt.generate_jwt({'userId':user_id,'ip':ip},key,'HS256',datetime.timedelta(seconds=15))
                res=response.json({'status':'success'},headers={'token':token})
                res.headers['token']=token
                request['session']['user_id'] = user_id     # 登录成功后保留会话
                del request['session']['VerificationCode']  # 验证成功删除session中的短图形验证码
                print("登录成功")
                return res
            else:
                print("登录失败")
                return response.json({'status':'loginfailed'})#返回错误，但是不告知是用户名出错还是密码出错【为了安全】
        # 有token登录, 判断token是否过期, 判断token是否正确
        # （token被盗取怎么处理）
        try:
            payload = pyjwt.verify_jwt(token,key,['HS256'])[1]
        except:
            print("身份信息过期")
            return response.json({'status': 'timeout'})     # token过期(loginfailed重新定位到登录界面)
        fip = request.form.get('ip')
        tip = payload.get('ip')
        # 验证ip是否正确，防止token被盗用
        if fip != tip:
            return response.json({'status':'timeout'})
        user_id = payload.get('user_id')                            # token未过期
        if mysqlCheckUserName(user_id):                         # 查数据库是否存在该用户
            print("登录成功")
            request['session']['user_id'] = user_id
            return response.json({'status':'success'})          # 存在，返回登录成功
        else:
            print("登录失败")
            return response.json({'status':'loginfailed'})   # 不存在, 返回登录失败

    # mode1:(免密登录)手机+短信验证码登录
    if mode == '1':
        user_id = request.form.get("tel")
        cSMSCode = request['session'].get(user_id)
        fSMSCode = request.form.get("SMSCode")  # fSMSCode:从提交的表单中获取短信验证码
        print('生成的验证码: ', cSMSCode, '用户填写的验证码: ', fSMSCode)
        if cSMSCode != fSMSCode:   # 如果验证码填写错误, 返回error
            print("验证码填写错误")
            return response.json({'status':'error'})
        request['session']['user_id'] = user_id
        # 登录成功删除session中的短信验证码
        del request['session'][user_id]
        print("登录成功")
        return response.json({'status':'success'})

# 注销
@purchase_bp.route('purchase/logout')
async def handle_purchase_logout(request):
    # 判断会话是否过时
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status': 'timeout'})  # 会话过时, 重定向到登录界面
    # 会话未过时
    request['session'].clear()
    print('注销成功')
    return response.json({'status':'success'})

##################################################################
# 个人信息管理
# - 修改用户名：直接修改
# - 修改密码：旧密码+新密码+重复新密码
# - 修改手机号：
#   1. 旧手机号可用：
#      - 获取旧手机号验证码
#      - 输入新手机号
#      - 获取新手机号验证码
#   2. 旧手机号不可用：
#      注册新的账号，交由猪场的权限管理人员替换账号
# - 修改角色：卖家M(只能操作未售出的设备，只能用于演示) or 买家Z（只能操作售出且所属公司的设备）
# - 忘记密码
##################################################################
# 忘记密码
@purchase_bp.route('/purchase/forgetpasswd',methods = ['POST'])
async def forgetpasswd(request):
    user_id = request.form.get('tel')
    cSMSCode = request['session'].get(user_id)
    fSMSCode = request.form.get("SMSCode")
    print('生成的验证码: ', cSMSCode, '用户填写的验证码: ', fSMSCode)
    if cSMSCode != fSMSCode:
        print('短信验证码填写错误')
        return response.json({'status':'error'})
    # 若短信验证码填写正确，删除会话中的短信验证码，将新密码写入数据库中
    del request['session'][user_id]
    new_passwd = request.form.get('newpasswd')
    new_passwd_hash = bcrypt.hashpw(new_passwd.encode('utf-8'), bcrypt.gensalt())
    status = mysqlModifyUserInfo(user_id, {'password': new_passwd_hash})
    if not status:
        print('保存数据库失败')
        response.json({'status': 'warn'})
    print('新密码设置成功')
    return response.json({'status':'success'})      # 新密码设定成功，重定向到登录界面

# 修改密码
@purchase_bp.route('/purchase/modifypasswd',methods = ['POST'])
async def forgetpasswd(request):
    # 判断会话是否超时
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status':'timeout'})  # 会话过时, 重定向到登录界面
    # 未超时，判断旧密码是否正确
    old_passwd = request.form.get('oldpasswd')
    passwd_hash = readUserPasswd(user_id)
    print('old_passwd',old_passwd)
    print('old_passwd1', old_passwd.encode('utf-8'))
    print('old_passwd2',passwd_hash.encode('utf-8'))
    if not bcrypt.checkpw(old_passwd.encode('utf-8'), passwd_hash.encode('utf-8')):
        print('旧密码填写错误')
        return response.json({'status':'error'})    # 旧密码错误返回error
    # 旧密码正确，在数据库中用新密码替换旧密码
    new_passwd = request.form.get('newpasswd')
    new_passwd_hash = bcrypt.hashpw(new_passwd.encode('utf-8'), bcrypt.gensalt())
    status = mysqlModifyUserInfo(user_id, {'password': new_passwd_hash})
    if not status:
        print('保存数据库失败')
        response.json({'status': 'warn'})
    print('修改密码成功')
    return response.json({'status':'success'})        # 修改密码成功，重定向到登录界面

# 修改用户名
@purchase_bp.route('/purchase/modifyusername',methods=['POST'])
async def modifyusername(request):
    # 判断会话是否超时
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status':'timeout'})
    # 会话未超时，在数据库中用新的用户名替换旧的用户名
    user_name = request.form.get('userName')
    status = mysqlModifyUserInfo(user_id,{'real_name':user_name})
    if not status:
        print('保存数据库失败')
        return response.json({'status':'warn'})
    print('修改用户名成功')
    return response.json({'status':'success'})

# 修改用户身份（买家Z，卖家M）
@purchase_bp.route('/purchase/modifyuserauth',methods=['POST'])
async def modifyuserauth(request):
    # 判断会话是否超时
    user_id = request['session'].get('user_id')
    if not user_id:
        print('会话超时')
        return response.json({'status':'timeout'})
    # 会话未超时，在数据库中用新的auth替换旧的auth
    user_auth = request.form.get('userAuth')
    if user_auth in 'MZ':
        status = mysqlModifyUserInfo(user_id,{'role':user_auth})
        if status:
            print('修改用户名成功')
            return response.json({'status': 'success'})
    print('保存数据库失败')
    return response.json({'status':'warn'})

# 修改手机号
@purchase_bp.route('/purchase/modifyuserid/<step:step[1-3]{1}>',methods=['POST','GET'])
async def modifyuserid(request,step):
    user_id = request['session'].get('user_id')
    if not user_id:
        return response.json({'status': 'timeout'})
    # 第一步获取短信验证码，发送到当前用户手机
    if step == 'step1' and request.method=='GET':
        SMSCode = getRandomInt(6)
        # print(sendSMS(tel[:-1],SMSCode))
        print('手机号:', user_id, '生成的验证码:', SMSCode)
        request['session'][user_id] = SMSCode
        return response.json({'tel': user_id, 'SMSCode': SMSCode, 'status': 'success'})
    # 第二步判断填写的验证码是否正确
    if step == 'step2' and request.method=='POST':
        cSMSCode = request['session'].get(user_id)
        fSMSCode = request.form.get('SMSCode')
        print(fSMSCode)
        if cSMSCode != fSMSCode:
            print('短信验证码填写错误')
            return response.json({'status': 'error'})
        del request['session'][user_id]
        print('短信验证码填写成功')
        return response.json({'status': 'success'})
    # 第三步，验证新的手机号
    if step == 'step3' and request.method=='POST':
        new_userid = request.form.get('tel')
        cSMSCode = request['session'].get(new_userid)
        fSMSCode = request.form.get('SMSCode')
        if cSMSCode != fSMSCode:
            print('短信验证码填写错误')
            return response.json({'status': 'error'})
        # 若验证码正确，删除session中的短信验证码，将新号码保存至数据库，重定向到登录界面
        del request['session'][new_userid]
        status = mysqlModifyUserInfo(user_id, {'phone':new_userid})
        if not status:
            print('保存数据库失败')
            response.json({'status':'warn'})
        print('手机号修改成功')
        return response.json({'status': 'success'})

# =========== 判断合同是否过期 ========== #
# =========== 判断设备是否过期 ========== #
# =========== 卖家注册时的身份如何验证 ============ #

#装饰器，用于更新token，验证token的有效性，如果有效则执行路由功能，并在退出时更新token的有效时间
#如果token无效则直接相应token出错，应该是重定向到登录页面，日后有了登录页面路由更改
#使用装饰器的函数只需返回要响应的字典即可，由装饰器封装成json然后像前段响应
# def updateToken(func):
#     def res(request):
#         token=request.cookies.get('token')
#         try:
#             token=jwt.decode(token,'wuhanligongdaxue',algorithm='HS256')
#             result=func(request)
#             token['exp']=datetime.datetime.utcnow() + datetime.timedelta(seconds=30)
#             result.cookies['token']=jwt.encode(token,'wuhanligongdaxue',algorithm='HS256')
#             return response.json(result)
#         except:
#             return response.json({'status':'tokenFail'})#此处应该是重定向到登录界面
#     return res

# @purchase_bp.route('/bindDeviceSN',methods=['POST'])
# @updateToken
# async def bindDeviceSN(request):
#     token = jwt.decode(token, 'wuhanligongdaxue', algorithm='HS256')
#     userId=token['userId']
#     deviceSN=reeuest.form.get('deviceSN')
#     #auth=
#     print('userID：',userId,'deviceSN:',deviceSN)
#     return {'status':'success'}
