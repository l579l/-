import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import time
import tkinter
from tkinter import ttk
import random
import string
from sqlalchemy import create_engine,func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from conf import *
import qrcode
from PIL import Image,ImageTk

engine = create_engine(MYSQL_CONNECT,
                       pool_size=10,max_overflow=3,echo_pool=True)
Session = sessionmaker(bind=engine)  #订制会话
Base =automap_base()
Base.prepare(engine,reflect=True)
qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=3,
        border=4,
    )

#获取最大deviceSN,测试用
def getMaxDeviceSN():
    sess=Session()
    dev = Base.classes.prod_device
    res=sess.query(func.max(dev.deviceSN)).one()
    sess.close()
    return res[0]

def on_connect(client,userdata,rc,_):
    T.insert(tkinter.END,"MQTT client connect success!\n")
    T.see(tkinter.END)

def on_message(client,userdata,msg):
    global DeviceSN
    global HogpenId_list
    ind = client_list.index(client)
    if 'DeviceID' in msg.topic:
        DeviceSN[ind] = (msg.payload.decode("utf-8")[:-1])
        print("[print mode] DeviceSN is: ",DeviceSN[ind])
        client.unsubscribe(TOPIC_sub1[ind])
        # 获取SN后订阅设备别名
        client.subscribe('ComServer/Hogpen/'+msg.payload.decode("utf-8")[:-1])
        print('ComServer/Hogpen/'+msg.payload.decode("utf-8")[:-1])
        i = tree.get_children()[ind]
        if msg.payload.decode("utf-8")[-1] == "1":
            tree.item(i, values=[tree.item(i)["values"][0], DeviceSN[tree.item(i)["values"][0] - 1]], tags=["on"])
        else:
            tree.item(i, values=[tree.item(i)["values"][0], DeviceSN[tree.item(i)["values"][0] - 1]], tags=["error"])
    elif 'ComServer/Hogpen/' in msg.topic:
        HogpenId = msg.payload.decode('utf-8')      #111111112/黄陂/第1舍/第1栏
        HogpenId_list[ind] = HogpenId
        print('订阅的topic is：','Cmd/'+HogpenId[0:HogpenId.rfind('/')]+'/+')
        client.subscribe('Cmd/'+HogpenId[0:HogpenId.rfind('/')]+'/+')
    elif 'Cmd/' in msg.topic:
        msg_payload = json.loads(msg.payload.decode('utf-8'))
        # 服务器对下位机参数设置
        print(msg_payload)
        if msg_payload['CmdCode'] == 1:
            msg_payload.pop('CmdCode')
            publish.single('Setting/'+HogpenId_list[ind],payload=json.dumps(msg_payload),hostname=hostname.get(), port=port.get())

def select(event):
    global select_id
    select_id = tree.selection()
    if len(select_id) == 1:
        row_num = tree.item(select_id)["values"][0]
        deviceSN = DeviceSN[row_num - 1]
        if deviceSN:
            cpuID = CPUID[row_num - 1]
            mess = deviceSN + cpuID
            qr.clear()
            qr.add_data(mess)
            qr.make(fit=True)
            qr_img = qr.make_image()
            qr_img.save(r'qrcode.png')
        else:
            qr_img = Image.new('RGB', (111, 111), (255, 255, 255))
            qr_img.save(r'qrcode.png')
        img_open=Image.open(r'qrcode.png')
        img = ImageTk.PhotoImage(img_open)
        Img.config(image=img)
        Img.image=img

def start():
    global select_id
    for i in select_id:
        row_num = tree.item(i)["values"][0]
        deviceSN = DeviceSN[row_num-1]
        client_list[row_num - 1].subscribe('ComServer/Hogpen/'+deviceSN)
        if deviceSN == '':
            client_list[row_num-1].subscribe(TOPIC_sub1[row_num-1])
            publish.single(TOPIC_pub1, payload=CPUID[row_num-1], hostname=hostname.get(), port=port.get())
            print("[print mode] CPUID publish success!")
        else:
            for i in select_id:
                tree.item(i, values=[tree.item(i)["values"][0], DeviceSN[tree.item(i)["values"][0] - 1]],tags=["on"])
            print("[print mode] DeviceSN is: ",DeviceSN[row_num-1])
    tree.tag_configure("on", background="LawnGreen")
    tree.tag_configure("error", background="Yellow")

