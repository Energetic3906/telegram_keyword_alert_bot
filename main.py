#coding=utf-8
from telethon import TelegramClient, events, sync, errors
from db import utils
import socks,os,datetime
import re as regex
import diskcache
from urllib.parse import urlparse
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.channels import DeleteHistoryRequest
from telethon.tl.functions.channels import LeaveChannelRequest, DeleteChannelRequest
from logger import logger
from config import config,_current_path as current_path
from telethon import utils as telethon_utils
from telethon.tl.types import PeerChannel


PRODUCTION = False # 是否为生产环境（无代理配置）

# 配置访问tg服务器的代理
proxy = None
if all(config['proxy'].values()): # 同时不为None
  logger.info(f'proxy info:{config["proxy"]}')
  proxy = (getattr(socks,config['proxy']['type']), config['proxy']['address'], config['proxy']['port'])
# proxy = (socks.SOCKS5, '127.0.0.1', 1088)
else:
  PRODUCTION = True # 生产环境会退出无用的频道/群组


account = config['account']
cache = diskcache.Cache(current_path+'/.tmp')# 设置缓存文件目录  当前tmp文件夹。用于缓存分步执行命令的操作，避免bot无法找到当前输入操作的进度
client = TelegramClient('{}/.{}_tg_login'.format(current_path,account['username']), account['api_id'], account['api_hash'], proxy = proxy)
client.start(phone=account['phone'])
# client.start()

# 设置bot，且直接启动
bot = TelegramClient('.{}'.format(account['bot_name']), account['api_id'], account['api_hash'],proxy = proxy).start(bot_token=account['bot_token'])

def js_to_py_re(rx):
  '''
  解析js的正则字符串到python中使用
  只支持ig两个匹配模式
  '''
  query, params = rx[1:].rsplit('/', 1)
  if 'g' in params:
      obj = regex.findall
  else:
      obj = regex.search

  # May need to make flags= smarter, but just an example...    
  return lambda L: obj(query, L, flags=regex.I if 'i' in params else 0)

def is_regex_str(string):
  return regex.search(r'^/.*/[a-zA-Z]*?$',string)

