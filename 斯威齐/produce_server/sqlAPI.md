###生产场景数据库接口
1. 登录
数据库中预先写好用户名(prodsys)和密码（123,暂时写明文，稍后再统一改成密文）
每次进路由读取数据库返回用户名和密码：
接口：
result=readProdUser()
返回值(dict)：
result['username']
result['passwd']
2. 读数据库中的CPUID【接口暂时废弃，因为用户是看不到CPUID的，所以无法使用CPUID来查询设备信息】
用于查询数据库中的CPUID
result=readProdCPUID(cpuID)
输入(string)：
cpuID
输出(string)：
deviceSN
3. 读数据库中的DeviceSN，返回CPUID
根据设备的DeviceSN查询设备的CPUID
result=readProdDeviceSN(deviceSN)
输入(string)：
DeviceSN
输出(string)：
CPUID
4. 根据时间条件查询数据中的设备信息
result=readProdTime(startTime,endTime)
输入（datatime，如‘2018-11-4 10:36：59’）：
startTime：要查询的开始时间
endTime：要查询的结束时间
输出（dict）:
{{deviceSN1:CPUID1},{deviceSN2:CPUID2}}
5. 查询数据库中未打印标签的设备
result=readProdNoPrint()
输入：无输入
输出(dict)：
{{deviceSN1:CPUID1},{deviceSN2:CPUID2}}
6. 转换数据库中设备的打印状态
result=switchPrintStat(deviceSNList)
输入(list)：
[deviceSN1,deveceSN2]
输出(bool)：
true or false
7. 查询数据库中是否有此CPUID
result=checkcpuID(CPUID)
输入（string）：
cpuID
输出(bool)：
true or false
8. 将设备的CPUID和生成的DeviceSN写到数据库中
result=writeDeviceSN(cpuID,deviceSN)
输入（string，string）：
cpuID,deviceSN
输出(int)：
0 or 1【注意此处不是true or false】
9.转换设备状态
result=switchDeviceStat(cpuID,status)
输入（string,char)
cpuID
status:要转换的状态，A，B，C
输出(bool)：
true or false