# 引用

本项目主要基于 [keyword_alert_bot](https://github.com/Hootrix/keyword_alert_bot) 进行的二次开发，请遵循相关协议。感谢 Hootrix。


## 🚀Run

### 1. 配置文件

#### config.yml.default --> config.yml

将 config.yml.default 复制到本地并重命名为 config.yml，然后根据下面申请的 api 进行配置

#### Create Telelgram Account & API

建议使用新Telegram账户[开通api](https://my.telegram.org/apps) 来使用

#### Create BOT 

https://t.me/BotFather  创建机器人


### 2. 🐳Docker

当前目录下配置 config.yml 文件后，使用 docker 一键启动，docker-compose.yaml 文件配置如下：

```yaml
services:
  keyword_alert_bot:
    image: povoma4617/keyword_alert_bot:latest
    container_name: keyword_alert_bot
    volumes:
      - ./config.yml:/app/config.yml
      - ./etc:/app/etc
```

然后

```shell
docker compose run keyword_alert_bot
```
即：

```
$ docker compose run keyword_alert_bot



Please enter the code you received: 12345
Please enter your password: 
Signed in successfully as DEMO; remember to not break the ToS or you will risk an account ban!

#################################################################
##                                                             ##
##                          ● success                          ##
##   🤖️Telegram keyword alert bot (Version: 20240627.f6672cf)  ##
##                                                             ##
#################################################################

```


输入验证码，输入密码，登录成功。之后就直接 `docker compose up -d` ，因为我将 bot session 保存到了 `./etc` 中，这样就不用反复登录；数据库也保存到了 `./etc` 中，避免数据丢失，可以持续化的保存到宿主机中。

之后可以直接根据容器名重启或者停止：

```
$ docker restart keyword_alert_bot
$ docker stop keyword_alert_bot
```

---

# 以下是源项目说明：

## 🤖Telegram keyword alert bot ⏰

Telegram关键字提醒机器人，用于实时监测频道/群组中的关键字消息。

确保普通Telegram账户能够在不需要验证的情况下加入指定群组。

Warning: Demo bot使用过载，建议使用 Docker 镜像自行搭建。


👉  Features：

- [x] 关键字消息订阅：根据设定的关键字和频道实时推送消息提醒
- [x] 支持正则表达式匹配语法
- [x] 支持多频道订阅 & 多关键字订阅
- [x] 支持订阅群组消息
- [x] 支持私有频道ID/邀请链接的消息订阅 

  1. https://t.me/+B8yv7lgd9FI0Y2M1  
  2. https://t.me/joinchat/B8yv7lgd9FI0Y2M1 
  

👉 Todo:

- [x] 私有群组订阅和提醒
- [ ] 私有频道消息提醒完整内容预览
- [ ] 多账号支持
- [ ] 扫描退出无用频道/群组

## 🔍Demo

http://t.me/keyword_alert_bot

<img width="250px" alt="demo" src="https://user-images.githubusercontent.com/10736915/171514829-4186d486-e1f4-4303-b3a9-1cfc1b571668.png" />



## 📘Usage

### 普通关键字匹配

```
/subscribe   免费     https://t.me/tianfutong
/subscribe   优惠券   https://t.me/tianfutong

```

### 正则表达式匹配

使用类似JavaScript正则语法规则，用/包裹正则语句，目前可以使用的匹配模式：i,g

```
# 订阅手机型号关键字：iphone x，排除XR，XS等型号，且忽略大小写
/subscribe   /(iphone\s*x)(?:[^sr]|$)/ig  com9ji,xiaobaiup
/subscribe   /(iphone\s*x)(?:[^sr]|$)/ig  https://t.me/com9ji,https://t.me/xiaobaiup

# xx券
/subscribe  /([\S]{2}券)/g  https://t.me/tianfutong

```



### 2. RUN

运行环境 python3.12+

首次运行需要使用Telegram账户接收数字验证码，并输入密码（Telegram API触发）。

```
$ pipenv install

$ pipenv shell

$ python3 ./main.py
```

## BUG Q&A
 - You have joined too many channels/supergroups (caused by JoinChannelRequest)

 BOT中所有订阅频道的总数超过 500。原因是BOT使用的Telegram演示账户限制导致。建议你自行部署

 ### 2. 查看日志发现个别群组无法接收消息，而软件客户端正常接收

 🤔尝试更新telethon到最新版本或者稳定的1.24.0版本

 ### 3. 订阅群组消息，机器人没任何反应
 https://github.com/Hootrix/keyword_alert_bot/issues/20

 ###  4. ModuleNotFoundError: No module named 'asyncstdlib', No module named '...'

```
$ pipenv  install
```

## BOT HELP

```

目的：根据关键字订阅频道消息

支持多关键字和多频道订阅，使用英文逗号`,`间隔

关键字和频道之间使用空格间隔

主要命令：

/subscribe - 订阅操作： `关键字1,关键字2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe - 取消订阅： `关键字1,关键字2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe_all - 取消所有订阅

/list - 显示所有订阅列表

---

Purpose: Subscribe to channel messages based on keywords

Supports multiple keyword and channel subscriptions, separated by commas.

Separate keywords and channels with a space.

Main commands:

/subscribe - subscribe operation: `keyword1, keyword2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe - unsubscribe: `keyword1, keyword2 https://t.me/tianfutong,https://t.me/xiaobaiup`

/unsubscribe_all - unsubscribe from all subscriptions

/list - display all subscription lists.
```

# License

[LICENSE](./LICENSE)