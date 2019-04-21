from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import io
import base64

# 随机字母:
def rndChar():
    i=random.randint(0,2)
    if i==0:
        return chr(random.randint(65, 90))
    if i==1:
        return chr(random.randint(48,57))
    return chr(random.randint(97, 122))

# 随机颜色1:
def rndColor():
    return (random.randint(64, 255), random.randint(64, 255), random.randint(64, 255))

# 随机颜色2:
def rndColor2():
    return (random.randint(32, 127), random.randint(32, 127), random.randint(32, 127))

async def getVerificationCode():
    # 200 x 50:
    VerificationCode=''
    width = 35 * 4
    height = 50
    image = Image.new('RGB', (width, height), (255, 255, 255))
    # 创建Font对象:
    font = ImageFont.truetype('DejaVuSans.ttf', 36)
    # 创建Draw对象:
    draw = ImageDraw.Draw(image)
    # 填充每个像素:
    for x in range(width):
        for y in range(height):
            draw.point((x, y), fill=rndColor())
    # 输出文字:
    for t in range(4):
        VerificationCode=VerificationCode+rndChar()
        draw.text((32 * t + 5, 5), VerificationCode[t], font=font, fill=rndColor2())
    image = image.filter(ImageFilter.BLUR)
    buffer=io.BytesIO()
    image.save(buffer,quality=80,format='jpeg')
    img='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('utf-8')
    return VerificationCode,img

if __name__=='__main__':
    getVerificationCode()