# client相关操作 目的：读取消息
# @client.on(events.MessageEdited)
@client.on(events.NewMessage())
async def on_greeting(event):
    '''Greets someone'''
    # telethon.events.newmessage.NewMessage.Event
    # telethon.events.messageedited.MessageEdited.Event
    # isinstance(event,events.NewMessage.Event)
    # if not event.is_group:# channel 类型
    if True:# 所有消息类型，支持群组
      message = event.message

      text = message.text
      if message.file and message.file.name:
        # text += ' file:{}'.format(message.file.name)# 追加上文件名
        text += ' {}'.format(message.file.name)# 追加上文件名

      # 打印消息
      logger.debug(f'event.chat.username: {event.chat.username},event.chat.id:{event.chat.id},event.chat.title:{event.chat.title},event.message.id:{event.message.id},text:{text}')

      # 1.方法(失败)：转发消息 
      # chat = 'keyword_alert_bot' #能转发 但是不能真对特定用户。只能转发给当前允许账户的bot
      # from_chat = 'tianfutong'
      # chat = 349506543# 无法使用chat_id直接转发 没有任何反应
      # chat = 1354871670
      # await message.forward_to('keyword_alert_bot')
      # await client.forward_messages(chat, message)
      # await bot.forward_messages(chat, message)
      # await client.forward_messages(chat, message.id, from_chat)

      # 2.方法：直接发送新消息,非转发.但是可以url预览达到效果

      # 查找当前频道的所有订阅
      sql = """
      select u.chat_id,l.keywords,l.id,l.chat_id
from user_subscribe_list as l  
INNER JOIN user as u on u.id = l.user_id 
where (l.channel_name = ? or l.chat_id = ?)  and l.status = 0  order by l.create_time  desc
      """
      find = utils.db.connect.execute_sql(sql,(event.chat.username,str(event.chat_id))).fetchall()
      if find:
        logger.info(f'channel: {event.chat.username}; all chat_id & keywords:{find}') # 打印当前频道，订阅的用户以及关键字
        for receiver,keywords,l_id,l_chat_id in find:
          try:
            if not l_chat_id:# 未记录频道id
              # 记录频道id
              re_update = utils.db.user_subscribe_list.update(chat_id = str(event.chat_id) ).where(utils.User_subscribe_list.id == l_id)
              re_update.execute()
            
            chat_title = event.chat.username or event.chat.title
            if is_regex_str(keywords):# 输入的为正则字符串
              regex_match = js_to_py_re(keywords)(text)# 进行正则匹配 只支持ig两个flag
              if isinstance(regex_match,regex.Match):#search()结果
                regex_match = [regex_match.group()]
              regex_match_str = []# 显示内容
              for _ in regex_match:
                item = ''.join(_) if isinstance(_,tuple) else _
                if item:
                  regex_match_str.append(item) # 合并处理掉空格
              regex_match_str = list(set(regex_match_str))# 处理重复元素
              if regex_match_str:# 默认 findall()结果
                message_str = f'# {chat_title} \n\n[#FOUND]({get_channel_url(event)}{message.id}) **{regex_match_str}**'
                logger.info(f'REGEX: receiver chat_id:{receiver}, message_str:{message_str}')
                await bot.send_message(receiver, message_str,link_preview = True,parse_mode = 'markdown')
              else:
                logger.debug(f'regex_match empty. regex:{keywords} ,message: t.me/{event.chat.username}/{event.message.id}')
            else:#普通模式
              if keywords in text:
                message_str = f'# {chat_title} \n\n**[#{keywords}]({get_channel_url(event)}{message.id})**'
                logger.info(f'TEXT: receiver chat_id:{receiver}, message_str:{message_str}')
                await bot.send_message(receiver, message_str,link_preview = True,parse_mode = 'markdown')
          except errors.rpcerrorlist.UserIsBlockedError  as _e:
            # User is blocked (caused by SendMessageRequest)  用户已手动停止bot
            logger.error(f'{_e}')
            pass # 关闭全部订阅
          except ValueError  as _e:
            # 用户从未使用bot
            logger.error(f'{_e}')
            # 删除用户订阅和id
            isdel = utils.db.user.delete().where(utils.User.chat_id == receiver).execute()
            user_id = utils.db.user.get_or_none(chat_id=receiver)
            if user_id:
              isdel2 = utils.db.user_subscribe_list.delete().where(utils.User_subscribe_list.user_id == user_id.id).execute()
          except Exception as _e:
            logger.error(f'{_e}')
      else:
        logger.debug(f'sql find empty. event.chat.username:{event.chat.username}, find:{find}, sql:{sql}')

        # 暂停频道退出操作
        # if PRODUCTION:
        #   logger.info(f'Leave  Channel/group: {event.chat.username}')
        #   await leave_channel(event.chat.username)


# bot相关操作
def parse_url(url):
  """
  解析url信息 
  根据urllib.parse操作 避免它将分号设置为参数的分割符以出现params的问题
  Args:
      url ([type]): [string]
  
  Returns:
      [dict]: [按照个人认为的字段区域名称]  <scheme>://<host>/<uri>?<query>#<fragment>
  """
  res = urlparse(url) # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
  result = {}
  result['scheme'],result['host'],result['uri'],result['_params'],result['query'],result['fragment'] = list(res)
  if result['_params'] or ';?' in url:
    result['uri'] += ';'+result['_params']
    del result['_params']
  return result

def get_channel_url(event):
  '''
  获取频道/群组 url

  https://docs.telethon.dev/en/latest/concepts/chats-vs-channels.html#converting-ids

  Args:
      event ([type]): [description]
  '''

  # 判断私有频道（event.is_private 无法判断）
  is_private = True if not event.chat.username else False
  host = 'https://t.me/' + ('c/' if is_private else '')
  real_id, peer_type = telethon_utils.resolve_id(int(event.chat_id))
  return f'''{host}{real_id}/'''


