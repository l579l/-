###生产场景服务接口
2018.11.4
1. 登录
生产管理系统登录，默认用户名和密码，开发时提前写入数据库中，日后若需更改需直接更改数据库。服务器收到请求后会先读数据库，因为数据库中只有一个用户名，所以直接将这个用户名和密码读出来即可，读出来后直接和收到的前端请求中的用户名和密码进行比较即可
接口('/login',methods=['POST'])
请求（json）：【默认值暂定'username':'prodsys','passwd':'123'】
{'username':'prodsys','passwd':'123'}
响应（json）：
用户名错误：
{"reqStatus":'userError'}
密码错误：
{"reqStatus":'passwdError'}
用户名和密码都正确
{"reqStatus":'sucess'}
**注：目前是明文传输，明文报名，需修改成密文**
2. 查询
根据不同的条件执行不同的查询功能，条件可设置为时间和DeviceSN
接口('/search',methods=['POST']):
 1. 以时间为条件查询
 查询某时间范围内打印的设备，根据输入的时间范围查询数据库中设备打印信息，无论设备有没有打印，都会检索出来并返回
 请求（json）
 condition：查询条件定为Time
 startTime：要查询时间段的开始时间(日期时间格式的字符串)
 endTime：要查询时间段的终止时间(日期时间格式的字符串)
 {'condition':'Time','startTime':'2018-10-4 11:34:11','endTime':'2018-11-4 11:34:11'}
 响应（json)：
 {{deviceSN1:CPUID1},{deviceSN2:CPUID2}}
 2. 以DeviceSN为条件进行查询
 查询条件为DeviceSN，用户可根据标签或者数码管上显示的DeviceSN查询设备信息，无论设备有没有打印都会检索出来并返回
 请求(json)：
 {'condition':'DeviceSN','DeviceSN':DeviceSN值}
 响应（json）:
 {'CPUID':CPUID值,'DeviceSN':DeviceSN值}
3. 转换打印状态
设备标签打印后，前段通知后端改变设备的打印状态，将打印设备的DeviceSN发送到后端，后端调用数据库接口改变状态即可，如果打印成功的话将设备打印状态转换为1，默认未打印设备的打印状态为0
请求json：
{'DeviceSNList':[DeviceSN1，DeviceSN2]}
响应：
response.json({'reqStatus':'sucess'})
response.json({'reqStatus':'error'})
 **注：如果前端发送的数据是个列表，如果列表中部分修改成功怎么处理【需增加】**
4. 查询数据库中未打印标签的设备
设备接口分两种，一种是由前端主动请求查询数据库中未打印标签的设备，另一种是后端主动向前端发送未打印标签的设备。
 1. 前端请求的接口('/searchNoPrint',methods=['GET'])
 前端get访问此接口就会返回未打印标签的设备列表
 响应json：
 {'DeviceSNList':[DeviceSN1，DeviceSN2]}，如果没有就返回一个空列表
 2. 后端主动向前端发送未打印标签的设备，采用websocket，后端线程以一定的频率查询数据库，有未打印的就返回给前端，如果没有就返回一个空列表
 发送内容：{'DeviceSNList':[DeviceSN1，DeviceSN2]}【将发送的内容封装成字典，然后json再发送】
 ```
 @prod_bp.websocket('/socketNoPrint')
async def prod_searchNoPrint_socket(request,ws):
    print("连接socket")
    i=0
    while True:
        DeviceSNList=readProdNoPrint()
        sendMessage=json.dumps(DeviceSNList)#+str(i)        
        await ws.send(sendMessage)
        await asyncio.sleep(20)
        i=i+1
 ```
 **注：此功能主要使用websocket主动向前端发送，前端主动查询的接口暂时【废弃】**
5. 打印二维码接口【废弃，二维码改为由前端产生】
前端需要打印二维码时，向后端请求二维码数据，将要打印的标签设备的DeviceSN发送到后端，后端生成二维码后响应
请求： {'DeviceSNList':[DeviceSN1，DeviceSN2]}
响应：
{
‘DeviceSN1’:qrcode1,
‘DeviceSN2’:qrcode2,
}
**注：目前是直接向前端发送二维码数据，前端无法解析，需更改成直接向前端响应二维码图片**

2018-11-7
1. 重新编写打印二维码接口
请求{'DeviceSNList':[DeviceSN1，DeviceSN2]}
响应：
{
‘DeviceSN1’:二维码图片的base64编码,
‘DeviceSN2’:二维码图片的base64编码,
}
二维码的内容：SN+‘ ’+CPUID
 
