Telegram 验证 bot, 支持使用 Google reCaptcha 或 Cloudflare turnstile.

# usage
准备工作
```bash
git clone git@github.com:tobyprime/VerificationBot.git
cd VerificationBot
pip install -r ./requirements.txt
```
## 以轮询方式运行
```bash
python ./run.py --telegram-token 100000000:XXXXX-1234567890 \
                --turnstile-token 0xAAAAAAA-ABVDEFG \
                --webapp-url https://your.webappurl \
                --proxy http://localhost:7890 \ 
                --test-time 60 \
                --ban true \
                --ban-time 30 
```
- --telegram-token: 你的 tg bot token，通过 https://t.me/BotFather 获取
- --turnstile-token: 你的 Cloudflare turnstile 的 secret token，如果使用，如果希望使用 google reCaptcha 则替换为 --recaptcha-token
- --webapp-url：用于客户端进行验证的网页地址（必须 https 协议通信），完成前端验证时将 response 通过 tg 的 url 返回给客户端，见 https://core.telegram.org/bots/webapps#initializing-mini-apps
- --proxy: 连接 tg 服务器与 response 验证服务器使用的代理
更多参数细节见 `python ./run.py --help` 或 config.py 内注释
## 以 webhook 方式运行
```bash
python ./run.py --telegram-token 100000000:XXXXX-1234567890 \
                --turnstile-token 0xAAAAAAA-ABVDEFG \
                --webapp-url https://your.webappurl \
                --proxy http://localhost:7890 \ 
                --test-time 60 \
                --ban true \
                --ban-time 30 \
                --server-host 0.0.0.0 \
                --server-port 8000 \
                --webhook-path "/webhook"
```
运行 bot 只要额外设置
- --server-host: 绑定到 localhost 则只允许内部访问，一般绑定到 0.0.0.0
- --server-port: 任何有效的端口
- --webhook-path: （可选，默认为`/webhook`）webhook 的路由地址
除此之外，还需要向 telegram 设置 webhook，发送 get 请求：
```
https://api.telegram.org/bot{your_bot_token}/setWebhook?url={your_server_url}/{webhook_path}&allowed_updates=["callback_query","message","chat_member"]
```
- your_bot_token: tg bot token
- your_server_url: 运行bot的服务器地址，必须是 telegram 服务器能访问到的公网地址
- webhook_path: 同 webhook-path 这里为 webhook