def parse_full_command(command, keywords, channels):
  """
处理多字段的命令参数  拼接合并返回
  Args:
      command ([type]): [命令 如 subscribe  unsubscribe]
      keywords ([type]): [description]
      channels ([type]): [description]

  Returns:
      [type]: [description]
  """
  keywords_list = keywords.split(',')
  channels_list = channels.split(',')
  res = []
  for keyword in keywords_list:
    keyword = keyword.strip()
    for channel in channels_list:
      channel = channel.strip()
      channel = parse_url(channel)['uri'].replace('/','') # 支持传入url  类似 https://t.me/xiaobaiup
      res.append((keyword,channel))
  return res

async def join_channel_insert_subscribe(user_id,keyword_channel_list):
  """
  加入频道 且 写入订阅数据表

  支持传入频道id

  Raises:
      events.StopPropagation: [description]
  """
  res = []
  # 加入频道
  for k,c in keyword_channel_list:
    username = c
    try:
      if c.lstrip('-').isdigit():# 整数
        real_id, peer_type = telethon_utils.resolve_id(int(c))
        c = await client.get_entity(real_id)
        # c.title
        username = ''

      await client(JoinChannelRequest(c))
      res.append((k,username))
    except Exception as _e: # 不存在的频道
      return '无法使用该频道：{}\n\nChannel error, unable to use'.format(c)
    
  # 写入数据表
  result = []
  for keyword,channel_name in res:
    
    if isinstance(channel_name,str):
      chat_id = ''
    else:# chat entity
      chat_id = telethon_utils.get_peer_id(PeerChannel(channel_name.id)) #转换为makerid存入
      channel_name = ''

    find = utils.db.user_subscribe_list.get_or_none(**{
        'user_id':user_id,
        'keywords':keyword,
        'channel_name':channel_name,
        'chat_id':chat_id,
      })

    if find:
      re_update = utils.db.user_subscribe_list.update(status = 0 ).where(utils.User_subscribe_list.id == find.id)#更新状态
      re_update = re_update.execute()# 更新成功返回1，不管是否重复执行
      if re_update:
        result.append((keyword,channel_name))
    else:
      insert_res = utils.db.user_subscribe_list.create(**{
        'user_id':user_id,
        'keywords':keyword,
        'channel_name':channel_name.replace('@',''),
        'create_time':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'chat_id':chat_id
      })
      if insert_res:
        result.append((keyword,channel_name))
  return result

async def leave_channel(channel_name):
  '''
  退出无用的频道/组

  Args:
      channel_name ([type]): [description]
  '''
  try:
      await client(LeaveChannelRequest(channel_name))
      await client(DeleteChannelRequest(channel_name))
      await client(DeleteHistoryRequest(channel_name))
      logger.info(f'退出 {channel_name}')
  except Exception as _e: # 不存在的频道
      return f'无法退出该频道：{channel_name}, {_e}'
      

