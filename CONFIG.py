BOT_TOKEN ="telegram-bot-token"
EXPIRATION_DELTA = 3600*24*5 #Время в течении которого держатся записи о действии самоката.

import os
# proxy = 'http://<user>:<pass>@<proxy>:<port>'
proxy = 'put-your-proxy-here'
os.environ['http_proxy'] = proxy
os.environ['HTTP_PROXY'] = proxy
os.environ['https_proxy'] = proxy
os.environ['HTTPS_PROXY'] = proxy
