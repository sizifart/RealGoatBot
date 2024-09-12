import asyncio
import random
from urllib.parse import unquote, quote

import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from datetime import timedelta
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.functions import account
from pyrogram.raw.types import InputBotAppShortName, InputNotifyPeer, InputPeerNotifySettings
from .agents import generate_random_user_agent
from bot.config import settings
from typing import Callable
from time import time
import functools
from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers


def error_handler(func: Callable):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            await asyncio.sleep(1)
    return wrapper

class Tapper:
    def __init__(self, tg_client: Client, proxy: str):
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.proxy = proxy
        self.tg_web_data = None
        self.tg_client_id = 0

    async def get_tg_web_data(self) -> str:
        
        if self.proxy:
            proxy = Proxy.from_str(self.proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)
            
            while True:
                try:
                    peer = await self.tg_client.resolve_peer('realgoats_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")
                    await asyncio.sleep(fls + 3)
            
            ref_id = random.choices([settings.REF_ID, "333c4cc1-2ce4-4b17-99f8-7c3797832413"], weights=[75, 25], k=1)[0]
            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                platform='android',
                app=InputBotAppShortName(bot_id=peer, short_name="run"),
                write_allowed=True,
                start_param=ref_id
            ))

            auth_url = web_view.url
            init_data = unquote(string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])


            me = await self.tg_client.get_me()
            self.tg_client_id = me.id
            
            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return init_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error: {error}")
            await asyncio.sleep(delay=3)

    
    async def make_request(self, http_client, method, url=None, **kwargs):
        response = await http_client.request(method, url, **kwargs)
        response.raise_for_status()
        response_json = await response.json()
        return response_json
    
    @error_handler
    async def login(self, http_client, init_data):
        http_client.headers['Rawdata'] = init_data
        return await self.make_request(http_client, 'POST', url="https://dev-api.goatsbot.xyz/auth/login", json={})
        
    
    
    @error_handler
    async def get_me_info(self, http_client):
        return await self.make_request(http_client, 'GET', url="https://api-me.goatsbot.xyz/users/me")
    
    @error_handler
    async def get_tasks(self, http_client: aiohttp.ClientSession) -> dict:
        return await self.make_request(http_client, 'GET', url='https://api-mission.goatsbot.xyz/missions/user')
    
    
    @error_handler
    async def done_task(self, http_client: aiohttp.ClientSession, task_id: str):
        return await self.make_request(http_client, 'POST', url=f'https://dev-api.goatsbot.xyz/missions/action/{task_id}')
        
        
    @error_handler
    async def check_proxy(self, http_client: aiohttp.ClientSession) -> None:
        response = await self.make_request(http_client, 'GET', url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
        ip = response.get('origin')
        logger.info(f"{self.session_name} | Proxy IP: <lc>{ip}</lc>")
        
        
    
    async def run(self) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
                random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
                logger.info(f"{self.session_name} | Bot will start in <lc>{random_delay}s</lc>")
                await asyncio.sleep(random_delay)
        
        
        proxy_conn = ProxyConnector().from_url(self.proxy) if self.proxy else None
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)
        if self.proxy:
            await self.check_proxy(http_client=http_client)
        
        if settings.FAKE_USERAGENT:            
            http_client.headers['User-Agent'] = generate_random_user_agent(device_type='android', browser_type='chrome')

        init_data = await self.get_tg_web_data()
        
        while True:
            try:
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = ProxyConnector().from_url(self.proxy) if self.proxy else None
                    http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
                    if settings.FAKE_USERAGENT:            
                        http_client.headers['User-Agent'] = generate_random_user_agent(device_type='android', browser_type='chrome')
                _login = await self.login(http_client=http_client, init_data=init_data)
                
                accessToken = _login.get('tokens', {}).get('access', {}).get('token', None)
                if not accessToken:
                    logger.info(f"{self.session_name} | 🐐 <lc>Login failed</lc>")
                    await asyncio.sleep(300)
                    logger.info(f"{self.session_name} | Sleep <lc>300s</lc>")
                    continue
                
                logger.info(f"{self.session_name} | 🐐 <lc>Login successful</lc>")
                http_client.headers['Authorization'] = f'Bearer {accessToken}'
                me_info = await self.get_me_info(http_client=http_client)
                logger.info(f"{self.session_name} | Age: {me_info.get('age')} | Balance: {me_info.get('balance')}")
                
                tasks = await self.get_tasks(http_client=http_client)
                for project, project_tasks in tasks.items():
                    for task in project_tasks:
                        if not task.get('status'):
                            task_id = task.get('_id')
                            task_name = task.get('name')
                            task_reward = task.get('reward')
                            
                            logger.info(f"Attempting task: {project}: {task_name}")
                            
                            done_result = await self.done_task(http_client=http_client, task_id=task_id)
                            
                            if done_result and done_result.get('status') == 'success':
                                logger.info(f"Task completed successfully: {project}: {task_name} | Reward: +{task_reward}")
                            else:
                                logger.warning(f"Failed to complete task: {project}: {task_name}")
                        
                        await asyncio.sleep(5)
                
                await http_client.close()
                if proxy_conn:
                    if not proxy_conn.closed:
                        proxy_conn.close()
                        
            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=3)
            
            sleep_time = random.randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
            logger.info(f"{self.session_name} | Sleep <lc>{sleep_time}s</lc>")
            await asyncio.sleep(delay=sleep_time)
            
            
            
            

async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client, proxy=proxy).run()
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
