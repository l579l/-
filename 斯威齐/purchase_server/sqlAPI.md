###购买场景数据库API
1. 注册
    ```result=mysqlWriteUserInfo(name=user_name,passwd=passwd_hash,id=user_id,auth=user_auth,num=user_num)```  
    num是可选字段
    注册分为两个部分，买家注册和买家注册
    1. 买家注册：
    
        输入：
            
            userid:string,电话
            passwd：string,密码的密文（bcrypt加密）
            userName:string,昵称【一般要求是用户名】
            userAuth：string,用户权限代码
        输出：
        
            True or False  
        调用：  
        ```status=mysqlWriteUserInfo(name=user_name,passwd=passwd_hash,id=user_id,auth=user_auth,num=user_num)```
    2. 卖家注册  
        输入：
        
            userid:string,电话
            passwd：string，密码的密文（bcrypt加密）
            userName:string，昵称【一般要求是用户名】
            userAuth：char，用户权限模型
            userNUm：string，卖家的工号用于标识卖家身份
        输出：
        
            True or False  
        调用：  
        ```        status=mysqlWriteUserInfo(name=user_name, passwd=passwd_hash, phone=user_id, auth='Z')```
    
    说明：  
    **加密算法自带加盐功能，所以暂时不向数据库中添加盐字段**  
    权限模型代码：  
    + A-猪场老板：合同中的用户，可添加BCD权限，管理BCD人员，管理猪场，管理设备
    + B-副总：可添加CD权限,管理CD人员，管理舍，管理设备
    + C-中层管理：管理设备
    + D-饲养员:使用设备
	+ G-猪场老板只读
    + M-卖家销售：可绑定未售出的设备进行演示
    + P-卖家管理合同的权限
    + S-超级管理员：开发人员，此账号扫描设备可以显示出一些内部参数【其他功能待定】
    + Z-空权限代码：用户最初注册时为此权限，上一级高权限为用户分配权限后用户的权限代码会变成对应的权限代码
    
2. 检查用户名是否重复  
    ```python
    status=mysqlCheckUserName(userName)
    ```
    输出  
    ```True or False```   
    如果用户名重复则返回false，如果无重复则返回true  
       
3. 登录    
    1. 根据userID查询用户的密码  
    输入：userID  
    输出：密码密文（如果用户名不存在则返回False）
    ```
    result=readUserPasswd(userID)
    ```
4. 查询用户权限代码  
    输入：userID  
    输出：权限代码  
    ```
    result=readUserAuth(userID)
    ```
5. 查询设备状态码  
    输入：deviceSN
    输出：设备状态码
    ```
    result=readDeviceStatus(deviceSN)
    ```
