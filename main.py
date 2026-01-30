from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.star.filter.platform_adapter_type import PlatformAdapterType

def get_value(obj, key, default=None):
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    except Exception:
            return default
    


@register("Group_Blacklist", "星星旁の旷野", "群黑名单插件", "0.5.0")
class MyPlugin(Star):

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        # 读取配置
        self.detect_groups = [str(g) for g in config.get("detect_groups", []) or []]
        self.blacklist = [str(u) for u in config.get("blacklist", []) or []]
        self.targets_groups = [str(g) for g in config.get("target_groups", []) or []]
        self.notice_groups = [str(g) for g in config.get("group_request_notice_groups", []) or []]
    

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("unban")
    async def unban(self, event: AstrMessageEvent,ban_user_id: int):
        """将用户从黑名单中移除"""

        raw_message = event.message_obj.raw_message

        group_id = get_value(raw_message, "group_id")
        user_id = get_value(raw_message, "user_id")

        client = event.bot
        logger.debug(f"获取用户 {user_id} 在群 {group_id} 的权限")
        role = str(user_id)
        member_info = await client.api.call_action('get_group_member_info', group_id=group_id, user_id=user_id)
        role = get_value(member_info, "role", role)
        if role in ["owner", "admin"]:
           role = True
        else: 
            role = False
        if role:
            await self.put_kv_data(ban_user_id, False)
            yield event.plain_result(f" 已将 {ban_user_id} 移出黑名单!")
        else:
            yield event.plain_result(f"无此权限")

    @filter.command("ban")
    async def ban(self, event: AstrMessageEvent,ban_user_id: int):
        """将用户加入黑名单"""

        group_id = get_value(event.message_obj, "group_id", None)
        user_id = get_value(event.message_obj, "user_id", None)

        client = event.bot
        logger.debug(f"获取用户 {user_id} 在群 {group_id} 的权限")
        role = str(user_id)
        member_info = await client.api.call_action('get_group_member_info', group_id=group_id, user_id=user_id)
        role = get_value(member_info, "role", role)
        if role in ["owner", "admin"]:
           role = True
        else: 
            role = False
        if role:
            await self.put_kv_data(ban_user_id, True)
            yield event.plain_result(f" 已将 {ban_user_id} 加入黑名单!\n注意：该用户若已在群内不会被自动踢出，仅会被拒绝加群请求。")
        else:
            yield event.plain_result(f"无此权限")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("refresh")
    async def refresh(self, event: AstrMessageEvent):
        """刷新黑名单缓存"""
        group_id = get_value(event.message_obj, "group_id", None)
        user_id = get_value(event.message_obj, "user_id", None)

        client = event.bot
        logger.debug(f"获取用户 {user_id} 在群 {group_id} 的权限")
        role = str(user_id)
        member_info = await client.api.call_action('get_group_member_info', group_id=group_id, user_id=user_id)
        role = get_value(member_info, "role", role)
        if role in ["owner", "admin"]:
           role = True
        else: 
            role = False
        if role:
            for ban_user_id in self.blacklist:
                ban_user_id = int(ban_user_id)
                await self.put_kv_data(ban_user_id, True)
            yield event.plain_result(f" 已刷新黑名单缓存，共 {len(self.blacklist)} 个用户被加入黑名单!")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("checkban")
    async def checkban(self, event: AstrMessageEvent, ban_user_id: int):
        """检查用户是否在黑名单中"""
        user_status = await self.get_kv_data(ban_user_id, False)
        if user_status:
            yield event.plain_result(f"用户 {ban_user_id} 在黑名单中。")
        else:
            yield event.plain_result(f"用户 {ban_user_id} 不在黑名单中。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("allow")
    async def allow(self, event: AstrMessageEvent, flag: str):
        """快捷同意加群请求"""
        client = event.bot
        try:
            await client.api.call_action('set_group_add_request', flag=flag, approve=True)
            yield event.plain_result(f"已同意加群请求。")
        except Exception as e:
            logger.error(f"同意加群请求时出错: {e}")
            yield event.plain_result(f"同意加群请求时出错: {e}")

    @filter.platform_adapter_type(PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def groupin(self, event: AstrMessageEvent):
        """处理加群申请"""

        raw_message = event.message_obj.raw_message
        post_type = get_value(raw_message, "post_type")

        if post_type == "request" :
            if get_value(raw_message, "request_type") == "group":
                logger.debug(f"收到加群请求事件，将由本插件处理")
                group_id = get_value(raw_message, "group_id")
                user_id = int(get_value(raw_message, "user_id"))
                flag= get_value(raw_message, "flag")
                logger.debug(f"用户 {user_id} 申请加入群 {group_id}")
                if str(group_id) in self.detect_groups:
                    user_status = await self.get_kv_data(user_id,False)
                    if user_status:
                        logger.debug(f"用户 {user_id} 在黑名单中，拒绝加群请求")
                        client = event.bot
                        try:
                            group_name = str(group_id)
                            try:
                                group_info = await client.api.call_action('get_group_info', group_id=int(group_id))
                                group_name = group_info.get('group_name', group_name)
                            except Exception as e:
                                logger.error(f"获取群名称失败，使用群号作为名称{e}")
                                pass

                            await client.api.call_action('set_group_add_request', flag=flag, approve=False)
                            logger.debug(f"开始发送拒绝消息至目标群聊{self.targets_groups}")
                            forward_message = f"黑名单用户 {user_id} 试图加入群 {group_name}，已拒绝其加群请求。"
                            for target_group in self.targets_groups:
                                    logger.debug(f"正在将消息转发至群 {target_group}")
                                    await client.api.call_action(
                                        'send_group_msg',
                                        group_id=int(target_group),
                                        message=forward_message
                                    )
                            logger.info(f"已拒绝用户 {user_id} 的加群请求")
                        except Exception as e:
                            logger.error(f"拒绝加群请求时出错: {e}")
                    else:
                        logger.debug(f"用户 {user_id} 不在黑名单中，允许加群请求")
                        logger.info(f"发送入群申请快捷处理条给目标用户")
                        client = event.bot
                        try:
                            group_info = await client.api.call_action('get_group_info', group_id=int(group_id))
                            group_name = str(group_id)
                            group_name = group_info.get('group_name', group_name)

                            for notice_group in self.notice_groups:
                                logger.debug(f"正在发送加群请求通知给用户 {notice_group}")
                                await client.api.call_action(
                                    'send_group_msg',
                                    group_id=int(notice_group),
                                    message=f'''用户 {user_id} 申请加入群 {group_name}。\n
                                        如需同意该请求，请点击下方 +1'''
                                )

                                # 发送两次以自动产生 +1 按钮
                                await client.api.call_action(
                                    'send_group_msg',
                                    group_id=int(notice_group),
                                    message=f'''/allow {flag}'''
                                )
                                await client.api.call_action(
                                    'send_group_msg',
                                    group_id=int(notice_group),
                                    message=f'''/allow {flag}'''
                                )

                        except Exception as e:
                            logger.error(f"发送加群请求通知时出错: {e}")
                else:
                    logger.debug(f"群 {group_id} 不在监控列表中，忽略该加群请求")


    @filter.platform_adapter_type(PlatformAdapterType.AIOCQHTTP)
    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def groupout(self, event: AstrMessageEvent):
        """处理退群通知"""
        raw_message = event.message_obj.raw_message
        post_type = get_value(raw_message, "post_type")
        if post_type == "notice" :
            if get_value(raw_message, "notice_type") == "group_decrease":
                user_id = int(get_value(raw_message, "user_id"))
                group_id = get_value(raw_message, "group_id")
                sub_type = get_value(raw_message, "sub_type")
                if str(group_id) in self.detect_groups:
                    logger.debug(f"收到群 {group_id} 的退群通知，处理用户 {user_id} 的黑名单状态")
                    if sub_type == "leave":
                        logger.debug(f"用户 {user_id} 主动退出了群 {group_id}")
                    elif sub_type == "kick":
                        operator_id = get_value(raw_message, "operator_id")
                        logger.info(f"用户 {user_id} 被管理员 {operator_id} 踢出了群 {group_id}")
                        client = event.bot
                        for target_group in self.targets_groups:
                            logger.debug(f"正在将消息转发至群 {target_group}")
                            await client.api.call_action('send_group_msg',group_id=int(target_group),message=f"用户 {user_id} 被管理员踢出了群{group_id}\n已自动加入全群黑名单\n如需解封请管理员发送\"/unban {user_id}\"")
                        await self.put_kv_data(user_id, True)