def close():
    global select_id
    for i in select_id:
        tree.item(i,tags=["off"])
        tree.item(i, values=[tree.item(i)["values"][0], ""])
    tree.tag_configure("off",background="PaleGoldenrod")

def changeconfig():
    T.insert(tkinter.END,"hostname changes to " + hostname.get() + ", and port changes to " + str(port.get()) + '.\n')
    T.see(tkinter.END)
    # print("hostname changes to " + hostname.get() + ", and port changes to " + str(port.get()) + '.')

def cleartext():
    T.delete(1.0,tkinter.END)

def set_flow():
    read_flow.set("")
    if len(flow.get())==3 and int(flow.get())<=999 and int(flow.get())>=0:
        publish.single("CPUID", payload=flow.get(), hostname=hostname.get(), port=port.get())
        T.insert(tkinter.END,"set flow success\n")
        T.see(tkinter.END)
        flow.set("")
    else:
        T.insert(tkinter.END,"set flow failed, the flow is invalid!\n")
        T.see(tkinter.END)

def get_flow():
    read_flow.set(getMaxDeviceSN()[-3:])

# 激活设备
def activatedevice():
    global select_id
    row_num = tree.item(select_id)["values"][0]
    deviceSN = DeviceSN[row_num - 1]
    publish.single("ComCtrl/activate/" + deviceSN, payload='C0', hostname=hostname.get(), port=port.get())
    print(deviceSN)

def add_device():
    global num
    num += 1
    DeviceSN.append('')
    CPUID.append(''.join(random.sample(string.ascii_letters + string.digits, 16)))
    HogpenId_list.append('0')
    TOPIC_sub1.append("DeviceID/" + CPUID[num])
    client_list.append(mqtt.Client(client_id="feeddevice" + str(num)))
    client_list[num].on_message = on_message
    client_list[num].on_connect = on_connect
    try:
        client_list[num].connect(hostname.get(),port=port.get())
    except:
        T.insert(tkinter.END,"MQTT Broker is not online. Connect later.\n")
        T.see(tkinter.END)
        # print("MQTT Broker is not online. Connect later.")
    tree.insert("","end",values=(num+1,""))
    tree.see(tree.get_children()[-1])
    client_list[num].loop_start()


