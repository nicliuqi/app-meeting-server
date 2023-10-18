from Crypto.Cipher import AES
import base64
import os

encoding_utf8 = 'utf-8'

def aes_gcm_encrypt(plaintext, secret):
    secret_key = base64.b64decode(secret)
    iv = os.urandom(12)
    aes_cipher = AES.new(secret_key, AES.MODE_GCM, iv)
    ciphertext, auth_tag = aes_cipher.encrypt_and_digest(plaintext.encode(encoding_utf8))
    result = iv + ciphertext + auth_tag
    return base64.b64encode(result).decode(encoding_utf8)


def aes_gcm_decrypt(encrypted, secret_key):
    res_bytes = base64.b64decode(encrypted.encode(encoding_utf8))
    nonce = res_bytes[:12]
    ciphertext = res_bytes[12:-16]
    auth_tag = res_bytes[-16:]
    aes_cipher = AES.new(base64.b64decode(secret_key), AES.MODE_GCM, nonce)
    return aes_cipher.decrypt_and_verify(ciphertext, auth_tag).decode(encoding_utf8)