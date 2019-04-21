from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA,MD5
from Crypto.Signature import PKCS1_v1_5
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import base64 

#签名输出的是字符串（经过base64转码之后的str）
def RSASign(message):#微信端使用private1.pem签名
    with open('crypto/appPrk.pem','r') as f:
        Prk=f.read()
    private=RSA.importKey(Prk)
    hash_message=SHA.new(message.encode('utf-8'))
    signer=PKCS1_v1_5.new(private)
    message_sign=signer.sign(hash_message)
    # print(message_sign)
    # print(base64.b64encode(message_sign))
    # print(base64.b64encode(message_sign).decode('utf-8'))
    return base64.b64encode(message_sign).decode('utf-8')

#验签时现将str转换成bytes，然后再b64decode
def RSAVerifySign(message,sign):#微信端使用public.pem验签
    with open('crypto/appPuk.pem','r') as f:
        Puk=f.read()
    public_key=RSA.importKey(Puk)
    hash_message=SHA.new(message.encode('utf-8'))
    verifier = PKCS1_v1_5.new(public_key)
    if verifier.verify(hash_message,base64.b64decode(sign.encode('utf-8'))):
        return True
    return False

#AES加密和解密
class prpcrypt():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    # 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
    def encrypt(self, text):
        # 生成随机初始向量IV
        iv = 'wuhanligongdaxue'.encode('utf-8')#Random.new().read(AES.block_size)
        cryptor = AES.new(self.key, self.mode, iv)
        text=text.encode("UTF-8")
        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度.目前AES-128足够用
        length = 16
        count = len(text)

        if (count % length != 0):
            add = length - (count % length)
        else:
            add = 0
        text = text + (b'\00' * add)
        ciphertext = cryptor.encrypt(text)
        return base64.b64encode(ciphertext).decode('utf-8')

    # 解密后，去掉补足的空格用strip() 去掉
    def decrypt(self, text):
        ciphertext=base64.b64decode(text.encode('utf-8'))
        iv = 'wuhanligongdaxue'.encode('utf-8')#ciphertext[0:AES.block_size]
        cryptor = AES.new(self.key, self.mode, iv)
        plain_text = cryptor.decrypt(ciphertext)
        return plain_text.rstrip(b'\00').decode("utf-8")

AESCryp=prpcrypt('WUHANLIGONGDAXUE')

def AESencrypt(messgae):
    return AESCryp.encrypt(messgae)

def AESdecrypt(message):
    return AESCryp.decrypt(message)

#MD5哈希密码，向用户发送的是AES加密后的MD5(密码),此函数返回的是密码哈希值AES加密后的字符串，直接打包到头信息中即可
def md5passwd(passwd):
    h=MD5.new()
    h.update(passwd.encode('utf-8'))
    return h.hexdigest()
    #return AESCryp.encrypt(h.hexdigest())