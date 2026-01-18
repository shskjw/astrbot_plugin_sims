import os
import json
from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from .core.common.data_manager import DataManager
from .core.common.image_utils import HTMLRenderer
from .core.common.config_manager import get_config
from .core import stock as stock_module, property as property_module, farm as farm_module, weather as weather_module, \
    pet as pet_module, relationship as relationship_module


@register("astrbot_plugin_sims", "shskjw",
          "模拟人生插件 - 农场/警察/医生/消防员/钓鱼/网吧/电影院/厨师/酒馆/宠物/关系等多系统经营游戏", "2.1.0")
class SimsPlugin(Star):
    def __init__(self, context: Context, config=None):
        try:
            super().__init__(context, config)
        except TypeError:
            super().__init__(context)

        # 加载插件配置
        self.config_manager = get_config()
        plugin_config = config if config else {}
        if plugin_config:
            self.config_manager.load_config(plugin_config)

        # 获取全局管理员列表
        self.admins = []
        if plugin_config and "admins_id" in plugin_config:
            for admin_id in plugin_config["admins_id"]:
                if str(admin_id).isdigit():
                    self.admins.append(str(admin_id))
            # 同步到配置管理器
            self.config_manager.set_admins(self.admins)

        self.data_manager = DataManager()
        # 模板渲染器，自动使用 resources/HTML 目录下的模板
        self.template = HTMLRenderer()
        # 子系统初始化
        self.stock_market = stock_module.logic.StockMarket()
        # 注册示例股票
        self.stock_market.register_stock(
            stock_module.models.StockData(id="S001", name="阿兹科技", price=12.34, volatility=0.6))
        self.stock_market.register_stock(
            stock_module.models.StockData(id="S002", name="绿能股份", price=8.21, volatility=0.4))

        self.property_market = property_module.logic.PropertyMarket()
        # 注册示例房产
        self.property_market.register_property(
            property_module.models.Property(id="P001", name="小公寓", price=10000, rent=50))
        self.property_market.register_property(
            property_module.models.Property(id="P002", name="商铺", price=50000, rent=300))

        # 农场子系统
        self.farm = farm_module.logic.FarmLogic(self.data_manager)
        self.farm_renderer = farm_module.render.FarmRenderer()

        # 天气系统
        self.weather = weather_module.logic.WeatherLogic(self.data_manager)

        # 宠物系统
        self.pet = pet_module.logic.PetLogic(self.data_manager)
        self.pet_renderer = pet_module.render.PetRenderer()

        # 关系系统
        self.relationship = relationship_module.logic.RelationshipLogic(self.data_manager)
        self.relationship_renderer = relationship_module.render.RelationshipRenderer()

        # 警察子系统
        from .core import police as police_module
        self.police = police_module.logic.PoliceLogic(self.data_manager)
        self.police_renderer = police_module.render.PoliceRenderer()

        # 医生子系统
        from .core import doctor as doctor_module
        self.doctor = doctor_module.logic.DoctorLogic(self.data_manager)
        self.doctor_renderer = doctor_module.render.DoctorRenderer()

        # 消防员子系统
        from .core import firefighter as firefighter_module
        self.firefighter = firefighter_module.logic.FirefighterLogic(self.data_manager)
        self.firefighter_renderer = firefighter_module.render.FirefighterRenderer()

        # 钓鱼子系统
        from .core import fishing as fishing_module
        self.fishing = fishing_module.logic.FishingLogic(self.data_manager)
        self.fishing_renderer = fishing_module.render.FishingRenderer()

        # 网吧子系统
        from .core import netbar as netbar_module
        self.netbar = netbar_module.logic.NetbarLogic(self.data_manager)
        self.netbar_renderer = netbar_module.render.NetbarRenderer()

        # 厨师子系统
        from .core import chef as chef_module
        self.chef = chef_module.logic.ChefLogic(self.data_manager)
        self.chef_renderer = chef_module.render.ChefRenderer()

        # 酒馆子系统
        from .core import tavern as tavern_module
        self.tavern = tavern_module.logic.TavernLogic(self.data_manager)
        self.tavern_renderer = tavern_module.render.TavernRenderer()

        # 电影院子系统
        from .core import cinema as cinema_module
        self.cinema = cinema_module.logic.CinemaLogic(self.data_manager)
        self.cinema_renderer = cinema_module.render.CinemaRenderer()

    # ========== 异步辅助方法 ==========
    async def _load_user(self, user_id: str) -> dict:
        """异步加载用户数据，返回默认值如果不存在"""
        data = await self.data_manager.async_load_user(user_id)
        return data or {"name": "玩家", "money": 1000}

    async def _save_user(self, user_id: str, data: dict):
        """异步保存用户数据"""
        await self.data_manager.async_save_user(user_id, data)

    def _bytes_to_image_path(self, img_bytes: bytes) -> str:
        """将图片字节转换为临时文件路径，供 event.image_result 使用"""
        import tempfile
        import os
        fd, path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(fd, 'wb') as tmp:
            tmp.write(img_bytes)
        return path

    @filter.command("模拟人生")
    async def sims_help(self, event: AstrMessageEvent):
        """显示模拟人生帮助"""
        user_id = event.get_sender_id()
        is_admin = self.config_manager.is_admin(user_id)

        # 加载帮助配置
        help_config_path = os.path.join(os.path.dirname(__file__), 'resources', 'help_config.json')
        help_data = {
            'helpCfg': {'title': '模拟人生帮助', 'subTitle': 'Yunzai-Bot & sims-Plugin'},
            'helpList': []
        }

        try:
            if os.path.exists(help_config_path):
                with open(help_config_path, 'r', encoding='utf-8') as f:
                    help_data = json.load(f)
        except Exception as e:
            self.logger.error(f"加载帮助配置失败: {e}")

        # 处理帮助列表，根据权限过滤
        help_groups = []
        for group in help_data.get('helpList', []):
            # 如果是管理员专属功能且用户不是管理员，则跳过
            if group.get('auth') == 'master' and not is_admin:
                continue

            # 处理每个帮助项的图标CSS
            for help_item in group.get('list', []):
                icon = help_item.get('icon', 0)
                if not icon:
                    help_item['css'] = 'display:none'
                else:
                    x = (icon - 1) % 10
                    y = (icon - x - 1) // 10
                    help_item['css'] = f'background-position:-{x * 50}px -{y * 50}px'

            help_groups.append(group)

        # 获取帮助配置
        help_cfg = help_data.get('helpCfg', {})
        col_count = help_cfg.get('colCount', 3)

        # 使用渲染器生成图片
        img = self.template.render(
            'sims_help.html',
            helpCfg=help_cfg,
            helpGroup=help_groups,
            colCount=col_count,
            bgType=''
        )
        # 转为图片字节
        from .core.common.screenshot import html_to_image_bytes
        # 传入base_path以修复CSS加载
        # 宽度调整为1000匹配CSS设定，高度由full_page=True自适应(如果有的话)
        img_bytes = await html_to_image_bytes(img, width=1000, height=2000, base_path=self.template.template_dir)

        if img_bytes:
            # AstrBot's event.image_result expects a string path or url, and doesn't support bytes directly.
            # We need to save the bytes to a temp file and pass the path, OR use MessageEventResult interface directly if possible.
            # However, looking at the error: "startswith first arg must be bytes or a tuple of bytes, not str"
            # Wait, the error is:
            # File "H:\AstrBot\astrbot\core\platform\astr_message_event.py", line 309, in image_result
            # if url_or_path.startswith("http"):
            # TypeError: startswith first arg must be bytes or a tuple of bytes, not str
            #
            # This means we passed BYTES (img_bytes) to a function that expected a STRING (url_or_path).
            # The line is `if url_or_path.startswith("http"):`
            # `url_or_path` is the bytes object we passed. "http" is a string.
            # In Python, bytes.startswith(str) raises TypeError.

            # Solution: Save bytes to a temp file and pass the path.
            import tempfile
            import os

            # Create a temporary file
            fd, path = tempfile.mkstemp(suffix=".png")
            try:
                with os.fdopen(fd, 'wb') as tmp:
                    tmp.write(img_bytes)
                yield event.image_result(path)
            finally:
                # We can't delete immediately because yield assumes the framework will read it.
                # But typically MessageEventResult processes immediately.
                # To be safe, we might unwantedly leave temp files.
                # Better approach: check if AstrBot supports bytes?
                # Based on source code read via terminal:
                # def image_result(self, url_or_path: str) -> MessageEventResult:
                #     if url_or_path.startswith("http"): ...
                # It strictly expects a string.
                pass
                # The framework likely reads the file content later.
                # Ideally config/logic should clean up old temp files or use a known temp dir.
                pass
        else:
            # 降级文本
            from .core.common.screenshot import _PLAYWRIGHT_AVAILABLE
            if not _PLAYWRIGHT_AVAILABLE:
                yield event.plain_result(
                    "无法渲染帮助图片。检测到缺少 Playwright 依赖。\n请在终端执行：\npip install playwright\nplaywright install chromium")
            else:
                yield event.plain_result("无法渲染帮助图片，未知错误，请检查后台日志。")

    @filter.command("模拟人生版本")
    async def sims_version(self, event: AstrMessageEvent):
        """显示模拟人生版本信息"""
        yield event.plain_result("模拟人生插件 v2.1.0\nby shskjw")

    # ========== 基础功能 ==========

    @filter.command("签到")
    async def cmd_daily_sign(self, event: AstrMessageEvent):
        """每日签到"""
        from datetime import datetime, timedelta
        user_id = event.get_sender_id()
        user = await self._load_user(user_id)

        today = datetime.now().strftime("%Y-%m-%d")
        last_sign = user.get('last_sign_date', '')

        if last_sign == today:
            yield event.plain_result("❌ 你今天已经签到过了，明天再来吧！")
            return

        # 计算连续签到
        streak = user.get('sign_streak', 0)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if last_sign == yesterday:
            streak += 1
        else:
            streak = 1

        # 签到奖励：基础100 + 连续签到加成
        base_reward = self.config_manager.daily_sign_reward
        bonus = min(streak * 10, 100)  # 连续签到每天+10，最多+100
        total_reward = base_reward + bonus

        user['money'] = user.get('money', 0) + total_reward
        user['last_sign_date'] = today
        user['sign_streak'] = streak
        user['total_signs'] = user.get('total_signs', 0) + 1

        await self._save_user(user_id, user)

        msg = f"✅ 签到成功！\n"
        msg += f"💰 获得 {total_reward} 金币"
        if bonus > 0:
            msg += f" (含连续签到加成 +{bonus})"
        msg += f"\n📅 连续签到: {streak} 天"
        msg += f"\n💵 当前余额: {user['money']} 金币"
        yield event.plain_result(msg)

    @filter.command("状态")
    async def cmd_player_status(self, event: AstrMessageEvent):
        """查看玩家状态"""
        user_id = event.get_sender_id()
        user = await self._load_user(user_id)

        msg = f"👤 玩家状态\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"🆔 ID: {user_id}\n"
        msg += f"📛 名称: {user.get('name', '玩家')}\n"
        msg += f"💰 金币: {user.get('money', 0)}\n"
        msg += f"📅 签到天数: {user.get('total_signs', 0)}\n"
        msg += f"🔥 连续签到: {user.get('sign_streak', 0)} 天\n"

        # 检查各系统状态
        systems = []
        try:
            if self.farm.load_farm(user_id):
                systems.append("🌾农场")
        except:
            pass
        try:
            if self.police._load_all_police().get(user_id):
                systems.append("👮警察")
        except:
            pass
        try:
            if self.doctor._load(self.doctor._doctors_file()).get(user_id):
                systems.append("👨‍⚕️医生")
        except:
            pass
        try:
            if self.firefighter._load_firefighters().get(user_id):
                systems.append("🚒消防员")
        except:
            pass
        try:
            if self.fishing._load_users().get(user_id):
                systems.append("🎣钓鱼")
        except:
            pass
        try:
            if self.chef._load_chef_data(user_id):
                systems.append("👨‍🍳厨师")
        except:
            pass
        try:
            if self.netbar._load_netbars().get(user_id):
                systems.append("🖥️网吧")
        except:
            pass
        try:
            if self.cinema._load_cinemas().get(user_id):
                systems.append("🎬电影院")
        except:
            pass
        try:
            if self.tavern._load_tavern_data(user_id):
                systems.append("🍺酒馆")
        except:
            pass

        if systems:
            msg += f"━━━━━━━━━━━━━━━\n"
            msg += f"📋 已开启系统:\n"
            msg += "  ".join(systems)

        yield event.plain_result(msg)

    @filter.command("背包")
    async def cmd_inventory(self, event: AstrMessageEvent):
        """查看背包"""
        user_id = event.get_sender_id()
        user = await self._load_user(user_id)

        inventory = user.get('inventory', {})

        msg = f"🎒 我的背包\n"
        msg += f"━━━━━━━━━━━━━━━\n"

        if not inventory:
            msg += "背包是空的，快去探索获取物品吧！"
        else:
            for item_name, item_data in inventory.items():
                if isinstance(item_data, dict):
                    count = item_data.get('count', 1)
                    msg += f"• {item_name} x{count}\n"
                else:
                    msg += f"• {item_name} x{item_data}\n"

        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"💰 金币: {user.get('money', 0)}"

        yield event.plain_result(msg)

    @filter.command("排行榜")
    async def cmd_leaderboard(self, event: AstrMessageEvent):
        """查看金币排行榜"""
        # 加载所有用户数据
        all_users = self.data_manager.load_all_users()

        if not all_users:
            yield event.plain_result("暂无排行数据")
            return

        # 按金币排序
        sorted_users = sorted(
            [(uid, data) for uid, data in all_users.items()],
            key=lambda x: x[1].get('money', 0),
            reverse=True
        )[:10]  # 取前10名

        msg = "🏆 金币排行榜 TOP 10\n"
        msg += "━━━━━━━━━━━━━━━\n"

        medals = ["🥇", "🥈", "🥉"]
        for i, (uid, data) in enumerate(sorted_users):
            rank = medals[i] if i < 3 else f"{i + 1}."
            name = data.get('name', uid[:8])
            money = data.get('money', 0)
            msg += f"{rank} {name}: {money} 💰\n"

        yield event.plain_result(msg)

    @filter.command("增加金币")
    async def cmd_admin_add_money(self, event: AstrMessageEvent, target_id: str, amount: int):
        """管理员增加金币"""
        user_id = event.get_sender_id()
        if not self.config_manager.is_admin(user_id):
            yield event.plain_result("🚫 只有管理员可以使用此命令。")
            return

        target_user = await self.data_manager.async_load_user(target_id)
        if not target_user:
            yield event.plain_result(f"找不到用户 {target_id}")
            return

        old_money = target_user.get('money', 0)
        target_user['money'] = old_money + amount
        await self.data_manager.async_save_user(target_id, target_user)
        yield event.plain_result(f"✅ 已给用户 {target_id} 增加 {amount} 金币。\n当前余额: {target_user['money']}")

    @filter.command("扣除金币")
    async def cmd_admin_remove_money(self, event: AstrMessageEvent, target_id: str, amount: int):
        """管理员扣除金币"""
        user_id = event.get_sender_id()
        if not self.config_manager.is_admin(user_id):
            yield event.plain_result("🚫 只有管理员可以使用此命令。")
            return

        target_user = await self.data_manager.async_load_user(target_id)
        if not target_user:
            yield event.plain_result(f"找不到用户 {target_id}")
            return

        old_money = target_user.get('money', 0)
        target_user['money'] = max(0, old_money - amount)
        await self.data_manager.async_save_user(target_id, target_user)
        yield event.plain_result(f"✅ 已扣除用户 {target_id} 的 {amount} 金币。\n当前余额: {target_user['money']}")

    @filter.command("重置玩家")
    async def cmd_admin_reset_user(self, event: AstrMessageEvent, target_id: str):
        """管理员重置玩家数据"""
        user_id = event.get_sender_id()
        if not self.config_manager.is_admin(user_id):
            yield event.plain_result("🚫 只有管理员可以使用此命令。")
            return

        # 这里仅重置金币和基础信息作为示例，根据需求可重置更多
        basic_data = {"name": "玩家", "money": 1000}
        await self.data_manager.async_save_user(target_id, basic_data)
        yield event.plain_result(f"⚠️ 用户 {target_id} 的数据已重置。")

    @filter.command("股票列表")
    async def stocks_list(self, event: AstrMessageEvent):
        tpl_list = [stock_module.render.render_stock_overview(s) for s in self.stock_market.stocks.values()]
        if not tpl_list:
            return event.plain_result("当前没有可交易的股票。")
        return event.plain_result("\n".join(tpl_list))

    @filter.command("买股票")
    async def cmd_buy_stock(self, event: AstrMessageEvent):
        # 格式： 买股票 <股票ID> <数量>
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法： 买股票 <股票ID> <数量>')
            return
        sid = parts[1]
        try:
            amt = int(parts[2])
        except Exception:
            yield event.plain_result('数量必须为整数')
            return
        try:
            res = self.stock_market.buy(self.data_manager, event.get_sender_id(), sid, amt)
            yield event.plain_result(f"购买成功：{sid} x{res['amount']} 平均价 {res['avg_price']:.2f}")
        except Exception as e:
            yield event.plain_result(f'购买失败: {e}')

    @filter.command("卖股票")
    async def cmd_sell_stock(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法： 卖股票 <股票ID> <数量>')
            return
        sid = parts[1]
        try:
            amt = int(parts[2])
        except Exception:
            yield event.plain_result('数量必须为整数')
            return
        try:
            res = self.stock_market.sell(self.data_manager, event.get_sender_id(), sid, amt)
            yield event.plain_result(f"卖出成功，获得 {res['revenue']:.2f} 金币，剩余持仓 {res['remaining']}")
        except Exception as e:
            yield event.plain_result(f'卖出失败: {e}')

    @filter.command("我的股票")
    async def cmd_my_stocks(self, event: AstrMessageEvent):
        holdings = self.stock_market.list_holdings(self.data_manager, event.get_sender_id())
        if not holdings:
            yield event.plain_result('你当前没有持仓')
            return
        lines = [f"{k}: {v['amount']} 股 (均价 {v['avg_price']:.2f})" for k, v in holdings.items()]
        yield event.plain_result('\n'.join(lines))

    @filter.command("房产列表")
    async def property_list(self, event: AstrMessageEvent):
        props = [f"{p.name} ({p.id}) — 价格: {p.price:.2f} 租金: {p.rent:.2f}" for p in
                 self.property_market.properties.values()]
        if not props:
            return event.plain_result("当前没有房产信息。")
        return event.plain_result("\n".join(props))

    @filter.command("创建农场")
    async def cmd_create_farm(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        user = await self._load_user(user_id)
        try:
            farm = self.farm.create_farm(user_id, user)
            # 渲染图片（需要 Playwright 支持）
            img = await self.farm_renderer.render_image('farm_created.html', farmName=farm['name'],
                                                        userName=user.get('name'))
            if img and isinstance(img, (bytes, bytearray)):
                img_path = self._bytes_to_image_path(img)
                yield event.image_result(img_path)
            else:
                yield event.plain_result('农场创建成功，但无法生成图片。')
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'创建失败: {e}')

    @filter.command("成为警察")
    async def cmd_join_police(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        user = await self._load_user(user_id)
        # 确保用户数据存在
        existing = await self.data_manager.async_load_user(user_id)
        if not existing:
            await self._save_user(user_id, user)
        try:
            result = self.police.join_police(user_id, user)
            yield event.plain_result(
                f"🚔 恭喜你成为了{result['info']['rank']}！\n薪资: {result['info']['salary']}金币/月\n使用 #警察信息 查看详情。")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"加入失败: {e}")

    @filter.command("警察信息")
    async def cmd_police_info(self, event: AstrMessageEvent):
        try:
            user_id = event.get_sender_id()
            info = self.police.get_user_info(user_id)
            if not info or not info.get('info'):
                yield event.plain_result('你还不是警察，使用 #成为警察 加入。')
                return
            p_info = info['info']
            skills = p_info.get('skills', {})
            lines = [
                f"🚔 警察信息 - {info.get('name', '玩家')}",
                f"警衔: {p_info.get('rank', '实习警员')}",
                f"经验: {p_info.get('experience', 0)}",
                f"破案数: {p_info.get('cases_solved', 0)}",
                f"巡逻时长: {p_info.get('patrol_hours', 0)}小时",
                f"声望: {p_info.get('reputation', 50)}",
                f"体力: {p_info.get('stamina', 100)}%",
                f"薪资: {p_info.get('salary', 3000)}金币/月",
                f"\n📊 技能:",
                f"  调查: {skills.get('investigation', 1)} | 战斗: {skills.get('combat', 1)}",
                f"  领导: {skills.get('leadership', 1)} | 沟通: {skills.get('communication', 1)}"
            ]
            equipment = info.get('equipment', [])
            if equipment:
                lines.append(f"\n🔫 装备({len(equipment)}件):")
                for eq in equipment[:5]:
                    lines.append(f"  - {eq.get('name')} (耐久:{eq.get('durability', 100)}%)")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f"获取警察信息失败: {e}")

    @filter.command("巡逻")
    async def cmd_patrol(self, event: AstrMessageEvent):
        """开始巡逻"""
        try:
            result = self.police.start_patrol(event.get_sender_id())
            evt = result['event']
            lines = [
                f"🚔 巡逻报告",
                f"事件: {evt['desc']}",
                f"获得经验: +{result['exp_gain']}",
                f"获得金币: +{result['money_gain']}",
                f"声望变化: +{result['rep_gain']}",
                f"\n当前状态:",
                f"  经验: {result['info'].get('experience', 0)}",
                f"  体力: {result['info'].get('stamina', 100)}%"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('你需要休息一下才能继续巡逻。')
            else:
                yield event.plain_result(f"巡逻失败: {e}")

    @filter.command("出警")
    async def cmd_accept_case(self, event: AstrMessageEvent):
        """接取案件"""
        cases = self.police.list_cases()
        if not cases:
            # 自动生成一个案件
            case = self.police.generate_random_case()
            cases = [case]
        c = cases[0]
        try:
            accepted = self.police.accept_case(event.get_sender_id(), c['id'])
            yield event.plain_result(
                f"📋 你已接取案件：\n{accepted['title']}\n难度: {accepted.get('difficulty', '普通')}\n奖励: {accepted.get('reward', 0)}金币\n\n使用 #处理案件 来破案")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"接案失败: {e}")

    @filter.command("处理案件")
    async def cmd_handle_case(self, event: AstrMessageEvent):
        """处理当前案件"""
        try:
            result = self.police.handle_case(event.get_sender_id())
            case = result['case']
            status = "✅ 破案成功!" if result['success'] else "❌ 破案失败"
            lines = [
                f"📋 案件处理结果",
                f"案件: {case.get('title')}",
                f"结果: {status}",
            ]
            if result['success']:
                lines.extend([
                    f"获得经验: +{result['exp_gain']}",
                    f"获得金币: +{result['money_gain']}",
                    f"声望: +{result['rep_change']}"
                ])
            else:
                lines.append(f"声望: {result['rep_change']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"处理失败: {e}")

    @filter.command("警察装备商店")
    async def cmd_police_shop(self, event: AstrMessageEvent):
        """查看警察装备商店"""
        shop = self.police.get_equipment_shop()
        lines = ["🔫 警察装备商店"]
        for category in ['weapons', 'armor', 'tools', 'special']:
            if category in shop:
                cat_name = {'weapons': '武器', 'armor': '防具', 'tools': '工具', 'special': '特殊'}[category]
                lines.append(f"\n【{cat_name}】")
                for name, data in list(shop[category].items())[:4]:
                    req = data.get('requirements', {})
                    lines.append(f"  {name} - ￥{data.get('price', 0)} (需要:{req.get('rank', '实习警员')})")
        lines.append("\n使用 #购买警察装备 <装备名> 购买")
        yield event.plain_result("\n".join(lines))

    @filter.command("购买警察装备")
    async def cmd_buy_police_equipment(self, event: AstrMessageEvent):
        """购买警察装备"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: #购买警察装备 <装备名>")
            return
        equipment_name = parts[1]
        try:
            result = self.police.buy_equipment(event.get_sender_id(), equipment_name)
            yield event.plain_result(
                f"✅ 购买成功!\n装备: {result['equipment']['name']}\n花费: {result['price']}金币\n剩余: {result['remaining_money']}金币")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"购买失败: {e}")

    @filter.command("维护装备")
    async def cmd_maintain_equipment(self, event: AstrMessageEvent):
        """维护警察装备"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: #维护装备 <装备名>")
            return
        equipment_name = parts[1]
        try:
            result = self.police.maintain_equipment(event.get_sender_id(), equipment_name)
            yield event.plain_result(
                f"🔧 维护完成!\n装备: {result['equipment']}\n花费: {result['cost']}金币\n耐久度: {result['old_durability']}% → {result['new_durability']}%")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"维护失败: {e}")

    @filter.command("警察升职考核")
    async def cmd_promotion_exam(self, event: AstrMessageEvent):
        """参加升职考核"""
        try:
            result = self.police.promotion_exam(event.get_sender_id())
            lines = [
                f"📝 升职考核结果",
                f"目标警衔: {result['target_rank']}",
                f"理论成绩: {result['theory_score']:.1f}分",
                f"体能成绩: {result['physical_score']:.1f}分",
                f"实践成绩: {result['practical_score']:.1f}分",
                f"总分: {result['total_score']:.1f}分 (及格线: 75分)",
                ""
            ]
            if result['passed']:
                lines.append(f"🎉 恭喜晋升为 {result['new_rank']}!")
                lines.append("获得奖励: 500经验 + 5000金币")
            else:
                lines.append("❌ 考核未通过，继续努力!")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('考核中心暂时繁忙，请稍后再试。')
            else:
                yield event.plain_result(f"考核失败: {e}")

    @filter.command("警员培训")
    async def cmd_police_training(self, event: AstrMessageEvent):
        """警员技能培训"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: #警员培训 <技能类型>\n可选: 调查/战斗/领导/沟通")
            return
        skill_type = parts[1]
        try:
            result = self.police.police_training(event.get_sender_id(), skill_type)
            if result['success']:
                yield event.plain_result(
                    f"🎓 培训成功!\n{skill_type}技能: {result['old_level']} → {result['new_level']}\n获得经验: +{result['exp_gain']}\n花费: {result['cost']}金币")
            else:
                yield event.plain_result(
                    f"😓 培训失败...\n{skill_type}技能保持: {result['old_level']}级\n花费: {result['cost']}金币")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('培训中心暂时繁忙，请稍后再试。')
            else:
                yield event.plain_result(f"培训失败: {e}")

    @filter.command("警察休息")
    async def cmd_police_rest(self, event: AstrMessageEvent):
        """休息恢复体力"""
        try:
            result = self.police.rest(event.get_sender_id())
            yield event.plain_result(f"😴 休息完成!\n体力: {result['old_stamina']}% → {result['new_stamina']}%")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('你刚休息过，请稍后再试。')
            else:
                yield event.plain_result(f"休息失败: {e}")

    @filter.command("警察排行榜")
    async def cmd_police_ranking(self, event: AstrMessageEvent):
        """查看警察排行榜"""
        parts = event.text.strip().split()
        rank_type = parts[1] if len(parts) > 1 else 'exp'
        if rank_type not in ['exp', 'cases', 'reputation']:
            rank_type = 'exp'

        rankings = self.police.get_police_ranking(rank_type)
        type_names = {'exp': '经验', 'cases': '破案数', 'reputation': '声望'}
        lines = [f"🏆 警察排行榜 ({type_names[rank_type]}):"]

        for i, r in enumerate(rankings[:10], 1):
            if rank_type == 'exp':
                score = f"{r['experience']}exp"
            elif rank_type == 'cases':
                score = f"{r['cases_solved']}案"
            else:
                score = f"{r['reputation']}声望"
            lines.append(f"{i}. {r['name']} ({r['rank']}) - {score}")

        yield event.plain_result("\n".join(lines))

    @filter.command("成为医生")
    async def cmd_join_doctor(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        user = self.data_manager.load_user(user_id) or {"name": "玩家", "money": 0}
        if not self.data_manager.load_user(user_id):
            self.data_manager.save_user(user_id, user)
        try:
            d = self.doctor.register_doctor(user_id, user)
            yield event.plain_result(
                f"🏥 恭喜你成为了{d.get('rank', '实习医生')}！\n薪资: {d.get('salary', 5000)}金币/月\n使用 #医生信息 查看详情。")
        except Exception as e:
            yield event.plain_result(f"注册失败: {e}")

    @filter.command("医生信息")
    async def cmd_doctor_info(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        info = self.doctor.get_info(user_id)
        if not info:
            yield event.plain_result('你还不是医生，使用 #成为医生 加入。')
            return
        skills = info.get('skills', {})
        stats = info.get('stats', {})
        hospital = info.get('hospital', {})
        lines = [
            f"🏥 医生信息 - {info.get('name', '医生')}",
            f"职称: {info.get('rank', '实习医生')} (Lv.{info.get('level', 1)})",
            f"经验: {info.get('experience', 0)}/{info.get('experience_needed', 1000)}",
            f"薪资: {info.get('salary', 5000)}金币/月",
            f"\n📊 技能:",
            f"  诊断: {skills.get('diagnosis', 50)} | 手术: {skills.get('surgery', 30)}",
            f"  开药: {skills.get('prescription', 40)} | 沟通: {skills.get('communication', 60)}",
            f"  研究: {skills.get('research', 20)}",
            f"\n📈 统计:",
            f"  治愈患者: {stats.get('patients_treated', 0)}",
            f"  完成手术: {stats.get('surgeries_performed', 0)}",
            f"  拯救生命: {stats.get('lives_saved', 0)}",
            f"\n🏥 医院: {hospital.get('name', '社区卫生服务中心')}",
            f"  等级: {hospital.get('level', 1)} | 声望: {hospital.get('reputation', 50)}"
        ]
        yield event.plain_result("\n".join(lines))

    @filter.command("出诊")
    async def cmd_treat(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        patients = self.doctor.list_patients()
        if not patients:
            # 自动生成一个患者
            self.doctor.create_patient()
            patients = self.doctor.list_patients()
        if not patients:
            yield event.plain_result('当前没有病人。')
            return
        p = patients[0]
        try:
            res = self.doctor.treat_patient(user_id, p['id'])
            yield event.plain_result(
                f"✅ 治疗成功!\n患者: {res['patient'].get('name')}\n疾病: {res['patient'].get('disease')}\n获得金币: +{res['reward']}\n获得经验: +{res['exp_gain']}")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'出诊失败: {e}')

    # ========== 医生系统 - 补全功能 ==========

    @filter.command("诊断患者")
    async def cmd_diagnose_patient(self, event: AstrMessageEvent):
        """诊断患者"""
        patients = self.doctor.list_patients()
        if not patients:
            self.doctor.create_patient()
            patients = self.doctor.list_patients()
        if not patients:
            yield event.plain_result('当前没有病人。')
            return
        p = patients[0]
        try:
            res = self.doctor.diagnose_patient(event.get_sender_id(), p['id'])
            patient = res['patient']
            treatment = res.get('recommended_treatment', {})
            lines = [
                f"🔬 诊断结果",
                f"患者: {patient.get('name')} ({patient.get('age')}岁 {patient.get('gender')})",
                f"症状: {', '.join(patient.get('symptoms', [])[:4])}",
                f"诊断: {patient.get('disease')}",
                f"准确率: {res['accuracy']}%",
                f"获得经验: +{res['exp_gain']}",
            ]
            if treatment:
                lines.append(f"\n📋 建议治疗:")
                lines.append(f"  休息天数: {treatment.get('rest_days', 3)}天")
                if treatment.get('special_care'):
                    lines.append(f"  特殊护理: {treatment.get('special_care')}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'诊断失败: {e}')

    @filter.command("开药")
    async def cmd_prescribe_medicine(self, event: AstrMessageEvent):
        """给患者开药"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            medicines = self.doctor.get_medicines_list()[:5]
            lines = ["用法: #开药 <药品ID>", "\n可用药品:"]
            for m in medicines:
                lines.append(f"  ID:{m.get('id')} {m.get('name')} - 有效性:{m.get('effectiveness', 70)}%")
            yield event.plain_result("\n".join(lines))
            return

        try:
            medicine_id = int(parts[1])
        except:
            yield event.plain_result("药品ID必须是数字")
            return

        patients = self.doctor.list_patients()
        if not patients:
            yield event.plain_result('当前没有病人。')
            return
        p = patients[0]

        try:
            res = self.doctor.prescribe_medicine(event.get_sender_id(), p['id'], medicine_id)
            status = "✅ 治疗成功!" if res['success'] else "❌ 治疗效果不佳"
            lines = [
                f"💊 开药结果",
                f"药品: {res['medicine'].get('name')}",
                f"有效性: {res['effectiveness']}%",
                f"结果: {status}",
            ]
            if res['success']:
                lines.append(f"获得金币: +{res['reward']}")
            lines.append(f"获得经验: +{res['exp_gain']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'开药失败: {e}')

    @filter.command("执行手术")
    async def cmd_perform_surgery(self, event: AstrMessageEvent):
        """执行手术"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            surgeries = self.doctor.get_surgeries_list()[:5]
            lines = ["用法: #执行手术 <手术ID>", "\n可用手术:"]
            for s in surgeries:
                lines.append(
                    f"  ID:{s.get('id')} {s.get('name')} - 成功率:{s.get('success_rate', 70)}% 需要:{s.get('required_level', 1)}级")
            yield event.plain_result("\n".join(lines))
            return

        try:
            surgery_id = int(parts[1])
        except:
            yield event.plain_result("手术ID必须是数字")
            return

        patients = self.doctor.list_patients()
        if not patients:
            yield event.plain_result('当前没有需要手术的病人。')
            return
        p = patients[0]

        try:
            res = self.doctor.perform_surgery(event.get_sender_id(), p['id'], surgery_id)
            status = "✅ 手术成功!" if res['success'] else "⚠️ 手术出现并发症"
            lines = [
                f"🔪 手术结果",
                f"手术: {res['surgery'].get('name')}",
                f"成功率: {res['success_rate']}%",
                f"结果: {status}",
                f"详情: {res['outcome']}",
                f"获得金币: +{res['reward']}",
                f"获得经验: +{res['exp_gain']}",
                f"声望变化: {'+' if res['reputation_change'] > 0 else ''}{res['reputation_change']}"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'手术失败: {e}')

    @filter.command("医生培训")
    async def cmd_doctor_training(self, event: AstrMessageEvent):
        """医生技能培训"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: #医生培训 <技能类型>\n可选: 诊断/手术/开药/沟通/研究")
            return
        skill_type = parts[1]
        try:
            res = self.doctor.doctor_training(event.get_sender_id(), skill_type)
            if res['success']:
                yield event.plain_result(
                    f"🎓 培训成功!\n{skill_type}技能: {res['old_level']} → {res['new_level']}\n获得经验: +{res['exp_gain']}\n花费: {res['cost']}金币")
            else:
                yield event.plain_result(
                    f"😓 培训失败...\n{skill_type}技能保持: {res['old_level']}\n花费: {res['cost']}金币")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('培训中心暂时繁忙，请稍后再试。')
            else:
                yield event.plain_result(f"培训失败: {e}")

    @filter.command("开始研究")
    async def cmd_start_research(self, event: AstrMessageEvent):
        """开始医学研究"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: #开始研究 <项目名>\n可选: 新药研发/手术技术/疾病预防/基因治疗")
            return
        project_name = parts[1]
        try:
            res = self.doctor.start_research(event.get_sender_id(), project_name)
            project = res['project']
            yield event.plain_result(
                f"🔬 研究开始!\n项目: {project['name']}\n进度: {project['progress']}%\n完成奖励: {project['exp_reward']}经验 + {project['money_reward']}金币")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"开始研究失败: {e}")

    @filter.command("推进研究")
    async def cmd_advance_research(self, event: AstrMessageEvent):
        """推进研究进度"""
        try:
            res = self.doctor.advance_research(event.get_sender_id())
            lines = [
                f"🔬 研究进展",
                f"项目: {res['project_name']}",
                f"进度: {res['progress']}% (+{res['progress_gain']}%)"
            ]
            if res['completed']:
                lines.append(f"\n🎉 研究完成!")
                lines.append(f"获得经验: +{res['exp_gain']}")
                lines.append(f"获得金币: +{res['money_gain']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"推进研究失败: {e}")

    @filter.command("医生排行榜")
    async def cmd_doctor_ranking(self, event: AstrMessageEvent):
        """查看医生排行榜"""
        parts = event.text.strip().split()
        rank_type = parts[1] if len(parts) > 1 else 'exp'
        if rank_type not in ['exp', 'patients', 'surgeries']:
            rank_type = 'exp'

        rankings = self.doctor.get_doctor_ranking(rank_type)
        type_names = {'exp': '经验', 'patients': '治愈患者', 'surgeries': '手术数'}
        lines = [f"🏆 医生排行榜 ({type_names[rank_type]}):"]

        for i, r in enumerate(rankings[:10], 1):
            if rank_type == 'exp':
                score = f"{r['experience']}exp"
            elif rank_type == 'patients':
                score = f"{r['patients_treated']}人"
            else:
                score = f"{r['surgeries']}台"
            lines.append(f"{i}. {r['name']} ({r['rank']}) - {score}")

        yield event.plain_result("\n".join(lines))

    @filter.command("我的农场")
    async def cmd_view_farm(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        farm = self.farm.load_farm(user_id)
        if not farm:
            yield event.plain_result('你还没有农场，使用 #创建农场 来创建一个。')
            return
        img = await self.farm_renderer.render_image('farm_view.html', farm=farm)
        if img and isinstance(img, (bytes, bytearray)):
            img_path = self._bytes_to_image_path(img)
            yield event.image_result(img_path)
        else:
            yield event.plain_result('无法生成农场图片，请检查模板或截图管线。')

    @filter.command("购买农田")
    async def cmd_buy_land(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        user = self.data_manager.load_user(user_id) or {"name": "玩家", "money": 1000}
        try:
            farm = self.farm.buy_land(user_id, user)
            yield event.plain_result('购买成功，农田已升级。')
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'购买失败: {e}')

    # ========== 农场系统 - 补全功能 ==========

    @filter.command("农场状态")
    async def cmd_farm_status(self, event: AstrMessageEvent):
        """查看农场详细状态"""
        user_id = event.get_sender_id()
        try:
            status = self.farm.view_farm_status(user_id)
            lines = [
                f"🌾 {status['name']} (Lv.{status['level']})",
                f"经验: {status['experience']}/{status['next_level_exp']}",
                f"农田: {status['land']['name']} ({status['land']['size']}块地)",
                ""
            ]
            # 季节信息
            if status.get('current_season'):
                season = status['current_season']
                lines.append(f"🗓️ 当前季节: {season.get('name', '未知')}")
            # 地块状态
            lines.append("\n📊 地块状态:")
            for plot in status['plots']:
                if plot['crop']:
                    ready = "✅可收获" if plot.get('harvestReady') else f"🌱{plot.get('growth_progress', 0)}%"
                    lines.append(
                        f"  地块{plot['index']}: {plot['crop']} {ready} 💧{plot['water']}% 🌿{plot['fertility']}%")
                else:
                    lines.append(f"  地块{plot['index']}: 空地")
            # 活动事件
            if status.get('active_events'):
                lines.append("\n⚡ 活动事件:")
                for evt in status['active_events']:
                    lines.append(f"  - {evt['event_name']} ({evt['event_type']})")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f"查看失败: {e}")

    @filter.command("农场季节")
    async def cmd_farm_season(self, event: AstrMessageEvent):
        """查看当前季节和适种作物"""
        try:
            season_info = self.farm.get_seasonal_seeds()
            season = season_info.get('current_season', {})
            lines = [
                f"🗓️ 当前季节: {season.get('name', '未知')}",
                f"📝 {season.get('description', '')}",
                ""
            ]
            effects = season.get('effects', {})
            lines.append(f"📊 季节效果:")
            lines.append(f"  生长速度: {effects.get('growth', 1.0)}倍")
            lines.append(f"  水分消耗: {effects.get('water', 1.0)}倍")
            lines.append(f"  温度: {effects.get('temperature', '适中')}")

            if season_info.get('seasonal'):
                lines.append("\n🌱 当季作物:")
                for seed in season_info['seasonal'][:8]:
                    lines.append(f"  - {seed.get('name')} (￥{seed.get('price', 0)})")

            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f"查看季节失败: {e}")

    @filter.command("农场事件")
    async def cmd_farm_events(self, event: AstrMessageEvent):
        """查看当前活动的农场事件"""
        user_id = event.get_sender_id()
        try:
            events = self.farm.get_active_events(user_id)
            if not events:
                yield event.plain_result("当前没有活动事件。")
                return
            lines = ["⚡ 当前活动事件:"]
            for evt in events:
                effect = evt.get('effect', {})
                effect_str = ", ".join(f"{k}:{v}" for k, v in effect.items() if v != 0)
                status = "✅已补救" if evt.get('remedied') else "⏳进行中"
                lines.append(f"\n🎯 {evt['event_name']} [{evt['event_type']}] {status}")
                lines.append(f"   效果: {effect_str}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f"查看事件失败: {e}")

    @filter.command("触发事件")
    async def cmd_trigger_farm_event(self, event: AstrMessageEvent):
        """触发一个随机农场事件"""
        user_id = event.get_sender_id()
        try:
            evt = self.farm.trigger_random_event(user_id)
            if evt:
                yield event.plain_result(f"⚡ 发生了事件: {evt['event_name']}\n效果: {evt.get('effect', {})}")
            else:
                yield event.plain_result("没有触发任何事件。")
        except Exception as e:
            yield event.plain_result(f"触发事件失败: {e}")

    @filter.command("补救事件")
    async def cmd_remedy_event(self, event: AstrMessageEvent):
        """使用道具补救事件"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: #补救事件 <事件ID>")
            return
        try:
            event_id = int(parts[1])
            self.farm.remedy_event(event.get_sender_id(), event_id)
            yield event.plain_result("✅ 事件已成功补救！")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"补救失败: {e}")

    @filter.command("出售农产品")
    async def cmd_sell_crop(self, event: AstrMessageEvent):
        """出售农产品获得金币"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: #出售农产品 <作物名> [数量]")
            return
        crop_name = parts[1]
        quantity = int(parts[2]) if len(parts) > 2 else 1
        try:
            result = self.farm.sell_crop(event.get_sender_id(), crop_name, quantity)
            bonus_str = f" (季节加成x{result['season_bonus']})" if result['season_bonus'] > 1 else ""
            yield event.plain_result(
                f"💰 出售成功!\n"
                f"出售: {result['crop_name']} x{result['quantity']}\n"
                f"单价: {result['price_per_unit']}金币{bonus_str}\n"
                f"总收入: {result['total_price']}金币"
            )
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"出售失败: {e}")

    @filter.command("批量浇水")
    async def cmd_water_all(self, event: AstrMessageEvent):
        """给所有作物浇水"""
        try:
            result = self.farm.water_all_crops(event.get_sender_id())
            yield event.plain_result(f"💧 批量浇水完成!\n共给 {result['watered_count']} 块地浇了水。")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"浇水失败: {e}")

    @filter.command("批量施肥")
    async def cmd_fertilize_all(self, event: AstrMessageEvent):
        """给所有作物施肥"""
        try:
            result = self.farm.fertilize_all_crops(event.get_sender_id())
            yield event.plain_result(f"🌿 批量施肥完成!\n共给 {result['fertilized_count']} 块地施了肥。")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"施肥失败: {e}")

    @filter.command("批量收获")
    async def cmd_harvest_all(self, event: AstrMessageEvent):
        """收获所有成熟作物"""
        try:
            result = self.farm.harvest_all_crops(event.get_sender_id())
            lines = [f"🌾 批量收获完成! 共收获 {result['total']} 个农产品:"]
            for h in result['harvested']:
                lines.append(f"  - 地块{h['plot']}: {h['name']} x{h['yield']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"收获失败: {e}")

    @filter.command("农场排行")
    async def cmd_farm_ranking(self, event: AstrMessageEvent):
        """查看农场排行榜"""
        parts = event.text.strip().split()
        rank_type = parts[1] if len(parts) > 1 else 'level'
        if rank_type not in ['level', 'harvest', 'income']:
            rank_type = 'level'

        try:
            rankings = self.farm.get_farm_ranking(rank_type)
            type_names = {'level': '等级', 'harvest': '收获量', 'income': '总收入'}
            lines = [f"🏆 农场排行榜 ({type_names[rank_type]}):"]

            for i, r in enumerate(rankings[:10], 1):
                if rank_type == 'level':
                    score = f"Lv.{r['level']} ({r['experience']}exp)"
                elif rank_type == 'harvest':
                    score = f"{r['total_harvested']}个"
                else:
                    score = f"{r['total_income']}金币"
                lines.append(f"{i}. {r['farm_name']} - {score}")

            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f"获取排行榜失败: {e}")

    # ========== 消防员系统命令 ==========
    @filter.command("加入消防队")
    async def cmd_join_fire_department(self, event: AstrMessageEvent):
        """加入消防队"""
        user_id = event.get_sender_id()
        try:
            info = self.firefighter.join_fire_department(user_id)
            lines = [
                "🔥 恭喜你成功加入消防队！",
                f"👤 职称：{info.rank}",
                f"🏢 消防站：{info.station.name}",
                "",
                "📝 新手攻略：",
                "1. 使用【消防演习】提升经验和技能",
                "2. 使用【灭火行动】执行真实任务",
                "3. 使用【学习消防技能 技能名】提高专业能力",
                "4. 使用【购买消防装备 装备名】保障安全",
                "5. 使用【消防救援 类型】执行救援任务"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'加入失败: {e}')

    @filter.command("消防员信息")
    async def cmd_firefighter_info(self, event: AstrMessageEvent):
        """查看消防员信息"""
        user_id = event.get_sender_id()
        try:
            info = self.firefighter.get_firefighter_info(user_id)
            from datetime import datetime
            join_date = datetime.fromisoformat(info.join_date)
            days = (datetime.now() - join_date).days

            success_rate = 0
            total = info.stats.missions_completed + info.stats.missions_failed
            if total > 0:
                success_rate = info.stats.missions_completed / total * 100

            lines = [
                "🚒 消防员信息",
                f"👤 职称：{info.rank}",
                f"📊 经验值：{info.experience}",
                f"📅 服役天数：{days}天",
                "",
                "📈 任务统计：",
                f"  ✅ 完成任务：{info.stats.missions_completed}",
                f"  ❌ 失败任务：{info.stats.missions_failed}",
                f"  🎯 成功率：{success_rate:.1f}%",
                f"  👥 救援人数：{info.stats.people_rescued}",
                "",
                f"🏋️ 训练次数：{info.stats.training_completed}",
                f"🛡️ 装备：{', '.join(info.equipment) or '无'}",
                f"📚 技能：{', '.join(info.skills) or '无'}",
                f"🏅 勋章：{info.stats.medals}"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'获取信息失败: {e}')

    @filter.command("消防站信息")
    async def cmd_fire_station_info(self, event: AstrMessageEvent):
        """查看消防站信息"""
        user_id = event.get_sender_id()
        try:
            station = self.firefighter.get_station_info(user_id)
            lines = [
                f"🏢 {station['name']}",
                f"⭐ 等级：{station['level']}",
                f"👥 人员：{station['staff']}/{station['max_staff']}",
                f"🚒 车辆：{len(station['vehicles'])}/{station['max_vehicles']}",
                f"  - {', '.join(station['vehicles'])}",
                f"🛡️ 装备：{', '.join(station['equipment'])}",
                f"⏱️ 响应时间：{station['response_time']}分钟",
                f"📈 升级进度：{station['upgrade_progress']}%"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取消防站信息失败: {e}')

    @filter.command("消防演习")
    async def cmd_firefighting_drill(self, event: AstrMessageEvent):
        """进行消防演习"""
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.firefighting_drill(user_id)
            status = "✅ 成功" if result.success else "❌ 失败"
            lines = [
                f"🔥 消防演习 - {result.drill_type}",
                f"结果：{status}",
                f"📊 获得经验：{result.exp_gained}",
                f"💪 消耗体力：{result.stamina_cost}",
                f"🎯 成功率：{result.success_rate:.1f}%"
            ]
            if result.health_lost > 0:
                lines.append(f"💔 损失生命：{result.health_lost}")
            if result.new_skill:
                lines.append(f"🎉 习得新技能：{result.new_skill}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'演习失败: {e}')

    @filter.command("灭火行动")
    async def cmd_start_firefighting(self, event: AstrMessageEvent):
        """开始灭火行动"""
        user_id = event.get_sender_id()
        try:
            mission = self.firefighter.start_firefighting_mission(user_id)
            lines = [
                f"🔥 紧急火灾警报！{mission['fire_location']}发生{mission['fire_name']}！",
                "",
                f"📊 难度：{'⭐' * mission['difficulty']}",
                f"⚠️ 危险度：{'🔥' * mission['danger']}",
                f"👥 被困人数：{mission['casualties']}",
                f"⏱️ 时限：{mission['time_limit'] // 60}分钟",
                "",
                f"🛡️ 建议装备：{', '.join(mission['required_equipment'])}",
                f"📚 建议技能：{', '.join(mission['recommended_skills'])}",
                "",
                "📝 使用【火灾控制 方案名】选择灭火方案：",
                f"  可选：{', '.join(mission['methods'])}"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'开始任务失败: {e}')

    @filter.command("火灾控制")
    async def cmd_fire_control(self, event: AstrMessageEvent):
        """执行火灾控制方案"""
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：火灾控制 <方案名>\n可选：直接灭火、疏散人员、控制火势、救援伤员、请求支援')
            return
        method = parts[1].strip()
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.fire_control(user_id, method)
            status = "✅ 成功" if result.success else "❌ 失败"
            lines = [
                f"🔥 灭火行动 - {result.method}",
                f"地点：{result.fire_location}",
                f"结果：{status}",
                "",
                result.message
            ]
            if result.exp_gained > 0:
                lines.append(f"📊 获得经验：{result.exp_gained}")
            if result.money_gained > 0:
                lines.append(f"💰 获得奖金：{result.money_gained}元")
            if result.people_rescued > 0:
                lines.append(f"👥 救出人数：{result.people_rescued}")
            if result.health_lost > 0:
                lines.append(f"💔 损失生命：{result.health_lost}")
            if result.mission_completed:
                lines.append("\n🎉 任务完成！")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'控制失败: {e}')

    @filter.command("消防技能列表")
    async def cmd_firefighter_skills_list(self, event: AstrMessageEvent):
        """查看消防技能列表"""
        try:
            skills = self.firefighter.get_skills_list()
            lines = ["📚 消防技能列表", ""]
            for skill in skills:
                prereq = f"(前置:{','.join(skill['prerequisites'])})" if skill['prerequisites'] else ""
                lines.append(f"【{skill['name']}】 - {skill['cost']}元 [{skill['required_rank']}] {prereq}")
                lines.append(f"  {skill['description']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取技能列表失败: {e}')

    @filter.command("学习消防技能")
    async def cmd_learn_firefighter_skill(self, event: AstrMessageEvent):
        """学习消防技能"""
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：学习消防技能 <技能名>\n使用【消防技能列表】查看可学技能')
            return
        skill_name = parts[1].strip()
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.learn_skill(user_id, skill_name)
            lines = [
                f"🎓 成功学习【{result['skill_name']}】！",
                f"📝 {result['description']}",
                f"💰 花费：{result['cost']}元"
            ]
            if result['buffs']:
                buffs = ", ".join(f"{k}+{v}%" for k, v in result['buffs'].items())
                lines.append(f"📈 增益效果：{buffs}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'学习失败: {e}')

    @filter.command("消防装备商店")
    async def cmd_firefighter_equipment_shop(self, event: AstrMessageEvent):
        """查看消防装备商店"""
        try:
            shop = self.firefighter.get_equipment_shop()
            lines = ["🛡️ 消防装备商店", ""]
            for item in shop:
                lines.append(f"【{item['name']}】 - {item['price']}元 [{item['required_rank']}]")
                lines.append(f"  {item['description']}")
                lines.append(f"  防护值：{item['protection']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取商店失败: {e}')

    @filter.command("购买消防装备")
    async def cmd_buy_firefighter_equipment(self, event: AstrMessageEvent):
        """购买消防装备"""
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：购买消防装备 <装备名>\n使用【消防装备商店】查看可购买装备')
            return
        equipment_name = parts[1].strip()
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.buy_equipment(user_id, equipment_name)
            lines = [
                f"✅ 成功购买【{result['equipment_name']}】！",
                f"📝 {result['description']}",
                f"💰 花费：{result['price']}元"
            ]
            if result['discount'] > 0:
                lines.append(f"🏷️ 已享受 {result['discount']}% 职称折扣")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'购买失败: {e}')

    @filter.command("消防救援类型")
    async def cmd_rescue_types_list(self, event: AstrMessageEvent):
        """查看救援类型列表"""
        try:
            rescue_types = self.firefighter.get_rescue_types()
            lines = ["🚑 救援类型列表", ""]
            for rt in rescue_types:
                lines.append(f"【{rt['name']}】 [{rt['min_rank']}]")
                lines.append(f"  {rt['description']}")
                lines.append(f"  难度：{'⭐' * rt['difficulty']} | 奖励：{rt['xp_reward']}exp + {rt['money_reward']}元")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取救援类型失败: {e}')

    @filter.command("消防救援")
    async def cmd_rescue_operation(self, event: AstrMessageEvent):
        """执行救援任务"""
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：消防救援 <救援类型>\n使用【消防救援类型】查看可选类型')
            return
        rescue_type = parts[1].strip()
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.rescue_operation(user_id, rescue_type)
            status = "✅ 成功" if result['success'] else "❌ 失败"
            lines = [
                f"🚑 救援行动 - {result['rescue_type']}",
                f"结果：{status}",
                result['message'],
                f"📊 获得经验：{result['exp_gained']}"
            ]
            if result['money_gained'] > 0:
                lines.append(f"💰 获得奖金：{result['money_gained']}元")
            if result['people_saved'] > 0:
                lines.append(f"👥 救出人数：{result['people_saved']}")
            if result['health_lost'] > 0:
                lines.append(f"💔 损失生命：{result['health_lost']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'救援失败: {e}')

    @filter.command("申请消防晋升")
    async def cmd_apply_fire_promotion(self, event: AstrMessageEvent):
        """申请消防职称晋升"""
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.apply_for_promotion(user_id)
            if result['success']:
                lines = [
                    "🎉 晋升成功！",
                    f"📈 {result['old_rank']} → {result['new_rank']}",
                    f"💰 工资提升至 {result['salary']} 元/天"
                ]
            else:
                lines = [
                    "❌ 晋升条件不足",
                    f"当前职称：{result['current_rank']}",
                    f"目标职称：{result['next_rank']}",
                    "",
                    "缺少条件："
                ]
                for m in result['missing']:
                    lines.append(f"  • {m}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'申请晋升失败: {e}')

    @filter.command("升级消防站")
    async def cmd_upgrade_fire_station(self, event: AstrMessageEvent):
        """升级消防站"""
        user_id = event.get_sender_id()
        try:
            result = self.firefighter.upgrade_station(user_id)
            lines = [
                f"🏢 消防站升级成功！",
                f"⭐ 当前等级：{result['new_level']}",
                f"💰 花费：{result['cost']}元",
                f"👥 人员：{result['staff']}",
                f"🚒 车辆：{', '.join(result['vehicles'])}"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'升级失败: {e}')

    @filter.command("消防排行榜")
    async def cmd_firefighter_ranking(self, event: AstrMessageEvent):
        """查看消防员排行榜"""
        parts = event.message_str.strip().split()
        sort_by = parts[1] if len(parts) > 1 else "experience"

        sort_options = {
            "经验": "experience",
            "任务": "missions",
            "救援": "rescued",
            "勋章": "medals"
        }
        sort_by = sort_options.get(sort_by, sort_by)

        try:
            rankings = self.firefighter.get_firefighter_ranking(sort_by)
            if not rankings:
                yield event.plain_result("暂无排行数据")
                return

            lines = [f"🚒 消防员排行榜（按{sort_by}排序）", ""]
            for i, entry in enumerate(rankings[:10], 1):
                lines.append(f"{i}. {entry.user_name}")
                lines.append(
                    f"   [{entry.rank}] 经验:{entry.experience} 任务:{entry.missions_completed} 救援:{entry.people_rescued}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取排行榜失败: {e}')

    @filter.command("消防训练")
    async def cmd_firefighter_train(self, event: AstrMessageEvent):
        """兼容旧命令"""
        user_id = event.get_sender_id()
        missions = self.firefighter.list_missions()
        if not missions:
            yield event.plain_result('当前没有任务。请使用【消防演习】或【灭火行动】进行训练。')
            return
        m = missions[0]
        try:
            self.firefighter.accept_mission(user_id, m['id'])
            yield event.plain_result(f"接取任务：{m['type']}")
        except Exception as e:
            yield event.plain_result(f'接任务失败: {e}')

    # ========== 钓鱼系统命令 ==========
    @filter.command("开始钓鱼")
    async def cmd_start_fishing(self, event: AstrMessageEvent):
        """开始钓鱼"""
        user_id = event.get_sender_id()
        try:
            result = self.fishing.start_fishing(user_id)
            yield event.plain_result(result['message'])
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('钓鱼太频繁啦，请稍后再试～')
            else:
                yield event.plain_result(f'开始钓鱼失败: {e}')

    @filter.command("收杆")
    async def cmd_pull_rod(self, event: AstrMessageEvent):
        """收杆"""
        user_id = event.get_sender_id()
        try:
            result = self.fishing.pull_rod(user_id)
            if result.success:
                lines = [
                    f"🎣 {result.message}",
                    f"📊 获得经验：{result.exp_gained}"
                ]
                if result.level_up:
                    lines.append(f"🎉 等级提升到 {result.new_level} 级！")
            else:
                lines = [f"😢 {result.message}"]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'收杆失败: {e}')

    @filter.command("钓鱼状态")
    async def cmd_fishing_status(self, event: AstrMessageEvent):
        """查看钓鱼状态"""
        user_id = event.get_sender_id()
        try:
            result = self.fishing.check_fishing_status(user_id)
            yield event.plain_result(result['message'])
        except Exception as e:
            yield event.plain_result(f'查询失败: {e}')

    @filter.command("钓鱼信息")
    async def cmd_fishing_info(self, event: AstrMessageEvent):
        """查看钓鱼信息"""
        user_id = event.get_sender_id()
        try:
            info = self.fishing.get_fishing_info(user_id)
            lines = [
                "🎣 钓鱼信息",
                f"📊 等级：{info['level']} ({info['exp']}/{info['exp_needed']} exp)",
                f"🐟 总钓鱼数：{info['total_catch']}",
                f"⚖️ 总重量：{info['total_weight']}kg",
                "",
                "🛠️ 装备：",
                f"  🎣 鱼竿：{info['rod']} (成功率 {info['rod_rate']}%)",
                f"  🪱 鱼饵：{info['bait']} (吸引率 {info['bait_rate']}%)",
                f"  🪣 鱼篓：{info['basket']} ({info['basket_used']}/{info['basket_capacity']})"
            ]
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取信息失败: {e}')

    @filter.command("查看鱼篓")
    async def cmd_check_basket(self, event: AstrMessageEvent):
        """查看鱼篓"""
        user_id = event.get_sender_id()
        try:
            basket = self.fishing.check_basket(user_id)
            lines = [
                f"🪣 {basket['basket_name']} ({basket['used']}/{basket['capacity']})",
                ""
            ]
            if not basket['fish_list']:
                lines.append("鱼篓是空的～")
            else:
                for fish in basket['fish_list']:
                    fresh = f"🟢 {fish['freshness']:.0f}%" if fish['freshness'] > 50 else (
                        f"🟡 {fish['freshness']:.0f}%" if fish['freshness'] > 20 else f"🔴 {fish['freshness']:.0f}%")
                    if fish['is_spoiled']:
                        fresh = "💀 变质"
                    lines.append(f"• {fish['name']} {fish['weight']}kg {'⭐' * fish['rarity']} {fresh}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'查看鱼篓失败: {e}')

    @filter.command("出售鱼获")
    async def cmd_sell_fish(self, event: AstrMessageEvent):
        """出售鱼获"""
        user_id = event.get_sender_id()
        try:
            result = self.fishing.sell_fish(user_id)
            yield event.plain_result(result.message)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'出售失败: {e}')

    @filter.command("升级鱼竿")
    async def cmd_upgrade_rod(self, event: AstrMessageEvent):
        """升级鱼竿"""
        user_id = event.get_sender_id()
        try:
            result = self.fishing.upgrade_rod(user_id)
            yield event.plain_result(result['message'])
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'升级失败: {e}')

    @filter.command("升级鱼饵")
    async def cmd_upgrade_bait(self, event: AstrMessageEvent):
        """升级鱼饵"""
        user_id = event.get_sender_id()
        try:
            result = self.fishing.upgrade_bait(user_id)
            yield event.plain_result(result['message'])
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'升级失败: {e}')

    @filter.command("钓鱼商店")
    async def cmd_fishing_shop(self, event: AstrMessageEvent):
        """查看钓鱼商店"""
        try:
            shop = self.fishing.get_equipment_shop()
            lines = ["🏪 钓鱼商店", ""]
            for item in shop:
                lines.append(f"【{item['name']}】({item['type']}) - {item['price']}金币")
                lines.append(f"  ID: {item['id']} | {item['attributes']}")
            lines.append("")
            lines.append("使用【购买钓鱼装备 装备ID】购买")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取商店失败: {e}')

    @filter.command("购买钓鱼装备")
    async def cmd_buy_fishing_equipment(self, event: AstrMessageEvent):
        """购买钓鱼装备"""
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：购买钓鱼装备 <装备ID>\n使用【钓鱼商店】查看可购买装备')
            return
        equipment_id = parts[1].strip()
        user_id = event.get_sender_id()
        try:
            result = self.fishing.buy_equipment(user_id, equipment_id)
            yield event.plain_result(result['message'])
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'购买失败: {e}')

    @filter.command("鱼类图鉴")
    async def cmd_fish_list(self, event: AstrMessageEvent):
        """查看鱼类图鉴"""
        try:
            fish_list = self.fishing.get_fish_list()
            lines = ["🐟 鱼类图鉴", ""]
            for fish in fish_list:
                lines.append(f"【{fish['name']}】 {'⭐' * fish['rarity']}")
                lines.append(
                    f"  价格: {fish['price']}金币/kg | 重量: {fish['weight_range']} | 难度: Lv.{fish['difficulty']}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取图鉴失败: {e}')

    @filter.command("钓鱼排行")
    async def cmd_fishing_ranking(self, event: AstrMessageEvent):
        """查看钓鱼排行榜"""
        parts = event.message_str.strip().split()
        sort_by = parts[1] if len(parts) > 1 else "catch"

        sort_options = {"数量": "catch", "重量": "weight", "最佳": "best"}
        sort_by = sort_options.get(sort_by, sort_by)

        try:
            rankings = self.fishing.get_fishing_ranking(sort_by)
            if not rankings:
                yield event.plain_result("暂无排行数据")
                return

            lines = [f"🎣 钓鱼排行榜（按{sort_by}排序）", ""]
            for i, entry in enumerate(rankings[:10], 1):
                best_info = f" | 最佳:{entry.best_catch_fish} {entry.best_catch_weight}kg" if entry.best_catch_fish else ""
                lines.append(f"{i}. {entry.user_name} [Lv.{entry.level}]")
                lines.append(f"   钓获:{entry.total_catch}条 总重:{entry.total_weight:.1f}kg{best_info}")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            yield event.plain_result(f'获取排行榜失败: {e}')

    @filter.command("钓鱼")
    async def cmd_fish(self, event: AstrMessageEvent):
        """快速钓鱼（兼容旧命令）"""
        user_id = event.get_sender_id()
        try:
            fish = self.fishing.go_fishing(user_id)
            yield event.plain_result(
                f"钓到了: {fish.get('name')} ({fish.get('weight', 1)}kg, 稀有度 {'⭐' * fish.get('rarity', 1)})")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'钓鱼失败: {e}')

    @filter.command("网吧充值")
    async def cmd_netbar_recharge(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： 网吧充值 <金额>')
            return
        try:
            amt = int(parts[1])
        except Exception:
            yield event.plain_result('金额必须为整数')
            return
        try:
            u = self.netbar.recharge(event.get_sender_id(), amt)
            yield event.plain_result(f"充值成功，余额: {u['balance']}")
        except Exception as e:
            yield event.plain_result(f'充值失败: {e}')

    @filter.command("网吧租赁")
    async def cmd_netbar_rent(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： 网吧租赁 <小时数>')
            return
        try:
            hours = int(parts[1])
        except Exception:
            yield event.plain_result('小时数必须为整数')
            return
        try:
            u = self.netbar.buy_hour(event.get_sender_id(), hours, price_per_hour=1)
            yield event.plain_result(f"租赁成功，剩余小时: {u['hours_remaining']}")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'租赁失败: {e}')

    # ========== 网吧经营系统 ==========

    @filter.command("创建网吧")
    async def cmd_create_netbar(self, event: AstrMessageEvent):
        """创建网吧"""
        parts = event.text.strip().split(maxsplit=1)
        name = parts[1] if len(parts) > 1 else None
        try:
            netbar = self.netbar.create_netbar(event.get_sender_id(), name)
            msg = f"🏪 恭喜！成功创建网吧【{netbar.name}】\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"📍 等级: {netbar.level}级\n"
            msg += f"💻 初始电脑: 基础配置×{netbar.computers.basic}\n"
            msg += f"⭐ 声誉: {netbar.reputation}\n"
            msg += f"💰 花费启动资金: 50000元\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💡 提示: 使用【我的网吧】查看网吧详情"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 创建失败: {e}')

    @filter.command("我的网吧")
    async def cmd_my_netbar(self, event: AstrMessageEvent):
        """查看网吧信息"""
        try:
            netbar = self.netbar.get_netbar_info(event.get_sender_id())
            msg = f"🏪 【{netbar.name}】\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"📊 等级: {netbar.level}级 | 声誉: {netbar.reputation}\n"
            msg += f"🧹 清洁度: {netbar.cleanliness:.0f}%\n"
            msg += f"🔧 设备状态: {netbar.maintenance.status:.0f}%\n"
            msg += f"━━━━━━━━━━━━━━\n"

            # 电脑信息
            c = netbar.computers
            msg += f"💻 电脑配置:\n"
            msg += f"   基础×{c.basic} | 标准×{c.standard} | 高端×{c.premium}\n"

            # 员工信息
            msg += f"👥 员工数量: {len(netbar.staff)}/{netbar.level * 3}\n"
            if netbar.staff:
                positions = {}
                for s in netbar.staff:
                    positions[s.position] = positions.get(s.position, 0) + 1
                pos_str = ' '.join(f"{p}×{c}" for p, c in positions.items())
                msg += f"   {pos_str}\n"

            # 设施信息
            facilities = []
            if netbar.facilities.snack_bar:
                facilities.append("小卖部")
            if netbar.facilities.rest_area:
                facilities.append("休息区")
            if netbar.facilities.gaming_area:
                facilities.append("电竞区")
            msg += f"🏠 设施: {', '.join(facilities) if facilities else '无特殊设施'}\n"

            # 收入信息
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💰 累计收入: {netbar.income}元\n"
            msg += f"💸 累计支出: {netbar.expenses}元\n"
            msg += f"📈 当日收入: {netbar.daily_income}元\n"
            msg += f"👥 顾客统计: {netbar.statistics.total_customers}人次"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ {e}')

    @filter.command("雇佣员工")
    async def cmd_hire_netbar_staff(self, event: AstrMessageEvent):
        """雇佣网吧员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            types = self.netbar.get_staff_types()
            msg = "�【网吧员工招聘】\n"
            msg += "━━━━━━━━━━━━━━━━━\n"
            for t in types:
                msg += f"👤 {t.get('position', 'N/A')}\n"
                msg += f"   💰 月薪: {t.get('salary', 0)}元\n"
                msg += f"   ⭐ 技能: {t.get('skill_level', 0)}\n"
                msg += f"   📝 {t.get('description', '暂无描述')}\n"
            msg += "━━━━━━━━━━━━━━━━━\n"
            msg += "用法: #雇佣员工 <职位>"
            yield event.plain_result(msg)
            return
        position = parts[1]
        try:
            result = self.netbar.hire_employee(event.get_sender_id(), position)
            msg = f"✅ 成功雇佣{result.get('position', '员工')}！\n"
            msg += f"━━━━━━━━━━━━━━━━━\n"
            msg += f"🆔 员工编号: {result.get('employee_id', 'N/A')}\n"
            msg += f"👤 职位: {result.get('position', 'N/A')}\n"
            msg += f"💰 首月工资: {result.get('salary', 0)}元\n"
            msg += f"⭐ 技能等级: {result.get('skill', 0)}\n"
            msg += f"😊 满意度: {result.get('satisfaction', 100)}%\n"
            msg += f"📝 {result.get('description', '暂无描述')}\n"
            msg += f"\n💡 提示: 员工工资每月自动扣费，需合理管理现金流"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 雇佣失败: {e}')

    @filter.command("解雇员工")
    async def cmd_fire_netbar_staff(self, event: AstrMessageEvent):
        """解雇网吧员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            try:
                netbar = self.netbar.get_netbar_info(event.get_sender_id())
                staff_list = netbar.get('staff', []) if isinstance(netbar, dict) else getattr(netbar, 'staff', [])
                if not staff_list:
                    yield event.plain_result("当前没有员工可解雇。")
                    return
                msg = "👥【网吧员工列表】\n"
                msg += "━━━━━━━━━━━━━━━━━\n"
                for s in staff_list:
                    s_id = s.get('id') if isinstance(s, dict) else getattr(s, 'id', 'N/A')
                    s_pos = s.get('position') if isinstance(s, dict) else getattr(s, 'position', 'N/A')
                    s_sal = s.get('salary') if isinstance(s, dict) else getattr(s, 'salary', 0)
                    s_perf = s.get('performance', 100) if isinstance(s, dict) else getattr(s, 'performance', 100)
                    msg += f"🆔 {s_id} - {s_pos}\n"
                    msg += f"   💰 月薪: {s_sal}元 | 🎯 绩效: {s_perf}%\n"
                msg += "━━━━━━━━━━━━━━━━━\n"
                msg += "用法: #解雇员工 <员工编号>"
                yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f'❌ 获取员工列表失败: {e}')
            return
        employee_id = parts[1]
        try:
            result = self.netbar.fire_employee(event.get_sender_id(), employee_id)
            msg = f"✅ 已解雇{result.get('position', '员工')}！\n"
            msg += f"━━━━━━━━━━━━━━━━━\n"
            msg += f"👤 职位: {result.get('position', 'N/A')}\n"
            msg += f"📅 工作期限: {result.get('work_days', 0)}天\n"
            msg += f"💰 遣散费: {result.get('severance_pay', 0)}元\n"
            msg += f"📈 获得经验: {result.get('experience_gained', 0)}\n"
            msg += f"\n💡 提示: 解雇员工会失去其带来的收益加成"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 解雇失败: {e}')

    @filter.command("购买网吧设备")
    async def cmd_buy_netbar_equipment(self, event: AstrMessageEvent):
        """购买网吧设备"""
        parts = event.text.strip().split()
        if len(parts) < 3:
            types = self.netbar.get_equipment_types()
            msg = "💻 可购买的设备类型:\n"
            msg += "━━━━━━━━━━━━━━\n"
            for t in types:
                msg += f"📦 {t['type']}配置\n"
                msg += f"   💰 单价: {t['price']}元\n"
                msg += f"   ⚡ 性能: {t['performance']}\n"
                msg += f"   🔧 维护费: {t['maintenance_cost']}元/次\n"
                msg += f"   💡 {t['description']}\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "用法: 购买网吧设备 <类型> <数量>\n"
            msg += "示例: 购买网吧设备 标准 5"
            yield event.plain_result(msg)
            return
        eq_type = parts[1]
        try:
            count = int(parts[2])
        except:
            yield event.plain_result("数量必须为整数！")
            return
        try:
            result = self.netbar.buy_equipment(event.get_sender_id(), eq_type, count)
            msg = f"✅ 成功购买{result['count']}台{result['type']}配置电脑！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💰 总花费: {result['total_cost']}元\n"
            msg += f"⭐ 声誉+{result['reputation_gain']}\n"
            msg += f"💡 {result['description']}"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 购买失败: {e}')

    @filter.command("维护网吧设备")
    async def cmd_maintain_netbar(self, event: AstrMessageEvent):
        """维护网吧设备"""
        try:
            result = self.netbar.maintain_equipment(event.get_sender_id())
            msg = f"🔧 设备维护完成！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"基础配置维护费: {result['basic_cost']}元\n"
            msg += f"标准配置维护费: {result['standard_cost']}元\n"
            msg += f"高端配置维护费: {result['premium_cost']}元\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💰 总花费: {result['total_cost']}元\n"
            msg += f"✅ 设备状态已恢复至100%"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 维护失败: {e}')

    @filter.command("购买网吧设施")
    async def cmd_buy_netbar_facility(self, event: AstrMessageEvent):
        """购买网吧设施"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            types = self.netbar.get_facility_types()
            msg = "🏠 可购买的设施:\n"
            msg += "━━━━━━━━━━━━━━\n"
            for t in types:
                msg += f"📦 {t['name']}\n"
                msg += f"   💰 价格: {t['price']}元\n"
                msg += f"   💡 {t['description']}\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "用法: 购买网吧设施 <设施名>"
            yield event.plain_result(msg)
            return
        facility_name = parts[1]
        try:
            result = self.netbar.buy_facility(event.get_sender_id(), facility_name)
            msg = f"✅ 成功购买{result['facility_name']}！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💰 花费: {result['price']}元\n"
            msg += f"💡 {result['description']}"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 购买失败: {e}')

    @filter.command("升级网吧")
    async def cmd_upgrade_netbar(self, event: AstrMessageEvent):
        """升级网吧"""
        try:
            result = self.netbar.upgrade_netbar(event.get_sender_id())
            msg = f"🎉 网吧升级成功！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"📊 等级: {result['old_level']} → {result['new_level']}\n"
            msg += f"💰 花费: {result['cost']}元\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"✨ 新福利:\n"
            msg += f"   👥 员工上限: {result['staff_limit']}人\n"
            msg += f"   💻 电脑上限: {result['computer_limit']}台"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 升级失败: {e}')

    @filter.command("收取网吧收入")
    async def cmd_collect_netbar_income(self, event: AstrMessageEvent):
        """收取网吧收入"""
        try:
            result = self.netbar.collect_income(event.get_sender_id())
            msg = f"💰 收入收取成功！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💵 收取金额: {result['collected']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ {e}')

    @filter.command("网吧排行榜")
    async def cmd_netbar_ranking(self, event: AstrMessageEvent):
        """网吧排行榜"""
        parts = event.text.strip().split()
        sort_by = parts[1] if len(parts) > 1 else "reputation"
        sort_options = {"声誉": "reputation", "等级": "level", "收入": "income", "电脑": "computers"}
        sort_key = sort_options.get(sort_by, sort_by)

        try:
            ranking = self.netbar.get_netbar_ranking(sort_key)
            if not ranking:
                yield event.plain_result("暂无排行数据")
                return

            sort_name = {"reputation": "声誉", "level": "等级", "income": "收入", "computers": "电脑数"}.get(sort_key,
                                                                                                             "声誉")
            msg = f"🏆 网吧排行榜 (按{sort_name}排序)\n"
            msg += "━━━━━━━━━━━━━━\n"
            for i, entry in enumerate(ranking[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                msg += f"{medal} {entry.netbar_name}\n"
                msg += f"   👤 {entry.owner_name}\n"
                msg += f"   📊 Lv{entry.level} | ⭐{entry.reputation} | 💻{entry.computer_count}台\n"
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f'❌ {e}')

    @filter.command("渲染模板")
    async def render_template(self, event: AstrMessageEvent):
        """调试命令：渲染并返回某个模板的 HTML（模板名作为参数）"""
        # 示例: "渲染模板 user_info.html"
        text = event.text.strip()
        parts = text.split()
        if len(parts) < 2:
            return event.plain_result("用法： 渲染模板 <模板文件名>")
        tpl_name = parts[1]
        try:
            html = self.template.render(tpl_name, user={"name": "测试用户", "money": 123.45})
            return event.plain_result(html[:400])
        except Exception as e:
            return event.plain_result(f"渲染出错: {e}")

    # ========== 厨师系统 - 完整版 ==========

    @filter.command("成为厨师")
    async def cmd_become_chef(self, event: AstrMessageEvent):
        try:
            res = self.chef.become_chef(event.get_sender_id())
            msg = self.chef_renderer.render_become_chef()
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"成为厨师失败: {e}")

    @filter.command("查看食谱")
    async def cmd_show_recipes(self, event: AstrMessageEvent):
        try:
            chef_data = self.chef._load_chef_data(event.get_sender_id())
            if not chef_data:
                yield event.plain_result("你还不是厨师！发送 #成为厨师 开始。")
                return
            msg = self.chef_renderer.render_recipes(self.chef.recipes, chef_data['recipes'], chef_data['level'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"查看食谱失败: {e}")

    @filter.command("学习食谱")
    async def cmd_learn_recipe(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： #学习食谱 <食谱ID>')
            return
        recipe_id = parts[1]
        try:
            res = self.chef.learn_recipe(event.get_sender_id(), recipe_id)
            msg = self.chef_renderer.render_learn_recipe(res['recipe'], res['cost'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"学习失败: {e}")

    @filter.command("制作料理")
    async def cmd_cook(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： #制作料理 <食谱ID>')
            return
        recipe_id = parts[1]
        try:
            res = self.chef.cook_dish(event.get_sender_id(), recipe_id)
            msg = self.chef_renderer.render_cook_result(res['success'], res['recipe'], res['chef_level'],
                                                        res['chef_exp'])
            yield event.plain_result(msg)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result(f"冷却中，请稍后。{str(e)}")
            else:
                yield event.plain_result(f"制作失败: {e}")
        except Exception as e:
            yield event.plain_result(f"制作失败: {e}")

    @filter.command("查看全部食材")
    async def cmd_show_ingredients(self, event: AstrMessageEvent):
        try:
            chef_data = self.chef._load_chef_data(event.get_sender_id())
            if not chef_data:
                yield event.plain_result("你还不是厨师！发送 #成为厨师 开始。")
                return
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            user_inv = {}
            for item in user.get('backpack', []):
                if item.get('type') == 'ingredient':
                    user_inv[item['id']] = item.get('amount', 1)
            msg = self.chef_renderer.render_ingredients(self.chef.ingredients, user_inv)
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"查看食材失败: {e}")

    @filter.command("购买食材")
    async def cmd_buy_ingredient(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： #购买食材 <食材ID> [数量]')
            return
        ing_id = parts[1]
        amount = int(parts[2]) if len(parts) > 2 else 1
        try:
            res = self.chef.buy_ingredient(event.get_sender_id(), ing_id, amount)
            msg = self.chef_renderer.render_buy_ingredient(res['ingredient'], res['amount'], res['cost'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"购买失败: {e}")

    @filter.command("查看厨具商店")
    async def cmd_show_kitchenware(self, event: AstrMessageEvent):
        try:
            chef_data = self.chef._load_chef_data(event.get_sender_id())
            if not chef_data:
                yield event.plain_result("你还不是厨师！发送 #成为厨师 开始。")
                return
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            owned = [item['id'] for item in user.get('backpack', []) if item.get('type') == 'kitchenware']
            msg = self.chef_renderer.render_kitchenware(self.chef.kitchenware, chef_data['level'], owned)
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"查看厨具失败: {e}")

    @filter.command("购买厨具")
    async def cmd_buy_kitchenware(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： #购买厨具 <厨具ID>')
            return
        kw_id = parts[1]
        try:
            res = self.chef.buy_kitchenware(event.get_sender_id(), kw_id)
            msg = self.chef_renderer.render_buy_kitchenware(res['kitchenware'], res['cost'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"购买失败: {e}")

    @filter.command("厨师等级")
    async def cmd_show_chef_level(self, event: AstrMessageEvent):
        try:
            chef_data = self.chef._load_chef_data(event.get_sender_id())
            if not chef_data:
                yield event.plain_result("你还不是厨师！发送 #成为厨师 开始。")
                return
            msg = self.chef_renderer.render_chef_info(chef_data)
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"查看失败: {e}")

    @filter.command("出售料理")
    async def cmd_sell_dish(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： #出售料理 <料理ID>')
            return
        dish_id = parts[1]
        try:
            res = self.chef.sell_dish(event.get_sender_id(), dish_id)
            msg = self.chef_renderer.render_sell_dish(res['dish'], res['price'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"出售失败: {e}")

    # ========== 厨师系统 - 高级功能 ==========

    @filter.command("创建厨师团队")
    async def cmd_create_chef_team(self, event: AstrMessageEvent):
        """创建厨师团队"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：#创建厨师团队 <团队名称>')
            return
        team_name = parts[1]
        try:
            res = self.chef.create_team(event.get_sender_id(), team_name)
            text = f"🎉【团队创建成功】\n\n"
            text += f"团队名称: {res['team']['name']}\n"
            text += f"团队ID: {res['team']['id']}\n"
            text += f"花费: {res['cost']}💰\n\n"
            text += "使用 #邀请加入团队 @某人 来邀请成员！"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("操作冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"创建失败: {e}")
        except Exception as e:
            yield event.plain_result(f"创建失败: {e}")

    @filter.command("加入厨师团队")
    async def cmd_join_chef_team(self, event: AstrMessageEvent):
        """加入厨师团队"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#加入厨师团队 <团队ID>')
            return
        team_id = parts[1]
        try:
            res = self.chef.join_team(event.get_sender_id(), team_id)
            yield event.plain_result(f"✅ 成功加入团队「{res['team']['name']}」！")
        except Exception as e:
            yield event.plain_result(f"加入失败: {e}")

    @filter.command("退出厨师团队")
    async def cmd_leave_chef_team(self, event: AstrMessageEvent):
        """退出厨师团队"""
        try:
            res = self.chef.leave_team(event.get_sender_id())
            yield event.plain_result(f"✅ 已退出团队「{res['left_team']}」")
        except Exception as e:
            yield event.plain_result(f"退出失败: {e}")

    @filter.command("解散厨师团队")
    async def cmd_disband_chef_team(self, event: AstrMessageEvent):
        """解散厨师团队"""
        try:
            res = self.chef.disband_team(event.get_sender_id())
            yield event.plain_result(f"✅ 已解散团队「{res['disbanded_team']}」")
        except Exception as e:
            yield event.plain_result(f"解散失败: {e}")

    @filter.command("我的厨师团队")
    async def cmd_my_chef_team(self, event: AstrMessageEvent):
        """查看我的厨师团队"""
        try:
            team = self.chef.get_user_team(event.get_sender_id())
            if not team:
                yield event.plain_result("你还没有加入任何团队。\n使用 #创建厨师团队 或 #加入厨师团队 来开始！")
                return

            text = f"👨‍🍳【{team['name']}】\n\n"
            text += f"团队ID: {team['id']}\n"
            text += f"等级: Lv.{team['level']} | 资金: {team['funds']}💰\n"
            text += f"成员 ({len(team['members'])}/5):\n"

            for mid in team['members']:
                is_leader = "👑" if mid == team['leader_id'] else "  "
                text += f"  {is_leader} {mid}\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取团队信息失败: {e}")

    @filter.command("厨师团队排行")
    async def cmd_chef_team_ranking(self, event: AstrMessageEvent):
        """查看厨师团队排行榜"""
        try:
            rankings = self.chef.get_team_ranking()
            if not rankings:
                yield event.plain_result("暂无团队排行数据。")
                return

            text = "🏆【厨师团队排行榜】\n\n"
            for r in rankings:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r['rank'], f"{r['rank']}.")
                text += f"{medal} {r['name']} (Lv.{r['level']})\n"
                text += f"   成员: {r['member_count']}人 | 声望: {r['total_reputation']} | 战力: {r['power']}\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取排行榜失败: {e}")

    @filter.command("发起厨艺比赛")
    async def cmd_create_cooking_contest(self, event: AstrMessageEvent):
        """发起厨艺比赛"""
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法：#发起厨艺比赛 <比赛名称> <食谱ID>')
            return
        contest_name = parts[1]
        recipe_id = parts[2]
        try:
            res = self.chef.create_contest(event.get_sender_id(), contest_name, recipe_id)
            contest = res['contest']
            text = f"🎊【厨艺比赛已创建】\n\n"
            text += f"比赛名称: {contest['name']}\n"
            text += f"比赛ID: {contest['id']}\n"
            text += f"比赛食谱: {contest['recipe_name']}\n"
            text += f"截止时间: {contest['deadline'][:16]}\n"
            text += f"花费: {res['cost']}💰\n\n"
            text += "其他厨师可使用 #参加厨艺比赛 来加入！"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("举办比赛冷却中(1小时)，请稍后再试。")
            else:
                yield event.plain_result(f"创建失败: {e}")
        except Exception as e:
            yield event.plain_result(f"创建失败: {e}")

    @filter.command("参加厨艺比赛")
    async def cmd_join_cooking_contest(self, event: AstrMessageEvent):
        """参加厨艺比赛"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#参加厨艺比赛 <比赛ID>')
            return
        contest_id = parts[1]
        try:
            res = self.chef.join_contest(event.get_sender_id(), contest_id)
            yield event.plain_result(f"✅ 成功参加比赛「{res['contest']['name']}」！\n使用 #提交比赛作品 来提交你的料理！")
        except Exception as e:
            yield event.plain_result(f"参加失败: {e}")

    @filter.command("提交比赛作品")
    async def cmd_submit_contest_dish(self, event: AstrMessageEvent):
        """提交比赛作品"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#提交比赛作品 <比赛ID>')
            return
        contest_id = parts[1]
        try:
            res = self.chef.submit_contest_dish(event.get_sender_id(), contest_id)
            yield event.plain_result(f"✅ 作品提交成功！\n你的得分: {res['score']}分")
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("提交冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"提交失败: {e}")
        except Exception as e:
            yield event.plain_result(f"提交失败: {e}")

    @filter.command("结束厨艺比赛")
    async def cmd_end_cooking_contest(self, event: AstrMessageEvent):
        """结束厨艺比赛(仅创建者)"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#结束厨艺比赛 <比赛ID>')
            return
        contest_id = parts[1]
        try:
            res = self.chef.end_contest(event.get_sender_id(), contest_id)
            text = f"🏆【比赛结束】{res['contest']['name']}\n\n"
            text += "获奖名单:\n"
            for r in res['results']:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r['rank'], "")
                text += f"{medal} 第{r['rank']}名: {r['user_id']}\n"
                text += f"   得分: {r['score']} | 奖励: {r['reward_money']}💰 +{r['reward_exp']}经验 +{r['reward_rep']}声望\n"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"结束失败: {e}")

    @filter.command("查看活跃比赛")
    async def cmd_list_active_contests(self, event: AstrMessageEvent):
        """查看活跃的厨艺比赛"""
        try:
            contests = self.chef.list_active_contests()
            if not contests:
                yield event.plain_result("当前没有进行中的厨艺比赛。\n使用 #发起厨艺比赛 来创建一个！")
                return

            text = "🎭【进行中的厨艺比赛】\n\n"
            for c in contests:
                text += f"📋 {c['name']}\n"
                text += f"   ID: {c['id']}\n"
                text += f"   食谱: {c['recipe_name']}\n"
                text += f"   参与人数: {c['participant_count']}人\n"
                text += f"   截止: {c['deadline'][:16]}\n\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取比赛列表失败: {e}")

    @filter.command("上架食材")
    async def cmd_list_ingredient_for_sale(self, event: AstrMessageEvent):
        """在食材市场上架食材"""
        parts = event.text.strip().split()
        if len(parts) < 4:
            yield event.plain_result('用法：#上架食材 <食材ID> <数量> <单价>')
            return
        ing_id = parts[1]
        try:
            quantity = int(parts[2])
            price = int(parts[3])
        except ValueError:
            yield event.plain_result("数量和价格必须是整数！")
            return
        try:
            res = self.chef.list_ingredient_for_sale(event.get_sender_id(), ing_id, quantity, price)
            listing = res['listing']
            text = f"✅【食材已上架】\n\n"
            text += f"食材: {listing['ingredient_name']}\n"
            text += f"数量: {listing['quantity']}\n"
            text += f"单价: {listing['price_per_unit']}💰\n"
            text += f"总价: {listing['total_price']}💰\n"
            text += f"挂单ID: {listing['id']}"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("操作冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"上架失败: {e}")
        except Exception as e:
            yield event.plain_result(f"上架失败: {e}")

    @filter.command("下架食材")
    async def cmd_cancel_listing(self, event: AstrMessageEvent):
        """取消食材挂单"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#下架食材 <挂单ID>')
            return
        listing_id = parts[1]
        try:
            res = self.chef.cancel_listing(event.get_sender_id(), listing_id)
            yield event.plain_result(
                f"✅ 已下架: {res['cancelled_listing']['ingredient_name']} x{res['cancelled_listing']['quantity']}")
        except Exception as e:
            yield event.plain_result(f"下架失败: {e}")

    @filter.command("食材市场")
    async def cmd_ingredient_market(self, event: AstrMessageEvent):
        """查看食材市场"""
        try:
            listings = self.chef.get_market_listings()
            if not listings:
                yield event.plain_result("食材市场暂无挂单。\n使用 #上架食材 来出售你的食材！")
                return

            text = "🏪【食材市场】\n\n"
            for l in listings[:15]:  # 最多显示15条
                text += f"📦 {l['ingredient_name']} x{l['quantity']}\n"
                text += f"   单价: {l['price_per_unit']}💰 | 总价: {l['total_price']}💰\n"
                text += f"   挂单ID: {l['id']}\n\n"

            text += "使用 #购买市场食材 <挂单ID> 来购买！"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取市场信息失败: {e}")

    @filter.command("购买市场食材")
    async def cmd_buy_from_market(self, event: AstrMessageEvent):
        """从食材市场购买"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#购买市场食材 <挂单ID>')
            return
        listing_id = parts[1]
        try:
            res = self.chef.buy_from_market(event.get_sender_id(), listing_id)
            purchased = res['purchased']
            yield event.plain_result(
                f"✅ 购买成功！\n获得: {purchased['ingredient_name']} x{purchased['quantity']}\n花费: {res['cost']}💰")
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("操作冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"购买失败: {e}")
        except Exception as e:
            yield event.plain_result(f"购买失败: {e}")

    @filter.command("我的挂单")
    async def cmd_my_listings(self, event: AstrMessageEvent):
        """查看我的食材挂单"""
        try:
            listings = self.chef.get_my_listings(event.get_sender_id())
            if not listings:
                yield event.plain_result("你没有正在出售的食材。")
                return

            text = "📋【我的挂单】\n\n"
            for l in listings:
                text += f"📦 {l['ingredient_name']} x{l['quantity']}\n"
                text += f"   单价: {l['price_per_unit']}💰 | 总价: {l['total_price']}💰\n"
                text += f"   ID: {l['id']}\n\n"

            text += "使用 #下架食材 <挂单ID> 来取消挂单"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取挂单失败: {e}")

    # ========== 厨师系统 - 合作料理 ==========

    @filter.command("发起合作料理")
    async def cmd_create_coop_cooking(self, event: AstrMessageEvent):
        """发起合作料理"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#发起合作料理 <食谱ID> [参与者ID1 参与者ID2 ...]')
            return
        recipe_id = parts[1]
        participant_ids = parts[2:] if len(parts) > 2 else []
        try:
            res = self.chef.create_coop_cooking(event.get_sender_id(), recipe_id, participant_ids)
            coop = res['coop']
            text = f"🍳【合作料理已发起】\n\n"
            text += f"料理ID: {coop['id']}\n"
            text += f"食谱: {coop['recipe_name']}\n"
            text += f"发起者: {event.get_sender_id()}\n"
            if participant_ids:
                text += f"邀请参与: {', '.join(participant_ids)}\n"
            text += f"\n被邀请者使用 #加入合作料理 {coop['id']} 来加入！"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("合作料理冷却中(5分钟)，请稍后再试。")
            else:
                yield event.plain_result(f"发起失败: {e}")
        except Exception as e:
            yield event.plain_result(f"发起失败: {e}")

    @filter.command("加入合作料理")
    async def cmd_join_coop_cooking(self, event: AstrMessageEvent):
        """加入合作料理"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#加入合作料理 <合作料理ID>')
            return
        coop_id = parts[1]
        try:
            res = self.chef.join_coop_cooking(event.get_sender_id(), coop_id)
            yield event.plain_result(f"✅ 已加入合作料理「{res['coop']['recipe_name']}」！\n使用 #贡献食材 来贡献你的食材！")
        except Exception as e:
            yield event.plain_result(f"加入失败: {e}")

    @filter.command("贡献食材")
    async def cmd_contribute_to_coop(self, event: AstrMessageEvent):
        """贡献食材到合作料理"""
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法：#贡献食材 <合作料理ID> <食材ID> [数量]')
            return
        coop_id = parts[1]
        ingredient_id = parts[2]
        amount = int(parts[3]) if len(parts) > 3 else 1
        try:
            res = self.chef.contribute_to_coop(event.get_sender_id(), coop_id, ingredient_id, amount)
            text = f"✅【食材已贡献】\n\n"
            text += f"食材: {res['ingredient']} x{res['amount']}\n"
            text += f"品质加成: +{res['quality_bonus']}\n"
            if res['is_required']:
                text += "👍 这是食谱所需的食材！\n"
            if res['coop_status'] == 'ready':
                text += "\n🎉 所有人都已贡献！发起者可以完成料理了！"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("操作冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"贡献失败: {e}")
        except Exception as e:
            yield event.plain_result(f"贡献失败: {e}")

    @filter.command("完成合作料理")
    async def cmd_complete_coop_cooking(self, event: AstrMessageEvent):
        """完成合作料理"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#完成合作料理 <合作料理ID>')
            return
        coop_id = parts[1]
        try:
            res = self.chef.complete_coop_cooking(event.get_sender_id(), coop_id)
            if res['success']:
                text = f"🎉【合作料理成功】\n\n"
                text += f"料理: {res['dish_name']}\n"
                text += f"品质: {res['quality']}\n"
                text += f"参与人数: {res['participant_count']}\n\n"
                text += "奖励分配:\n"
                for r in res['rewards']:
                    text += f"  {r['user_id']}: +{r['exp']}经验 +{r['reputation']}声望\n"
            else:
                text = f"😢【合作料理失败】\n\n{res['message']}\n成功率: {res['success_rate']:.1f}%"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"完成失败: {e}")

    @filter.command("我的合作料理")
    async def cmd_my_coop_cooking(self, event: AstrMessageEvent):
        """查看我参与的合作料理"""
        try:
            coops = self.chef.list_my_coop_cooking(event.get_sender_id())
            if not coops:
                yield event.plain_result("你没有正在进行的合作料理。\n使用 #发起合作料理 来开始！")
                return

            text = "🍳【我的合作料理】\n\n"
            for c in coops:
                text += f"📋 {c['recipe_name']}\n"
                text += f"   ID: {c['id']}\n"
                text += f"   状态: {c['status']}\n"
                text += f"   参与者: {len(c['participants'])}人\n"
                text += f"   品质加成: +{c['quality_bonus']}\n\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取失败: {e}")

    # ========== 厨师系统 - 成就系统 ==========

    @filter.command("厨师成就")
    async def cmd_chef_achievements(self, event: AstrMessageEvent):
        """查看厨师成就"""
        try:
            res = self.chef.get_user_achievements(event.get_sender_id())
            text = f"🏆【厨师成就】 {res['total_unlocked']}/{res['total_achievements']}\n\n"

            if res['current_title']:
                text += f"当前称号: 「{res['current_title']}」\n\n"

            text += "✅ 已解锁:\n"
            for ach in res['unlocked'][:5]:
                text += f"  🏅 {ach['name']} - {ach['description']}\n"

            text += "\n🔒 未解锁:\n"
            for ach in res['locked'][:5]:
                progress = ach.get('current_progress', 0)
                text += f"  ⬜ {ach['name']} ({progress}/{ach['requirement_value']})\n"

            if res['titles']:
                text += f"\n可用称号: {', '.join(res['titles'])}"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取成就失败: {e}")

    @filter.command("检查成就")
    async def cmd_check_achievements(self, event: AstrMessageEvent):
        """检查并解锁新成就"""
        try:
            newly_unlocked = self.chef.check_and_unlock_achievements(event.get_sender_id())
            if newly_unlocked:
                text = "🎉【新成就解锁】\n\n"
                for ach in newly_unlocked:
                    text += f"🏅 {ach['name']}\n"
                    text += f"   {ach['description']}\n"
                    rewards = []
                    if ach.get('reward_money'): rewards.append(f"{ach['reward_money']}💰")
                    if ach.get('reward_exp'): rewards.append(f"{ach['reward_exp']}经验")
                    if ach.get('reward_reputation'): rewards.append(f"{ach['reward_reputation']}声望")
                    if ach.get('reward_title'): rewards.append(f"称号「{ach['reward_title']}」")
                    if rewards:
                        text += f"   奖励: {', '.join(rewards)}\n"
                yield event.plain_result(text)
            else:
                yield event.plain_result("暂无新成就可解锁。继续努力！")
        except Exception as e:
            yield event.plain_result(f"检查失败: {e}")

    @filter.command("设置称号")
    async def cmd_set_chef_title(self, event: AstrMessageEvent):
        """设置厨师称号"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：#设置称号 <称号名>')
            return
        title = parts[1]
        try:
            res = self.chef.set_title(event.get_sender_id(), title)
            yield event.plain_result(f"✅ 称号已设置为「{res['title']}」")
        except Exception as e:
            yield event.plain_result(f"设置失败: {e}")

    # ========== 酒馆系统命令 ==========

    @filter.command("创建酒馆")
    async def cmd_create_tavern(self, event: AstrMessageEvent):
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result('用法：#创建酒馆 <酒馆名称>')
            return
        tavern_name = parts[1]
        try:
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            res = self.tavern.create_tavern(event.get_sender_id(), tavern_name, user.get('money', 0))
            msg = self.tavern_renderer.render_create_tavern(res['tavern'], res['cost'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"创建失败: {e}")

    @filter.command("酒馆信息")
    async def cmd_tavern_info(self, event: AstrMessageEvent):
        try:
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            res = self.tavern.get_tavern_info(event.get_sender_id())
            msg = self.tavern_renderer.render_tavern_info(res['tavern'], user.get('money', 0))
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"获取信息失败: {e}")

    @filter.command("酒馆市场")
    async def cmd_tavern_market(self, event: AstrMessageEvent):
        try:
            items = self.tavern.list_market_items()
            msg = self.tavern_renderer.render_market(items)
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"获取市场信息失败: {e}")

    @filter.command("购买酒馆物资")
    async def cmd_buy_tavern_supplies(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#购买酒馆物资 <物资ID> [数量]')
            return
        item_id = parts[1]
        quantity = int(parts[2]) if len(parts) > 2 else 1
        try:
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            res = self.tavern.buy_supplies(event.get_sender_id(), item_id, quantity, user.get('money', 0))
            msg = self.tavern_renderer.render_buy_supplies(res['item'], res['quantity'], res['total_price'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"购买失败: {e}")

    @filter.command("酒馆饮品")
    async def cmd_tavern_drinks(self, event: AstrMessageEvent):
        try:
            drinks = self.tavern.list_drinks()
            text = "【酒馆饮品列表】\n\n"
            for i, drink in enumerate(drinks[:10], 1):
                text += f"{i}. {drink.name} - {drink.base_price}元\n   {drink.description}\n"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取饮品列表失败: {e}")

    @filter.command("添加菜单")
    async def cmd_add_tavern_menu(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法：#添加菜单 <饮品ID> <价格>')
            return
        drink_id = parts[1]
        try:
            price = int(parts[2])
        except ValueError:
            yield event.plain_result('价格必须是整数！')
            return
        try:
            res = self.tavern.add_custom_menu_item(event.get_sender_id(), drink_id, price)
            msg = self.tavern_renderer.render_add_menu(res['menu_item'])
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"添加菜单失败: {e}")

    @filter.command("营业酒馆")
    async def cmd_operate_tavern(self, event: AstrMessageEvent):
        try:
            res = self.tavern.operate_tavern(event.get_sender_id())
            msg = self.tavern_renderer.render_operate_result(res)
            yield event.plain_result(msg)
        except Exception as e:
            if "cooldown:" in str(e):
                yield event.plain_result(f"操作冷却中: {e}")
            else:
                yield event.plain_result(f"营业失败: {e}")

    @filter.command("升级酒馆")
    async def cmd_upgrade_tavern(self, event: AstrMessageEvent):
        try:
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            res = self.tavern.upgrade_tavern(event.get_sender_id(), user.get('money', 0))
            msg = self.tavern_renderer.render_upgrade_result(res)
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"升级失败: {e}")

    @filter.command("酒馆员工")
    async def cmd_tavern_staff(self, event: AstrMessageEvent):
        try:
            res = self.tavern.get_tavern_info(event.get_sender_id())
            msg = self.tavern_renderer.render_staff_list(res['tavern'].staff)
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f"获取员工信息失败: {e}")

    @filter.command("酒馆雇佣员工")
    async def cmd_hire_tavern_staff(self, event: AstrMessageEvent):
        """酒馆雇佣员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            # 显示所有可用员工类型
            available_staff = [
                {'type': 'bartender', 'name': '酒保', 'salary': 100, 'level_req': 1, 'skills': '提高饮品效率、增加收入'},
                {'type': 'waiter', 'name': '服务员', 'salary': 80, 'level_req': 1, 'skills': '提高顾客满意度、增加消费'},
                {'type': 'cleaner', 'name': '清洁工', 'salary': 60, 'level_req': 2,
                 'skills': '维持清洁度、减缓环境恶化'},
                {'type': 'security', 'name': '保安', 'salary': 120, 'level_req': 3, 'skills': '维护秩序、解决冲突'},
                {'type': 'musician', 'name': '驻唱歌手', 'salary': 200, 'level_req': 4, 'skills': '提高氛围、吸引顾客'}
            ]
            msg = "🍺【酒馆员工招聘】\n"
            msg += "━━━━━━━━━━━━━━━━━\n"
            for staff in available_staff:
                msg += f"👤 {staff['name']} (ID: {staff['type']})\n"
                msg += f"   💰 月薪: {staff['salary']}元 | 📊 等级需求: {staff['level_req']}级\n"
                msg += f"   🎯 技能: {staff['skills']}\n"
            msg += "━━━━━━━━━━━━━━━━━\n"
            msg += "用法: #酒馆雇佣员工 <员工类型>"
            yield event.plain_result(msg)
            return
        staff_type = parts[1]
        try:
            user = self.data_manager.load_user(event.get_sender_id()) or {}
            res = self.tavern.hire_staff(event.get_sender_id(), staff_type, user.get('money', 0))
            staff_obj = res.get('staff')
            hire_cost = res.get('hire_cost', 0)

            # 获取员工信息
            staff_name = staff_obj.name if hasattr(staff_obj, 'name') else staff_obj.get('name', '员工')
            staff_id = staff_obj.id if hasattr(staff_obj, 'id') else staff_obj.get('id', 'N/A')

            msg = f"✅ 成功雇佣{staff_name}！\n"
            msg += f"━━━━━━━━━━━━━━━━━\n"
            msg += f"🆔 员工ID: {staff_id}\n"
            msg += f"👤 姓名: {staff_name}\n"
            msg += f"📊 职位: {staff_type}\n"
            msg += f"💰 首月工资: {hire_cost}元\n"
            msg += f"📈 晋升奖励: 经验+10\n"
            msg += f"\n💡 提示: 员工每天工作会增加经验，经验满后可升级"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"❌ 雇佣失败: {e}")

    @filter.command("酒馆解雇员工")
    async def cmd_fire_tavern_staff(self, event: AstrMessageEvent):
        """酒馆解雇员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            try:
                tavern_info = self.tavern.get_tavern_info(event.get_sender_id())
                staff_list = tavern_info.get('tavern').staff if isinstance(tavern_info.get('tavern'),
                                                                           object) else tavern_info.get('staff', [])
                if not staff_list:
                    yield event.plain_result("当前没有员工可解雇。")
                    return
                msg = "👥【酒馆员工列表】\n"
                msg += "━━━━━━━━━━━━━━━━━\n"
                for staff in staff_list:
                    s_id = staff.id if hasattr(staff, 'id') else staff.get('id', 'N/A')
                    s_name = staff.name if hasattr(staff, 'name') else staff.get('name', '未知')
                    s_type = staff.staff_type if hasattr(staff, 'staff_type') else staff.get('staff_type', 'N/A')
                    s_sal = staff.salary if hasattr(staff, 'salary') else staff.get('salary', 0)
                    msg += f"🆔 {s_id}\n"
                    msg += f"   姓名: {s_name} | 职位: {s_type} | 工资: {s_sal}元\n"
                msg += "━━━━━━━━━━━━━━━━━\n"
                msg += "用法: #酒馆解雇员工 <员工ID>"
                yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f'❌ 获取员工列表失败: {e}')
            return
        staff_id = parts[1]
        try:
            res = self.tavern.fire_staff(event.get_sender_id(), staff_id)
            fired_staff = res.get('fired_staff')
            staff_name = fired_staff.name if hasattr(fired_staff, 'name') else fired_staff.get('name', '员工')
            staff_type = fired_staff.staff_type if hasattr(fired_staff, 'staff_type') else fired_staff.get('staff_type',
                                                                                                           'N/A')

            msg = f"✅ 已解雇员工！\n"
            msg += f"━━━━━━━━━━━━━━━━━\n"
            msg += f"👤 员工: {staff_name}\n"
            msg += f"💼 职位: {staff_type}\n"
            msg += f"📝 状态: 已离职\n"
            msg += f"\n💡 提示: 解雇员工会失去其技能加成，可重新雇佣其他员工"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f"❌ 解雇失败: {e}")

    # ========== 酒馆系统 - 高级功能 ==========

    @filter.command("酒馆排行")
    async def cmd_tavern_ranking(self, event: AstrMessageEvent):
        """查看酒馆排行榜"""
        try:
            rankings = self.tavern.get_tavern_ranking()
            if not rankings:
                yield event.plain_result("暂无酒馆排行数据。")
                return

            text = "🏆【酒馆排行榜 TOP20】\n\n"
            for r in rankings:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r['rank'], f"{r['rank']}.")
                text += f"{medal} {r['name']} (Lv.{r['level']})\n"
                text += f"   总收入: {r['total_income']}💰 声誉: {r['reputation']}⭐ 评分: {r['rank_score']}\n"

            # 显示我的排名
            my_rank = self.tavern.get_my_rank(event.get_sender_id())
            if my_rank:
                text += f"\n📍你的排名: 第{my_rank['rank']}名 (评分: {my_rank['rank_score']})"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取排行榜失败: {e}")

    @filter.command("参观酒馆")
    async def cmd_visit_tavern(self, event: AstrMessageEvent):
        """参观其他玩家的酒馆"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#参观酒馆 <玩家ID>')
            return
        owner_id = parts[1]
        try:
            res = self.tavern.visit_tavern(event.get_sender_id(), owner_id)
            target = res['target_tavern']

            text = f"🍺【参观酒馆】\n\n"
            text += f"酒馆名称: {target['name']}\n"
            text += f"等级: Lv.{target['level']} | 人气: {target['popularity']}\n"
            text += f"氛围: {target['atmosphere']} | 声誉: {target['reputation']}⭐\n"
            text += f"菜单饮品: {target['menu_count']}种 | 员工: {target['staff_count']}人\n\n"
            text += f"✨ 参观灵感：你的酒馆{res['inspiration_bonus']} +{res['bonus_amount']}"

            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("参观冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"参观失败: {e}")
        except Exception as e:
            yield event.plain_result(f"参观失败: {e}")

    @filter.command("酒馆评分")
    async def cmd_rate_tavern(self, event: AstrMessageEvent):
        """给酒馆评分"""
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法：#酒馆评分 <玩家ID> <评分1-5>')
            return
        owner_id = parts[1]
        try:
            rating = int(parts[2])
        except ValueError:
            yield event.plain_result("评分必须是1-5的整数！")
            return
        comment = " ".join(parts[3:]) if len(parts) > 3 else ""
        try:
            res = self.tavern.rate_tavern(event.get_sender_id(), owner_id, rating, comment)
            yield event.plain_result(f"✅ 评分成功！\n当前平均分: {res['new_average']}⭐ (共{res['total_ratings']}条评价)")
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("评分冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"评分失败: {e}")
        except Exception as e:
            yield event.plain_result(f"评分失败: {e}")

    @filter.command("我的酒馆评分")
    async def cmd_my_tavern_ratings(self, event: AstrMessageEvent):
        """查看我的酒馆评分"""
        try:
            res = self.tavern.get_tavern_ratings(event.get_sender_id())
            text = f"⭐【{res['tavern_name']} 的评分】\n\n"
            text += f"平均评分: {res['average']}⭐ (共{res['total_ratings']}条)\n\n"

            if res['recent_ratings']:
                text += "最近评价:\n"
                for r in res['recent_ratings']:
                    text += f"  ⭐{r['rating']} - {r.get('comment', '无评语')}\n"
            else:
                text += "暂无评价"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取评分失败: {e}")

    @filter.command("处理酒馆事件")
    async def cmd_handle_tavern_event(self, event: AstrMessageEvent):
        """处理酒馆事件"""
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result('用法：#处理酒馆事件 <事件ID> <选择序号>')
            return
        event_id = parts[1]
        try:
            choice_idx = int(parts[2]) - 1  # 用户输入从1开始
        except ValueError:
            yield event.plain_result("选择序号必须是数字！")
            return
        try:
            res = self.tavern.process_event_choice(event.get_sender_id(), event_id, choice_idx)
            text = f"🎭【事件处理结果】\n\n"
            text += f"事件: {res['event']['title']}\n"
            text += f"选择: {res['choice']['text']}\n\n"
            text += "效果:\n"
            for k, v in res['effects'].items():
                sign = "+" if v > 0 else ""
                text += f"  • {k}: {sign}{v}\n"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("操作冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"处理失败: {e}")
        except Exception as e:
            yield event.plain_result(f"处理失败: {e}")

    @filter.command("酒馆事件历史")
    async def cmd_tavern_event_history(self, event: AstrMessageEvent):
        """查看酒馆事件历史"""
        try:
            history = self.tavern.get_event_history(event.get_sender_id())
            if not history:
                yield event.plain_result("暂无事件记录。")
                return

            text = "📜【酒馆事件历史】\n\n"
            for i, h in enumerate(history[-5:], 1):  # 最近5条
                text += f"{i}. {h['title']}\n"
                text += f"   选择: {h['choice']}\n"
                text += f"   效果: {h['effects']}\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取历史失败: {e}")

    # ========== 酒馆系统 - 特殊活动 ==========

    @filter.command("可办活动")
    async def cmd_list_activities(self, event: AstrMessageEvent):
        """列出可举办的活动"""
        try:
            activities = self.tavern.list_available_activities(event.get_sender_id())
            if not activities:
                yield event.plain_result("你需要先拥有酒馆才能举办活动！")
                return

            text = "🎭【可举办的活动】\n\n"
            for act in activities:
                status = "✅ 可举办" if act['can_host'] else f"❌ {act.get('missing_requirement', '条件不足')}"
                text += f"📋 {act['name']} (Lv.{act['min_level']}+)\n"
                text += f"   {act['description']}\n"
                text += f"   费用: {act['cost']}💰 | 时长: {act['duration_hours']}小时\n"
                text += f"   效果: {act['effects']}\n"
                text += f"   状态: {status}\n"
                text += f"   ID: {act['id']}\n\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取活动列表失败: {e}")

    @filter.command("举办活动")
    async def cmd_host_activity(self, event: AstrMessageEvent):
        """举办酒馆活动"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#举办活动 <活动ID>')
            return
        activity_id = parts[1]
        try:
            res = self.tavern.host_activity(event.get_sender_id(), activity_id)
            act = res['activity']
            text = f"🎉【活动已开始】\n\n"
            text += f"活动: {act['activity_name']}\n"
            text += f"开始: {act['start_time'][:16]}\n"
            text += f"结束: {act['end_time'][:16]}\n"
            text += f"花费: {res['cost']}💰\n\n"
            text += "即时效果:\n"
            for k, v in res['effects_applied'].items():
                text += f"  • {k}: +{v}\n"
            text += f"\n其他酒馆主可使用 #参加活动 {act['id']} 来参与！"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("举办活动冷却中(1小时)，请稍后再试。")
            else:
                yield event.plain_result(f"举办失败: {e}")
        except Exception as e:
            yield event.plain_result(f"举办失败: {e}")

    @filter.command("参加活动")
    async def cmd_join_activity(self, event: AstrMessageEvent):
        """参加其他酒馆的活动"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#参加活动 <活动实例ID>')
            return
        activity_id = parts[1]
        try:
            res = self.tavern.join_activity(event.get_sender_id(), activity_id)
            yield event.plain_result(
                f"✅ 成功参加「{res['activity_name']}」！\n举办酒馆: {res['host_tavern']}\n你的酒馆人气 +2")
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("参加活动冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"参加失败: {e}")
        except Exception as e:
            yield event.plain_result(f"参加失败: {e}")

    @filter.command("进行中活动")
    async def cmd_list_active_activities(self, event: AstrMessageEvent):
        """查看进行中的活动"""
        try:
            activities = self.tavern.list_active_activities()
            if not activities:
                yield event.plain_result("当前没有进行中的活动。\n使用 #举办活动 来开始一个！")
                return

            text = "🎭【进行中的活动】\n\n"
            for act in activities:
                text += f"📋 {act['activity_name']}\n"
                text += f"   举办: {act['tavern_name']}\n"
                text += f"   参与人数: {len(act['participants'])}人\n"
                text += f"   剩余: {act['remaining_hours']:.1f}小时\n"
                text += f"   ID: {act['id']}\n\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取活动列表失败: {e}")

    # ==================== IPO 与 股票扩展 ====================
    @filter.command("公司上市")
    async def cmd_ipo(self, event: AstrMessageEvent):
        """申请公司上市：#公司上市 <公司名> <股票代码> <发行价>"""
        parts = event.text.strip().split()
        if len(parts) < 4:
            yield event.plain_result("用法: 公司上市 <公司名> <股票代号> <发行价>")
            yield event.plain_result(f"示例: 公司上市 张三集团 ZSGP 10")
            return

        comp_name = parts[1]
        stock_name = parts[2]  # Actually mapped to 'stock_name' in model, but user provides code usually.
        # Wait, my logic takes: user_id: str, company_name: str, stock_name: str, initial_price: float
        # Let's align:
        #   company_name -> parts[1] (e.g. "ZhangSan Corp")
        #   stock_name -> parts[2] (e.g. "ZSC")
        try:
            price = float(parts[3])
        except:
            yield event.plain_result("价格必须是数字")
            return

        try:
            pc = self.stock_market.ipo(self.data_manager, event.get_sender_id(), comp_name, stock_name, price)
            yield event.plain_result(
                f"🎉 恭喜！你的公司【{pc.company_name}】已成功上市！\n股票代码: {pc.stock_id}\n当前股价: {pc.share_price}\n快邀请朋友购买你的股票吧！")
        except Exception as e:
            yield event.plain_result(f"上市失败: {e}")

    # ==================== P2P 交易市场 ====================
    @filter.command("发布收购")
    async def cmd_post_buy_order(self, event: AstrMessageEvent):
        """发布收购需求 (简化版: 只是喊话功能，配合转账使用)"""
        # True implementation requires complex Order Book.
        # For valid MVP: Just a broadcasting tool + 'transfer' command.
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result("用法: 发布收购 <物品名> <单价>")
            return

        item = parts[1]
        price = parts[2]
        user_name = event.get_sender_name()

        msg = f"📢【收购公告】\n"
        msg += f"老板: {user_name}\n"
        msg += f"需求: {item}\n"
        msg += f"出价: {price}金币/个\n"
        msg += f"有意者请私聊或使用 #转账 交易！"
        yield event.plain_result(msg)

    @filter.command("转账")
    async def cmd_transfer_money(self, event: AstrMessageEvent):
        """给其他玩家转账"""
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result("用法: 转账 <目标QQ> <金额>")
            return
        target_id = parts[1]
        try:
            amount = int(parts[2])
        except:
            yield event.plain_result("金额必须是整数")
            return

        if amount <= 0:
            yield event.plain_result("金额必须大于0")
            return

        user_id = event.get_sender_id()
        user = await self._load_user(user_id)

        if user.get('money', 0) < amount:
            yield event.plain_result("余额不足！")
            return

        target = await self.data_manager.async_load_user(target_id)
        if not target:
            yield event.plain_result("找不到目标用户")
            return

        user['money'] -= amount
        target['money'] = target.get('money', 0) + amount

        await self._save_user(user_id, user)
        await self._save_user(target_id, target)

        yield event.plain_result(f"✅ 转账成功！已向 {target.get('name', target_id)} 转账 {amount} 金币。")

    @filter.command("酿酒配方")
    async def cmd_brewing_recipes(self, event: AstrMessageEvent):
        """查看可用的酿酒配方"""
        try:
            recipes = self.tavern.list_brewing_recipes()
            text = "🍺 酿酒配方列表：\n"
            for r in recipes:
                text += f"\n🔖 {r['name']} ({r['type']})\n"
                text += f"   {r['description']}\n"
                text += f"   费用: {r['cost']}💰 | 时长: {r['brewing_hours']}小时\n"
                text += f"   参与人数: {r['min_participants']}-{r['max_participants']}人\n"
                text += f"   基础品质: {r['base_quality']}\n"
                text += f"   ID: {r['id']}\n\n"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取配方失败: {e}")

    @filter.command("发起酿酒")
    async def cmd_start_brewing(self, event: AstrMessageEvent):
        """发起合作酿酒"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#发起酿酒 <配方ID> [自定义酒名]')
            return
        recipe_id = parts[1]
        brew_name = " ".join(parts[2:]) if len(parts) > 2 else None
        try:
            res = self.tavern.start_brewing(event.get_sender_id(), recipe_id, brew_name)
            proj = res['project']
            text = f"🍺【酿酒项目已创建】\n\n"
            text += f"项目ID: {proj['id']}\n"
            text += f"酒名: {proj['name']}\n"
            text += f"类型: {proj['type']}\n"
            text += f"费用: {res['cost']}💰\n"
            text += f"预计完成: {res['estimated_hours']}小时后\n\n"
            text += f"其他酒馆主可使用 #参与酿酒 {proj['id']} 来加入！"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("发起酿酒冷却中(30分钟)，请稍后再试。")
            else:
                yield event.plain_result(f"发起失败: {e}")
        except Exception as e:
            yield event.plain_result(f"发起失败: {e}")

    @filter.command("参与酿酒")
    async def cmd_join_brewing(self, event: AstrMessageEvent):
        """参与合作酿酒"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#参与酿酒 <项目ID> [贡献金额]')
            return
        project_id = parts[1]
        contribution = int(parts[2]) if len(parts) > 2 else 100
        try:
            res = self.tavern.join_brewing(event.get_sender_id(), project_id, contribution)
            text = f"✅【已参与酿酒】\n\n"
            text += f"项目: {res['project_name']}\n"
            text += f"贡献: {res['contribution']}💰\n"
            text += f"品质加成: +{res['quality_bonus']}\n"
            text += f"当前品质: {res['new_quality']}"
            yield event.plain_result(text)
        except RuntimeError as e:
            if "cooldown" in str(e):
                yield event.plain_result("参与酿酒冷却中，请稍后再试。")
            else:
                yield event.plain_result(f"参与失败: {e}")
        except Exception as e:
            yield event.plain_result(f"参与失败: {e}")

    @filter.command("酿酒进度")
    async def cmd_brewing_progress(self, event: AstrMessageEvent):
        """查看酿酒进度"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#酿酒进度 <项目ID>')
            return
        project_id = parts[1]
        try:
            res = self.tavern.check_brewing_progress(project_id)
            proj = res['project']

            if res['status'] == 'completed':
                text = f"🍺【酿酒已完成】\n\n"
                text += f"酒名: {proj['name']}\n"
                text += f"最终品质: {proj.get('final_quality', proj['quality'])}"
            else:
                text = f"🍺【酿酒进度】\n\n"
                text += f"酒名: {proj['name']}\n"
                text += f"进度: {res['progress']}%\n"
                text += f"当前品质: {proj['quality']}\n"
                text += f"参与人数: {len(proj['participants'])}人\n"
                text += f"剩余时间: {res['remaining_hours']}小时"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"查询失败: {e}")

    @filter.command("完成酿酒")
    async def cmd_complete_brewing(self, event: AstrMessageEvent):
        """完成酿酒并领取成品"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法：#完成酿酒 <项目ID>')
            return
        project_id = parts[1]
        try:
            res = self.tavern.complete_brewing(event.get_sender_id(), project_id)
            text = f"🎉【酿酒完成】\n\n"
            text += f"酒名: {res['product_name']}\n"
            text += f"品质: {res['quality']}\n"
            text += f"产量: {res['count']}份\n"
            text += f"参与人数: {res['participant_count']}人\n\n"
            text += "成品已添加到你的酒馆饮品库存！"
            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"完成失败: {e}")

    @filter.command("酿酒项目")
    async def cmd_list_brewing_projects(self, event: AstrMessageEvent):
        """查看进行中的酿酒项目"""
        try:
            projects = self.tavern.list_brewing_projects()
            if not projects:
                yield event.plain_result("当前没有进行中的酿酒项目。\n使用 #发起酿酒 来开始！")
                return

            text = "🍺【进行中的酿酒项目】\n\n"
            for p in projects:
                status = "✅ 可领取" if p['is_complete'] else f"🔄 {p['progress']}%"
                text += f"📋 {p['name']} ({p['type']})\n"
                text += f"   发起者: {p['initiator_id']}\n"
                text += f"   参与: {p['participant_count']}/{p['max_participants']}人\n"
                text += f"   品质: {p['quality']} | 状态: {status}\n"
                text += f"   ID: {p['id']}\n\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取项目列表失败: {e}")

    @filter.command("我的酿酒")
    async def cmd_my_brewing(self, event: AstrMessageEvent):
        """查看我参与的酿酒项目"""
        try:
            projects = self.tavern.get_my_brewing(event.get_sender_id())
            if not projects:
                yield event.plain_result("你没有参与任何酿酒项目。\n使用 #参与酿酒 来加入一个！")
                return

            text = "🍺【我参与的酿酒】\n\n"
            for p in projects:
                text += f"📋 {p['name']} ({p['type']})\n"
                text += f"   ID: {p['id']}\n"
                text += f"   品质: {p['quality']} | 状态: {p['status']}\n\n"

            yield event.plain_result(text)
        except Exception as e:
            yield event.plain_result(f"获取失败: {e}")

    @filter.command("点酒")
    async def cmd_order_drink(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： 点酒 <饮品名>')
            return
        drink_name = parts[1]
        try:
            res = self.tavern.order_drink(event.get_sender_id(), drink_name)
            yield event.plain_result(f"点了: {res['name']} ({res['effect']})")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'点酒失败: {e}')

    # ========== 电影院系统 ==========

    @filter.command("看电影")
    async def cmd_watch_movie(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result('用法： 看电影 <电影ID>')
            return
        movie_id = parts[1]
        try:
            res = self.cinema.watch_movie(event.get_sender_id(), movie_id)
            yield event.plain_result(f"正在观看: {res['title']}")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'看电影失败: {e}')

    @filter.command("购买电影院")
    async def cmd_buy_cinema(self, event: AstrMessageEvent):
        """购买电影院"""
        parts = event.text.strip().split(maxsplit=1)
        name = parts[1] if len(parts) > 1 else None
        try:
            cinema = self.cinema.buy_cinema(event.get_sender_id(), name)
            msg = f"🎬 恭喜！成功购买电影院【{cinema.name}】\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"📍 等级: {cinema.level}级\n"
            msg += f"⭐ 声誉: {cinema.reputation}\n"
            msg += f"💰 花费启动资金: 100000元\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💡 提示: 使用【电影院信息】查看详情\n"
            msg += f"💡 使用【购买影厅】添加放映厅"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 购买失败: {e}')

    @filter.command("电影院信息")
    async def cmd_cinema_info(self, event: AstrMessageEvent):
        """查看电影院信息"""
        try:
            cinema = self.cinema.get_cinema_info(event.get_sender_id())
            msg = f"🎬 【{cinema.name}】\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"📊 等级: {cinema.level}级 | 声誉: {cinema.reputation}\n"

            # 影厅信息
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🎭 影厅数量: {len(cinema.theaters)}/{cinema.level * 2}\n"
            for t in cinema.theaters:
                from .core.cinema.models import THEATER_TYPES
                type_name = THEATER_TYPES[t.type]['name']
                msg += f"   📽️ {t.name}({type_name}) - {t.capacity}座\n"

            # 电影版权
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🎞️ 电影版权: {len(cinema.movies)}部\n"
            for m in cinema.movies[:3]:
                msg += f"   🎬 《{m.title}》 ⭐{m.rating}\n"
            if len(cinema.movies) > 3:
                msg += f"   ... 等{len(cinema.movies)}部电影\n"

            # 设施
            msg += f"━━━━━━━━━━━━━━\n"
            facilities = [f.name for f in cinema.facilities] or ['无']
            msg += f"🏠 设施: {', '.join(facilities)}\n"

            # 员工
            msg += f"👥 员工: {len(cinema.staff)}人\n"

            # 收入
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💰 累计收入: {cinema.total_revenue}元\n"
            msg += f"💵 日均收入: {cinema.daily_revenue}元\n"
            msg += f"💸 维护成本: {cinema.maintenance_cost}元/月\n"
            msg += f"💸 员工成本: {cinema.staff_cost}元/月"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ {e}')

    @filter.command("购买影厅")
    async def cmd_buy_theater(self, event: AstrMessageEvent):
        """购买影厅"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            types = self.cinema.get_theater_types()
            msg = "🎭 可购买的影厅类型:\n"
            msg += "━━━━━━━━━━━━━━\n"
            for t in types:
                msg += f"📽️ {t['type']} - {t['name']}\n"
                msg += f"   💺 座位: {t['capacity']}座\n"
                msg += f"   💰 价格: {t['cost']}元\n"
                msg += f"   🔧 维护: {t['maintenance_cost']}元/月\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "用法: 购买影厅 <类型>\n"
            msg += "示例: 购买影厅 small"
            yield event.plain_result(msg)
            return
        theater_type = parts[1]
        try:
            result = self.cinema.buy_theater(event.get_sender_id(), theater_type)
            msg = f"✅ 成功购买{result['type_name']}！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🆔 影厅: {result['theater_name']}\n"
            msg += f"💺 座位: {result['capacity']}座\n"
            msg += f"💰 花费: {result['cost']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 购买失败: {e}')

    @filter.command("升级影厅")
    async def cmd_upgrade_theater(self, event: AstrMessageEvent):
        """升级影厅"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: 升级影厅 <影厅名/ID>")
            return
        theater_id = parts[1]
        try:
            result = self.cinema.upgrade_theater(event.get_sender_id(), theater_id)
            msg = f"✅ 影厅升级成功！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🎭 影厅: {result['theater_name']}\n"
            msg += f"📊 {result['old_type']} → {result['new_type']}\n"
            msg += f"💺 新座位数: {result['new_capacity']}座\n"
            msg += f"💰 花费: {result['cost']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 升级失败: {e}')

    @filter.command("电影列表")
    async def cmd_movie_list(self, event: AstrMessageEvent):
        """查看可购买的电影列表"""
        movies = self.cinema.get_movie_list()
        msg = "🎬 可购买的电影版权:\n"
        msg += "━━━━━━━━━━━━━━\n"
        for genre_name, info in movies.items():
            msg += f"📁 {genre_name} (版权费{info['cost']}元)\n"
            for m in info['movies']:
                msg += f"   🎬 《{m['title']}》 ⭐{m['rating']} 人气{m['popularity']}\n"
        msg += "━━━━━━━━━━━━━━\n"
        msg += "用法: 购买电影 <电影名>"
        yield event.plain_result(msg)

    @filter.command("购买电影")
    async def cmd_buy_movie(self, event: AstrMessageEvent):
        """购买电影版权"""
        parts = event.text.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("用法: 购买电影 <电影名>\n使用【电影列表】查看可购买的电影")
            return
        movie_title = parts[1]
        try:
            result = self.cinema.buy_movie(event.get_sender_id(), movie_title)
            msg = f"✅ 成功购买电影版权！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🎬 《{result['title']}》\n"
            msg += f"📁 类型: {result['genre']}\n"
            msg += f"⏱️ 时长: {result['duration']}分钟\n"
            msg += f"💵 票价: {result['base_price']}元\n"
            msg += f"⭐ 评分: {result['rating']}\n"
            msg += f"📈 人气: {result['popularity']}\n"
            msg += f"💰 花费: {result['cost']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 购买失败: {e}')

    @filter.command("排片")
    async def cmd_schedule_movie(self, event: AstrMessageEvent):
        """排片"""
        parts = event.text.strip().split()
        if len(parts) < 4:
            yield event.plain_result("用法: 排片 <影厅名> <电影名> <时间>\n示例: 排片 小型影厅1 星际穿越 14:30")
            return
        theater_id = parts[1]
        movie_title = parts[2]
        time = parts[3]
        try:
            result = self.cinema.schedule_movie(event.get_sender_id(), theater_id, movie_title, time)
            msg = f"✅ 排片成功！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🎭 影厅: {result['theater_name']}\n"
            msg += f"🎬 电影: 《{result['movie_title']}》\n"
            msg += f"⏰ 时间: {result['time']}\n"
            msg += f"⏱️ 时长: {result['duration']}分钟\n"
            msg += f"💵 票价: {result['price']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 排片失败: {e}')

    @filter.command("购买电影院设施")
    async def cmd_buy_cinema_facility(self, event: AstrMessageEvent):
        """购买电影院设施"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            types = self.cinema.get_facility_types()
            msg = "🏠 可购买的设施:\n"
            msg += "━━━━━━━━━━━━━━\n"
            for t in types:
                msg += f"📦 {t['type']} - {t['name']}\n"
                msg += f"   💰 价格: {t['cost']}元\n"
                msg += f"   📈 收入加成: ×{t['revenue_multiplier']}\n"
                msg += f"   💡 {t['description']}\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "用法: 购买电影院设施 <类型>"
            yield event.plain_result(msg)
            return
        facility_type = parts[1]
        try:
            result = self.cinema.buy_facility(event.get_sender_id(), facility_type)
            msg = f"✅ 成功购买{result['name']}！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💰 花费: {result['cost']}元\n"
            msg += f"📈 收入加成: ×{result['revenue_multiplier']}\n"
            msg += f"💡 {result['description']}"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 购买失败: {e}')

    @filter.command("雇佣电影院员工")
    async def cmd_hire_cinema_staff(self, event: AstrMessageEvent):
        """雇佣电影院员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            types = self.cinema.get_staff_types()
            msg = "👥 可雇佣的员工类型:\n"
            msg += "━━━━━━━━━━━━━━\n"
            for t in types:
                msg += f"👤 {t['type']} - {t['name']}\n"
                msg += f"   💰 月薪: {t['salary']}元\n"
                msg += f"   ⚡ 效率: {t['efficiency']}\n"
                msg += f"   💡 {t['description']}\n"
            msg += "━━━━━━━━━━━━━━\n"
            msg += "用法: 雇佣电影院员工 <类型>"
            yield event.plain_result(msg)
            return
        staff_type = parts[1]
        try:
            result = self.cinema.hire_staff(event.get_sender_id(), staff_type)
            msg = f"✅ 成功雇佣{result['type_name']}！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"🆔 员工: {result['name']}\n"
            msg += f"💰 首月工资: {result['salary']}元\n"
            msg += f"⚡ 效率: {result['efficiency']}\n"
            msg += f"💡 {result['description']}"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 雇佣失败: {e}')

    @filter.command("培训电影院员工")
    async def cmd_train_cinema_staff(self, event: AstrMessageEvent):
        """培训电影院员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: 培训电影院员工 <员工名/ID>")
            return
        staff_id = parts[1]
        try:
            result = self.cinema.train_staff(event.get_sender_id(), staff_id)
            msg = f"✅ 员工培训完成！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"👤 员工: {result['staff_name']}\n"
            msg += f"📊 等级: {result['old_level']} → {result['new_level']}\n"
            msg += f"⚡ 新效率: {result['new_efficiency']:.2f}\n"
            msg += f"💰 培训费: {result['cost']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 培训失败: {e}')

    @filter.command("解雇电影院员工")
    async def cmd_fire_cinema_staff(self, event: AstrMessageEvent):
        """解雇电影院员工"""
        parts = event.text.strip().split()
        if len(parts) < 2:
            try:
                cinema = self.cinema.get_cinema_info(event.get_sender_id())
                staff_list = cinema.get('staff', []) if isinstance(cinema, dict) else getattr(cinema, 'staff', [])
                if not staff_list:
                    yield event.plain_result("当前没有员工可解雇。")
                    return
                msg = "👥【电影院员工列表】\n"
                msg += "━━━━━━━━━━━━━━━━\n"
                for staff in staff_list:
                    s_name = staff.get('name') if isinstance(staff, dict) else getattr(staff, 'name', 'N/A')
                    s_type = staff.get('type') if isinstance(staff, dict) else getattr(staff, 'type', 'N/A')
                    s_sal = staff.get('salary') if isinstance(staff, dict) else getattr(staff, 'salary', 0)
                    msg += f"👤 {s_name} ({s_type})\n"
                    msg += f"   💰 月薪: {s_sal}元\n"
                msg += "━━━━━━━━━━━━━━━━\n"
                msg += "用法: #解雇电影院员工 <员工名>"
                yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f'❌ 获取员工列表失败: {e}')
            return
        staff_name = parts[1]
        try:
            result = self.cinema.fire_staff(event.get_sender_id(), staff_name)
            msg = f"✅ 已解雇员工！\n"
            msg += f"━━━━━━━━━━━━━━━━\n"
            msg += f"👤 员工: {result.get('staff_name', '未知员工')}\n"
            msg += f"💼 职位: {result.get('staff_type', 'N/A')}\n"
            msg += f"📅 服务天数: {result.get('service_days', 0)}天\n"
            msg += f"💰 遣散费: {result.get('severance', 0)}元\n"
            msg += f"📈 获得经验: {result.get('experience_gained', 0)}"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 解雇失败: {e}')

    @filter.command("收取电影院收入")
    async def cmd_collect_cinema_revenue(self, event: AstrMessageEvent):
        """收取电影院收入"""
        try:
            result = self.cinema.collect_revenue(event.get_sender_id())
            msg = f"💰 收入收取成功！\n"
            msg += f"━━━━━━━━━━━━━━\n"
            msg += f"💵 收取金额: {result['collected']}元"
            yield event.plain_result(msg)
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ {e}')

    @filter.command("电影院排行榜")
    async def cmd_cinema_ranking(self, event: AstrMessageEvent):
        """电影院排行榜"""
        parts = event.text.strip().split()
        sort_by = "reputation" if len(parts) > 1 and parts[1] == "声誉" else "revenue"

        try:
            ranking = self.cinema.get_cinema_ranking(sort_by)
            if not ranking:
                yield event.plain_result("暂无排行数据")
                return

            sort_name = "声誉" if sort_by == "reputation" else "收入"
            msg = f"🏆 电影院排行榜 (按{sort_name}排序)\n"
            msg += "━━━━━━━━━━━━━━\n"
            for i, entry in enumerate(ranking[:10], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                msg += f"{medal} {entry.cinema_name}\n"
                msg += f"   👤 {entry.owner_name}\n"
                msg += f"   💰 收入{entry.total_revenue}元 | ⭐{entry.reputation}\n"
                msg += f"   🎭 {entry.theater_count}厅 | 🎬 {entry.movie_count}部\n"
            yield event.plain_result(msg)
        except Exception as e:
            yield event.plain_result(f'❌ {e}')

    @filter.command("创建电影院")
    async def cmd_create_cinema_old(self, event: AstrMessageEvent):
        """创建电影院(兼容旧指令)"""
        parts = event.text.strip().split(maxsplit=1)
        name = parts[1] if len(parts) > 1 else None
        try:
            cinema = self.cinema.buy_cinema(event.get_sender_id(), name)
            yield event.plain_result(f"🎬 电影院【{cinema.name}】创建成功！\n使用【电影院信息】查看详情")
        except Exception as e:
            if str(e).startswith('cooldown:'):
                yield event.plain_result('操作太快，请稍后再试。')
            else:
                yield event.plain_result(f'❌ 创建失败: {e}')

    # ==================== 天气系统 ====================
    @filter.command("查看天气")
    async def cmd_check_weather(self, event: AstrMessageEvent):
        state = self.weather.get_current_weather()
        msg = f"🌤️【当前天气】\n"
        msg += f"日期: {state.date_str}\n"
        msg += f"天气: {state.weather}\n"
        msg += f"气温: {state.temperature}℃"
        yield event.plain_result(msg)

    @filter.command("更新天气")
    async def cmd_update_weather(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        if not self.config_manager.is_admin(user_id):
            yield event.plain_result("🚫 只有管理员可以使用此命令。")
            return
        state = self.weather.update_weather()
        yield event.plain_result(f"✅ 天气已更新为: {state.date_str} {state.weather}")

    # ==================== 宠物系统 ====================
    @filter.command("宠物抽卡")
    async def cmd_pet_draw(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        user = await self._load_user(user_id)
        if user.get('money', 0) < 1000:
            yield event.plain_result("🚫 每次抽卡需要1000金币！")
            return

        user['money'] -= 1000
        await self._save_user(user_id, user)

        pet = self.pet.draw_pet(user_id)
        # Render image
        img = self.pet_renderer.render_draw(pet)
        # Convert HTML to image
        from .core.common.screenshot import html_to_image_bytes
        img_bytes = await html_to_image_bytes(img, width=600, height=800, base_path=self.template.template_dir)

        if img_bytes:
            import tempfile, os
            fd, path = tempfile.mkstemp(suffix=".png")
            try:
                with os.fdopen(fd, 'wb') as tmp:
                    tmp.write(img_bytes)
                yield event.image_result(path)
            finally:
                pass
        else:
            yield event.plain_result(f"恭喜获得: {pet.name} ({pet.rarity})")

    @filter.command("我的宠物")
    async def cmd_my_pets(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        pets = self.pet.get_user_pets(user_id)
        if not pets:
            yield event.plain_result("你还没有宠物哦，快去 #宠物抽卡 吧！")
            return

        img = self.pet_renderer.render_my_pets(pets)
        from .core.common.screenshot import html_to_image_bytes
        img_bytes = await html_to_image_bytes(img, width=800, height=1000, base_path=self.template.template_dir)

        if img_bytes:
            import tempfile, os
            fd, path = tempfile.mkstemp(suffix=".png")
            try:
                with os.fdopen(fd, 'wb') as tmp:
                    tmp.write(img_bytes)
                yield event.image_result(path)
            finally:
                pass
        else:
            msg = "🐾【我的宠物】\n"
            for p in pets:
                msg += f"{p.name} (Lv.{p.level})\n"
            yield event.plain_result(msg)

    @filter.command("喂养宠物")
    async def cmd_feed_pet(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: 喂养宠物 <宠物ID>")
            return
        pet = self.pet.feed_pet(parts[1])
        if pet:
            yield event.plain_result(f"🍖 喂养成功！{pet.name} 看起来很开心。\n饱食度: {pet.hunger} | 心情: {pet.mood}")
        else:
            yield event.plain_result("未找到该宠物。")

    # ==================== 关系系统 ====================
    @filter.command("赠送礼物")
    async def cmd_gift_relationship(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 3:
            yield event.plain_result("用法: 赠送礼物 <目标QQ> <花费金额>")
            return
        target_id = parts[1]
        try:
            amount = int(parts[2])
        except:
            yield event.plain_result("金额必须是整数")
            return

        user_id = event.get_sender_id()
        user = await self._load_user(user_id)
        if user.get('money', 0) < amount:
            yield event.plain_result("金币不足！")
            return

        user['money'] -= amount
        await self._save_user(user_id, user)

        # Get target name
        target_data = await self.data_manager.async_load_user(target_id)
        target_name = target_data.get('name', target_id) if target_data else target_id

        rel = self.relationship.add_affection(user_id, target_id, target_name, amount // 100)  # 100 gold = 1 affection
        yield event.plain_result(f"🎁 赠送成功！你们的关系提升了。\n当前好感度: {rel.affection} ({rel.status})")

    @filter.command("查看关系")
    async def cmd_view_relationship(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: 查看关系 <目标QQ>")
            return
        target_id = parts[1]
        user_id = event.get_sender_id()

        rel = self.relationship.get_relationship(user_id, target_id)
        if not rel:
            yield event.plain_result("你们还不够熟悉哦。(无关系数据)")
            return

        img = self.relationship_renderer.render_status(rel)
        from .core.common.screenshot import html_to_image_bytes
        img_bytes = await html_to_image_bytes(img, width=600, height=800, base_path=self.template.template_dir)

        if img_bytes:
            import tempfile, os
            fd, path = tempfile.mkstemp(suffix=".png")
            try:
                with os.fdopen(fd, 'wb') as tmp:
                    tmp.write(img_bytes)
                yield event.image_result(path)
            finally:
                pass
        else:
            yield event.plain_result(f"💝 {rel.target_name}\n好感度: {rel.affection}\n状态: {rel.status}")

    @filter.command("求婚")
    async def cmd_propose(self, event: AstrMessageEvent):
        parts = event.text.strip().split()
        if len(parts) < 2:
            yield event.plain_result("用法: 求婚 <目标QQ>")
            return
        target_id = parts[1]
        user_id = event.get_sender_id()

        can_marry, rel = self.relationship.check_marriage(user_id, target_id)
        if not can_marry:
            if not rel:
                yield event.plain_result("你们还不认识呢！")
            elif rel.status == "married":
                yield event.plain_result("你们已经结婚了！")
            else:
                yield event.plain_result(f"感情还不够深厚哦 (需要500好感度，当前{rel.affection})")
            return

        res = self.relationship.marry(user_id, target_id)
        yield event.plain_result(f"💍 恭喜！你和 {res.target_name} 结婚了！祝你们百年好合。")
