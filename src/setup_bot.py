"""
Bot description setup - run once to set bot description in Telegram.
"""
import asyncio
from telegram import Bot
from config import config


DESCRIPTION_AR = """🎓 مركز التدريب

منصة متكاملة لإدارة الدورات التدريبية

✨ الميزات:
• عرض الدورات المتاحة
• التسجيل في الدورات
• الوصول لمواد التعلم
• دعم العربية والإنجليزية

📱 سهل الاستخدام عبر الأزرار"""

DESCRIPTION_EN = """🎓 Training Center

Integrated platform for training course management

✨ Features:
• View available courses
• Register for courses
• Access learning materials
• Arabic & English support

📱 Easy button-based navigation"""

SHORT_DESCRIPTION_AR = "منصة إدارة الدورات التدريبية 🎓"
SHORT_DESCRIPTION_EN = "Training Course Management Platform 🎓"


async def setup_bot_description():
    """Set up bot description in Telegram."""
    if not config.telegram.bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return
    
    bot = Bot(token=config.telegram.bot_token)
    
    try:
        # Set Arabic description (default)
        await bot.set_my_description(
            description=DESCRIPTION_AR,
            language_code="ar"
        )
        print("✅ Arabic description set")
        
        # Set English description
        await bot.set_my_description(
            description=DESCRIPTION_EN,
            language_code="en"
        )
        print("✅ English description set")
        
        # Set default description (Arabic)
        await bot.set_my_description(
            description=DESCRIPTION_AR
        )
        print("✅ Default description set")
        
        # Set short descriptions
        await bot.set_my_short_description(
            short_description=SHORT_DESCRIPTION_AR,
            language_code="ar"
        )
        await bot.set_my_short_description(
            short_description=SHORT_DESCRIPTION_EN,
            language_code="en"
        )
        await bot.set_my_short_description(
            short_description=SHORT_DESCRIPTION_AR
        )
        print("✅ Short descriptions set")
        
        # Set commands
        from telegram import BotCommand
        
        commands_ar = [
            BotCommand("start", "القائمة الرئيسية 🏠"),
        ]
        
        commands_en = [
            BotCommand("start", "Main Menu 🏠"),
        ]
        
        await bot.set_my_commands(commands_ar, language_code="ar")
        await bot.set_my_commands(commands_en, language_code="en")
        await bot.set_my_commands(commands_ar)
        print("✅ Commands set")
        
        print("\n🎉 Bot setup complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(setup_bot_description())