if __name__ == '__main__':
    app = tkinter.Tk()

    # ======== 初始化参数 ========
    CPUID = []
    TOPIC_sub1 = []
    TOPIC_pub1 = "CPUID"
    DeviceSN = []
    HogpenId_list = []
    num = -1
    client_list = []
    w1_list = []
    select_id = ()
    hostname = tkinter.StringVar()
    port = tkinter.IntVar()
    flow = tkinter.StringVar()
    read_flow = tkinter.StringVar()

    # ======== tkinter布局 ========
    app.title("feeddevice")
    app.geometry("780x580")
    app.resizable(width=False,height=False)
    SNvar = tkinter.StringVar()

    # add device fram
    frm_r = tkinter.Frame(app)
    frm_l = tkinter.Frame(app)
    frm_r_d_l = tkinter.Frame(app)
    frm_r_d_r = tkinter.Frame(app)
    frm_d_l = tkinter.Frame(app)

    # tree
    tree = ttk.Treeview(frm_l,show="headings",height=18,columns=("a","b"))
    vbar = ttk.Scrollbar(frm_l,orient=tkinter.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=vbar.set)
    tree.column("a",width=50)
    tree.column("b",width=150)
    tree.heading("a",text="编号")
    tree.heading("b",text="DeviceSN")
    tree.bind("<<TreeviewSelect>>",select)
    tree.grid(row=0, column=0, columnspan=3, sticky=tkinter.EW)     # 设备显示列表
    vbar.grid(row=0, column=3, sticky=tkinter.NS)                   # 设备列表的滑动条

    # 按钮
    w_add = tkinter.Button(frm_l, text="+", command=add_device,bd=3,relief=tkinter.RAISED)
    w1 = tkinter.Button(frm_l, text="启动",
                        command=start,
                        bg="green",
                        bd=3,
                        relief=tkinter.RAISED,
                        activebackground="lightgreen",
                        width=9,
                        height=1)
    w2 = tkinter.Button(frm_l, text="停止",
                        command=close,
                        bg="red",
                        bd=3,
                        relief=tkinter.RAISED,
                        activebackground="lightcoral",
                        width=9,
                        height=1)
    w3 = tkinter.Button(frm_r,
                        # bitmap='info',
                        text="connect",
                        command=changeconfig,
                        bd=1,
                        # width=35,
                        # height=10,
                        width=7,
                        height=1,
                        compound=tkinter.RIGHT)
    w4 = tkinter.Button(frm_r_d_r,text="clear",command=cleartext)
    w5 = tkinter.Button(frm_r_d_l,text="set_flow",command=set_flow)
    w6 = tkinter.Button(frm_r_d_l,text="get_flow",command=get_flow)
    w7 = tkinter.Button(frm_r,text="激活",command=activatedevice)

    w1.grid(row=1,column=0,sticky=tkinter.E,pady=5)                    # 启动按钮
    w_add.grid(row=1, column=1,sticky=tkinter.N,pady=5)                # 添加按钮
    w2.grid(row=1,column=2,sticky=tkinter.W,pady=5)                    # 停止按钮
    w3.grid(row=0, column=5, sticky=tkinter.NS)                 # 连接MQTT服务按钮
    w4.grid(row=0,column=0,rowspan=2,sticky=tkinter.E)                    # 清空显示框的按钮
    w5.grid(row=0,column=1,sticky=tkinter.NW,padx=10)            # 设置flow按钮
    w6.grid(row=0,column=3,sticky=tkinter.NW,padx=10)            # 获取flow按钮
    w7.grid(row=0,column=0,sticky=tkinter.W)

    # 输入
    L1 = tkinter.Label(frm_r,text="hostname: ")
    L2 = tkinter.Label(frm_r,text="port: ")
    E1 = tkinter.Entry(frm_r,textvariable=hostname,bd=5,width=15)
    hostname.set("39.107.121.203")
    E2 = tkinter.Entry(frm_r,textvariable=port,bd=5,width=10)
    port.set(1883)
    E3 = tkinter.Entry(frm_r_d_l,textvariable=flow,bd=5,width=8)

    L1.grid(row=0,column=1,sticky=tkinter.NS)   # 文本"hostname: "
    L2.grid(row=0,column=3,sticky=tkinter.NS)   # 文本"port: "
    E1.grid(row=0,column=2,sticky=tkinter.N)    # hostname输入框
    E2.grid(row=0,column=4,sticky=tkinter.N)    # port输入框
    E3.grid(row=0,column=0,sticky=tkinter.NW)    # flow输入框,填写下一个flow的值（三位数）

    # 输出
    T = tkinter.Text(frm_r,width=65)
    vbar1 = ttk.Scrollbar(frm_r,orient=tkinter.VERTICAL, command=T.yview)
    T.configure(yscrollcommand=vbar1.set)
    E4 = tkinter.Entry(frm_r_d_l, textvariable=read_flow, bd=5, width=8)

    T.grid(row=1,column=0,columnspan=6,sticky=tkinter.NW,pady=5)    # 显示框
    vbar1.grid(row=1, column=6, sticky=tkinter.NS,pady=5)                  # 显示框滑动条
    E4.grid(row=0, column=2, sticky=tkinter.NW)                      # 获取flow,从数据库获取

    # 图片
    qr_img = Image.new('RGB',(111,111),(255,255,255))
    qr_img.save(r'qrcode.png')
    img_open = Image.open(r'qrcode.png')
    img = ImageTk.PhotoImage(img_open)
    Img = tkinter.Label(frm_d_l,image=img)

    Img.grid(row=0,column=0,padx=10,sticky=tkinter.NW)

    # 布局
    frm_l.grid(row=0,column=0,rowspan=2,padx=10,pady=10,sticky=tkinter.NW)
    frm_r.grid(row=0,column=1,columnspan=2,sticky=tkinter.NW,padx=10,pady=10)
    frm_r_d_l.grid(row=1,column=1,sticky=tkinter.NW,padx=10)
    frm_r_d_r.grid(row=1,column=2,sticky=tkinter.NE,padx=10)
    frm_d_l.grid(row=2,column=0,padx=10,pady=10,sticky=tkinter.NW)

    # 开线程显示GUI界面
    app.mainloop()

