from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from Crypto import Random
import base64

def genetateRASKey():
    random_generate=Random.new().read
    rsa=RSA.generate(1024,random_generate)

    private_pem=rsa.exportKey()
    with open('private.pem','wb') as f:
        f.write(private_pem)
    public_pem=rsa.publickey().exportKey()
    with open('public.pem','wb') as f:
        f.write(public_pem)

def RSAencrypt(plaintext):
    with open('public.pem','r') as f:
        key=f.read()
        rsakey=RSA.importKey(key)
        cipher=Cipher_pkcs1_v1_5.new(rsakey)
        ciphertext=base64.b64encode(cipher.encrypt(plaintext.encode('utf-8')))
        #ciphertext=cipher.encrypt(plaintext.encode('utf-8'))
        #print(ciphertext)
        return ciphertext

def RSAdecrypt(ciphertext):#输入参数 b'fQRHCJ4KmkcxGztlVb7...‘
    with open('private1.pem','r') as f:
        key=f.read()
        rsakey=RSA.importKey(key)
        cipher=Cipher_pkcs1_v1_5.new(rsakey)
        plaintext = cipher.decrypt(base64.b64decode(ciphertext),"ERROR")
        #print(plaintext.decode("utf-8"))
        return plaintext.decode("utf-8")


class prpcrypt():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    # 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
    def encrypt(self, text):
        # 生成随机初始向量IV
        iv = Random.new().read(AES.block_size)
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

        # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
        # 所以这里统一把加密后的字符串转化为16进制字符串
        return b2a_hex(iv+ciphertext)

    # 解密后，去掉补足的空格用strip() 去掉
    def decrypt(self, text):
        ciphertext = a2b_hex(text)
        iv = ciphertext[0:AES.block_size]
        ciphertext = ciphertext[AES.block_size:len(ciphertext)]
        cryptor = AES.new(self.key, self.mode, iv)
        plain_text = cryptor.decrypt(ciphertext)
        #print("plain_text",plain_text.rstrip(b'\00').decode("utf-8"))
        return plain_text.rstrip(b'\00').decode("utf-8")


if __name__=="__main__":
    #genetateRASKey()
    #RSAencrypt('申思远')
    # with open("/home/shensy/Code/Pythoncode/bottle/test2/python3/ceshixingneng.txt") as f:
    #     data=f.read()
    AEScrypt=prpcrypt('zxcvbnmasdfghjkl')
    # print(AEScrypt.decrypt(AEScrypt.encrypt(data)))
    # print(RSAdecrypt(RSAencrypt(data)))
    # print(type(RSAencrypt('zxzlwxserver').decode('utf-8')))
    # print(RSAencrypt('zxzlwxserver').decode('utf-8')+'/&/')

    data="Hm5BGoCw+0yiHRCkKyg8zCzmqs/g/4BUe0d+LO0u652aj0mY48CRuRR0aCeER2PEtFCicaeJxL3oXET1VUSozqCIfPAVBs7oIdPBsV28AMAWYJw1e+jKTnRn7c8w1IGQMFDVUdfhoVKUWvSgNmDE6HSoMNo947bWyQwQVyf7DQY=/&/d3deb58529d254ed5da68cc2b949c145abb70051b0bd10e88ae0aff52ecc1ef5346c4b3ea1c6f72c361f6f98729d9b916cb7899ef91a57e8498ddfb3e746bd82ce92b0c66a4ebb5d32cdbb71a7f10bad"
    a=data.split('/&/')[0].encode('utf-8')
    b=data.split('/&/')[1].encode('utf-8')
    print(data)
    print(a)
    print(RSAdecrypt(a))
    print(b)
    print(AEScrypt.decrypt(b))
    print(RSAdecrypt(RSAencrypt('wuhanligogndaxue')))

    #print(RSAdecrypt(b'Hm5BGoCw+0yiHRCkKyg8zCzmqs/g/4BUe0d+LO0u652aj0mY48CRuRR0aCeER2PEtFCicaeJxL3oXET1VUSozqCIfPAVBs7oIdPBsV28AMAWYJw1e+jKTnRn7c8w1IGQMFDVUdfhoVKUWvSgNmDE6HSoMNo947bWyQwQVyf7DQY='))
    #print(AEScrypt.decrypt(AEScrypt.encrypt('shensiyuan')))
    print(AEScrypt.decrypt('d3deb58529d254ed5da68cc2b949c145abb70051b0bd10e88ae0aff52ecc1ef5346c4b3ea1c6f72c361f6f98729d9b916cb7899ef91a57e8498ddfb3e746bd82ce92b0c66a4ebb5d32cdbb71a7f10bad'.encode('utf-8')))
