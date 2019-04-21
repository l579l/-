from PIL import Image,ImageDraw,ImageFont
import qrcode
import io
import base64

backMode = {#背景图属性，我的背景图上需要添加一个二维码和多个文本框
    "back_url":"back.png",
    "size":(142,167),
    "QR":{ #二维码属性
        "frame":(130,130),#大小
        "position":(5,5),#位置
    },
    "text":{#文本框属性
        "size":20,#字号
        "ttf":"DejaVuSans.ttf",#字体
        "color":(0,0,0),#颜色
        "position":(20,138),
        "frame":(200,20),
    },
}

async def make_qr(content,sizeW=0,sizeH=0):
    qr=qrcode.QRCode(version=3,box_size=3,border=1,error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(content)
    qr.make(fit=True)
    img=qr.make_image()
    if sizeW==0 and sizeH==0:
        return img
    img=img.resize((sizeW,sizeH),Image.ANTIALIAS)
    return img

async def makeQrcode(SN,CPUID):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=5,
        border=4,
    )
    qr.clear()
    mess=SN+CPUID
    qr.add_data(mess)
    qr.make(fit=True)
    img=qr.make_image()
    img.save('./produce_server/qrcode/'+mess+'.png')
    with open('./produce_server/qrcode/'+mess+'.png','rb') as f:
        ba=base64.b64encode(f.read())
        return 'data:image/jpeg;base64,'+str(ba.decode('utf-8'))

async def com_pic(topimg,backimg,position):
    nodeA=position
    w,h=topimg.size
    nodeB=(position[0]+w,position[1]+h)
    backimg.paste(topimg,(nodeA[0],nodeA[1],nodeB[0],nodeB[1]))
    return backimg

async def write_text(mode,img,text):
    myfont=ImageFont.truetype(mode['text']['ttf'],size=mode['text']['size'])
    #img=Image.open(mode['back_url'])
    draw=ImageDraw.Draw(img)
    tend=len(text)
    draw.text((mode['text']['position'][0],mode['text']['position'][1]),text[:tend],font=myfont,fill=mode['text']['color'])
    return img

async def make_pic(mode,text):
    #img=Image.open(mode['back_url'])
    img=Image.new('RGB',(mode['size'][0],mode['size'][1]),(255,255,255))
    QR=await make_qr(text,mode['QR']['frame'][0],mode['QR']['frame'][1])
    img=await com_pic(QR,img,mode['QR']['position'])
    img=await write_text(mode,img,text[0:8])
    img.save('a.png',quality=100)

async def make_base64(text,mode=backMode):
    #img=Image.open(mode['back_url'])
    img=Image.new('RGB',(mode['size'][0],mode['size'][1]),(255,255,255))
    QR=await make_qr(text,mode['QR']['frame'][0],mode['QR']['frame'][1])
    img=await com_pic(QR,img,mode['QR']['position'])
    img=await write_text(mode,img,text[0:8])
    buffer=io.BytesIO()
    img.save(buffer,quality=100,format='png')
    return 'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('utf-8')

#print(make_base64("18436012HU1kCjYJ4QEXeqbioNL3GnyA"))