def update_subscribe(user_id,keyword_channel_list):
  """
  更新订阅数据表（取消订阅操作）
  """
  # 修改数据表
  result = []
  for keyword,channel_name in keyword_channel_list:
    find = utils.db.user_subscribe_list.get_or_none(**{
      'user_id':user_id,
      'keywords':keyword,
      'channel_name':channel_name,
    })
    if find:
      re_update = utils.db.user_subscribe_list.update(status = 1 ).where(utils.User_subscribe_list.id == find)#更新状态
      re_update = re_update.execute()# 更新成功返回1，不管是否重复执行
      if re_update:
        result.append((keyword,channel_name))
    else:
      result.append((keyword,channel_name))
  return result

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
  """Send a message when the command /start is issued."""
  # insert chat_id
  chat_id = event.message.chat.id
  find = utils.db.user.get_or_none(chat_id=chat_id)
  if not find:
    insert_res = utils.db.user.create(**{
      'chat_id':chat_id,
      'create_time':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
  else: # 存在chat_id
    insert_res = True

  if insert_res:
    await event.respond('Hi! Please input /help , access usage.')
  else:
    await event.respond('Opps! Please try again /start ')
  
  raise events.StopPropagation

@bot.on(events.NewMessage(pattern='/subscribe'))
async def subscribe(event):
  """Send a message when the command /subscribe is issued."""
  # insert chat_id
  chat_id = event.message.chat.id
  find = utils.db.user.get_or_none(chat_id=chat_id)
  user_id = find
  if not find:# 不存在用户信息
    await event.respond('Failed. Please input /start')
    raise events.StopPropagation
  
  text = event.message.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"
  splitd = [i for i in regex.split('\s+',text) if i]# 删除空元素
  if len(splitd) <= 1:
    await event.respond('输入需要订阅的关键字,支持js正则语法：`/[\s\S]*/ig`\n\nInput the keyword that needs to subscribe, support JS regular syntax：`/[\s\S]*/ig`')
    cache.set('status_{}'.format(chat_id),{'current_status':'/subscribe keywords','record_value':text},expire=5*60)#设置5m后过期
  elif len(splitd)  == 3:
    command, keywords, channels = splitd
    result = await join_channel_insert_subscribe(user_id,parse_full_command(command, keywords, channels))
    if isinstance(result,str): 
        logger.error('join_channel_insert_subscribe 错误：'+result)
        await event.respond(result,parse_mode = None) # 提示错误消息
    else:
      msg = ''
      for key,channel in result:
        msg += 'keyword:{}  channel:{}\n'.format(key,channel)
      if msg:
        await event.respond('success subscribe:\n'+msg,parse_mode = None)
  raise events.StopPropagation


@bot.on(events.NewMessage(pattern='/unsubscribe_all'))
async def unsubscribe_all(event):
  """Send a message when the command /unsubscribe_all is issued."""
  # insert chat_id
  chat_id = event.message.chat.id
  find = utils.db.user.get_or_none(chat_id=chat_id)
  if not find:# 不存在用户信息
    await event.respond('Failed. Please input /start')
    raise events.StopPropagation
  user_id = find.id
  
  # 查找当前的订阅数据
  _user_subscribe_list = utils.db.connect.execute_sql('select keywords,channel_name,chat_id from user_subscribe_list where user_id = %d and status  = %d' % (user_id,0) ).fetchall()
  if _user_subscribe_list:
    msg = ''
    for keywords,channel_name,chat_id in _user_subscribe_list:
      if not channel_name:
        chat_id,_ = telethon_utils.resolve_id(int(chat_id))
        channel_name = f'c/{chat_id}'
      msg += 'keyword: {}\nchannel: https://t.me/{}\n---\n'.format(keywords,channel_name)

    re_update = utils.db.user_subscribe_list.update(status = 1 ).where(utils.User_subscribe_list.user_id == user_id)#更新状态
    re_update = re_update.execute()# 更新成功返回1，不管是否重复执行
    if re_update:
      await event.respond('success unsubscribe_all:\n' + msg,link_preview = False,parse_mode = None)
  else:
    await event.respond('not found unsubscribe list')
  raise events.StopPropagation


@bot.on(events.NewMessage(pattern='/unsubscribe_id'))
async def unsubscribe_id(event):
  '''
  根据id取消订阅
  '''
  chat_id = event.message.chat.id
  find = utils.db.user.get_or_none(chat_id=chat_id)
  user_id = find
  if not find:# 不存在用户信息
    await event.respond('Failed. Please input /start')
    raise events.StopPropagation
  text = event.message.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"
  splitd = [i for i in regex.split('\s+',text) if i]# 删除空元素
  if len(splitd) > 1:
    ids = [int(i) for i in splitd[1].split(',')]
    result = []
    for i in ids:
      re_update = utils.db.user_subscribe_list.update(status = 1 ).where(utils.User_subscribe_list.id == i,utils.User_subscribe_list.user_id == user_id)#更新状态
      re_update = re_update.execute()# 更新成功返回1，不管是否重复执行
      if re_update:
        result.append(i)
    await event.respond('success unsubscribe id:{}'.format(result if result else 'None'))
  elif len(splitd) < 2:
    await event.respond('输入需要**取消订阅**的订阅id：\n\nEnter the subscription id of the channel where ** unsubscribe **is required:')
    cache.set('status_{}'.format(chat_id),{'current_status':'/unsubscribe_id ids','record_value':None},expire=5*60)# 记录输入的关键字
    raise events.StopPropagation
  else:
    await event.respond('not found id')
  raise events.StopPropagation
  

@bot.on(events.NewMessage(pattern='/unsubscribe'))
async def unsubscribe(event):
  """Send a message when the command /unsubscribe is issued."""
  # insert chat_id
  chat_id = event.message.chat.id
  find = utils.db.user.get_or_none(chat_id=chat_id)
  user_id = find
  if not find:# 不存在用户信息
    await event.respond('Failed. Please input /start')
    raise events.StopPropagation
  

  text = event.message.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"
  splitd = [i for i in regex.split('\s+',text) if i]# 删除空元素
  if len(splitd) <= 1:
    await event.respond('输入需要**取消订阅**的关键字\n\nEnter a keyword that requires **unsubscribe**')
    cache.set('status_{}'.format(chat_id),{'current_status':'/unsubscribe keywords','record_value':text},expire=5*60)#设置5m后过期
  elif len(splitd)  == 3:
    command, keywords, channels = splitd
    result = update_subscribe(user_id,parse_full_command(command, keywords, channels))
    # msg = ''
    # for key,channel in result:
    #   msg += 'keyword:{}  channel:{}\n'.format(key,channel)
    # if msg:
    #   await event.respond('success unsubscribe:\n'+msg,parse_mode = None)
    await event.respond('success unsubscribe.')

  raise events.StopPropagation


@bot.on(events.NewMessage(pattern='/help'))
async def start(event):
  await event.respond('''

目的：根据关键字订阅频道消息，支持群组

BUG反馈：https://git.io/JJ0Ey

支持多关键字和多频道订阅，使用英文逗号`,`间隔

关键字和频道之间使用空格间隔

主要命令：

 - 订阅操作

  /subscribe  关键字1,关键字2 tianfutong,xiaobaiup

  /subscribe  关键字1,关键字2 https://t.me/tianfutong,https://t.me/xiaobaiup

 - 取消订阅

  /unsubscribe  关键字1,关键字2 https://t.me/tianfutong,https://t.me/xiaobaiup

 - 取消订阅id

  /unsubscribe_id  1,2

 - 取消所有订阅

  /unsubscribe_all

 - 显示所有订阅列表

  /list

---
Purpose: Subscribe to channel messages based on keywords. Support groups

BUG FEEDBACK: https://git.io/JJ0Ey

Multi-keyword and multi-channel subscription support, using comma `,` interval.

Use space between keywords and channels

Main command:

/subscribe  keyword1,keyword2 tianfutong,xiaobaiup
/subscribe  keyword1,keyword2 https://t.me/tianfutong,https://t.me/xiaobaiup

/unsubscribe  keyword1,keyword2 https://t.me/tianfutong,https://t.me/xiaobaiup

/unsubscribe_id  1,2

/unsubscribe_all

/list

  ''')
  raise events.StopPropagation


# 删除当前记录的用户状态
@bot.on(events.NewMessage(pattern='/cancel'))
async def cancel(event):
  chat_id = event.message.chat.id
  _ = cache.delete('status_{}'.format(chat_id))
  if _ :
    await event.respond('success cancel.')
  raise events.StopPropagation

# 查询当前用户的所有订阅
@bot.on(events.NewMessage(pattern='/list'))
async def _list(event):
  chat_id = event.message.chat.id
  find = utils.db.user.get_or_none(**{
      'chat_id':chat_id,
  })
  if find:
    find = utils.db.connect.execute_sql('select id,keywords,channel_name,chat_id from user_subscribe_list where user_id = %d and status  = %d' % (find.id,0) ).fetchall()
    if find:
      msg = ''
      # msg = 'list:\n'
      for sub_id,keywords,channel_name,chat_id in find:
        if not channel_name:
          chat_id,_ = telethon_utils.resolve_id(int(chat_id))
          channel_name = f'c/{chat_id}'
        _type = 'regex' if is_regex_str(keywords) else 'keyword'
        msg += 'id:{}\n{}: {}\nchannel: https://t.me/{}\n---\n'.format(sub_id,_type,keywords,channel_name)
      await event.respond(msg,parse_mode = None) # 不用任何模式解析 直接输出显示
    else:
      await event.respond('not found list')
  else:
    await event.respond('please /start')
  raise events.StopPropagation


# 其余消息的统一处理方法
@bot.on(events.NewMessage)
async def common(event):
  """Echo the user message."""
  chat_id = event.message.chat.id
  text = event.text
  text = text.replace('，',',')# 替换掉中文逗号
  text = regex.sub('\s*,\s*',',',text) # 确保英文逗号间隔中间都没有空格  如 "https://t.me/xiaobaiup, https://t.me/com9ji"

  find = cache.get('status_{}'.format(chat_id))
  if find:

    # 执行订阅
    if find['current_status'] == '/subscribe keywords':# 当前输入关键字
      await event.respond('输入需要订阅的频道url或者name：\n\nEnter the url or name of the channel to subscribe to:')
      cache.set('status_{}'.format(chat_id),{'current_status':'/subscribe channels','record_value':find['record_value'] + ' ' + text},expire=5*60)# 记录输入的关键字
      raise events.StopPropagation
    elif find['current_status'] == '/subscribe channels':# 当前输入频道
      full_command = find['record_value'] + ' ' + text
      splitd = [i for i in regex.split('\s+',full_command) if i]# 删除空元素
      command, keywords, channels = splitd
      user_id = utils.db.user.get_or_none(chat_id=chat_id)
      result = await join_channel_insert_subscribe(user_id,parse_full_command(command, keywords, channels))
      if isinstance(result,str): 
        await event.respond(result,parse_mode = None) # 提示错误消息
      else:
        msg = ''
        for key,channel in result:
          msg += 'keyword:{}  channel:{}\n'.format(key,channel)
        if msg:
          await event.respond('success subscribe:\n'+msg,parse_mode = None)

      cache.delete('status_{}'.format(chat_id))
      raise events.StopPropagation
    
    #取消订阅
    elif find['current_status'] == '/unsubscribe keywords':# 当前输入关键字
      await event.respond('输入需要**取消订阅**的频道url或者name：\n\nEnter the url or name of the channel where ** unsubscribe **is required:')
      cache.set('status_{}'.format(chat_id),{'current_status':'/unsubscribe channels','record_value':find['record_value'] + ' ' + text},expire=5*60)# 记录输入的关键字
      raise events.StopPropagation
    elif find['current_status'] == '/unsubscribe channels':# 当前输入频道
      full_command = find['record_value'] + ' ' + text
      splitd = [i for i in regex.split('\s+',full_command) if i]# 删除空元素
      command, keywords, channels = splitd
      user_id = utils.db.user.get_or_none(chat_id=chat_id)
      result = update_subscribe(user_id,parse_full_command(command, keywords, channels))
      # msg = ''
      # for key,channel in result:
      #   msg += '{},{}\n'.format(key,channel)
      # if msg:
      #   await event.respond('success:\n'+msg,parse_mode = None)
      await event.respond('success unsubscribe..')

      cache.delete('status_{}'.format(chat_id))
      raise events.StopPropagation
    elif find['current_status'] == '/unsubscribe_id ids':# 当前输入订阅id
      splitd =  text.strip().split(',')
      user_id = utils.db.user.get_or_none(chat_id=chat_id)
      result = []
      for i in splitd:
        if not i.isdigit():
          continue
        i = int(i)
        re_update = utils.db.user_subscribe_list.update(status = 1 ).where(utils.User_subscribe_list.id == i,utils.User_subscribe_list.user_id == user_id)#更新状态
        re_update = re_update.execute()# 更新成功返回1，不管是否重复执行
        if re_update:
          result.append(i)
      await event.respond('success unsubscribe id:{}'.format(result if result else 'None'))
  raise events.StopPropagation

if __name__ == "__main__":
    # 开启client loop。防止进程退出
    client.run_until_disconnected()