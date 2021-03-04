import requests

res = requests.get('http://47.110.74.149:9000/')

print(res.text)