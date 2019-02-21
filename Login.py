from sanic import Sanic,response
import pymysql   #导入相应的第三方模块

app = Sanic()

db = pymysql.connect("localhost","root","57955","test") #使用test库作为缓存信息载体
cursor = db.cursor()
cursor.execute("DROP TABLE IF EXISTS Login")
sql = """CREATE TABLE Login (
         User_id INT NOT NULL AUTO_INCREMENT,
         User_name  CHAR(20) NOT NULL,
         User_passwor CHAR(20) NOT NULL,
         PRIMARY KEY(User_id))"""     #MYSQL命令语句 建表
cursor.execute(sql)

@app.route('/login',methods=['GET','POST'])
async def login(request):
    Username = request.form.get('username')
    Password = request.form.get('password')
    if request.method == 'GET':    #注册网页  获取注册信息并存入数据库
        cursor = db.cursor()
        sql1 = "INSERT INTO Login(User_name,User_password)" \
              "VALUES (Username,Password)"
        cursor.execute(sql1)
    if request.method == 'POST':   # 登陆网页  获取输入信息并进行数据判断
        sql2 = "SELECT User_password FROM Login WHELE User_name = 'Username'"
        cursor.execute(sql2)
        User= cursor.fetchone()
        if Username == User[0] and Password == User[1]:
            return response.redirect("登陆成功！")
        else:
            return response.text("帐号或者密码有误！")

db.close()

if __name__ =='__main__':
    app.run(host='0.0.0.0',port='1121',debug=True)
