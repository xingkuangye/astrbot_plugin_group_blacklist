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

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("unban")
    async def unban(self, event: AstrMessageEvent,user_id: int):
        """将用户从黑名单中移除"""
        await self.put_kv_data(user_id, False)
        yield event.plain_result(f" 已将 {user_id} 移出黑名单!")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("ban")
    async def ban(self, event: AstrMessageEvent,user_id: int):
        """将用户加入黑名单"""
        await self.put_kv_data(user_id, True)
        yield event.plain_result(f" 已将 {user_id} 加入黑名单!\n注意：该用户若已在群内不会被自动踢出，仅会被拒绝加群请求。")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("refresh")
    async def refresh(self, event: AstrMessageEvent):
        """刷新黑名单缓存"""
        for user_id in self.blacklist:
            user_id = int(user_id)
            await self.put_kv_data(user_id, True)
        yield event.plain_result(f" 已刷新黑名单缓存，共 {len(self.blacklist)} 个用户被加入黑名单!")

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
                        await client.api.call_action('send_group_msg',group_id=int(group_id),message=f"用户 {user_id} 被管理员踢出了群\n已自动加入全群黑名单")
                        await self.put_kv_data(user_id, True)