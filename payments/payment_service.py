from aiocryptopay import AioCryptoPay, Networks
import asyncio
import logging
from config import settings

logger = logging.getLogger(__name__)

# Инициализация клиента CryptoBot API с явным указанием токена
# Важно: замените токен на ваш токен от CryptoBot
CRYPTOBOT_TOKEN = "токен"  # Замените на свой токен
logger.info(f"Инициализация CryptoBot API с токеном: {CRYPTOBOT_TOKEN[:10]}...")

try:
    cryptopay = AioCryptoPay(
        token=CRYPTOBOT_TOKEN,
        network=Networks.MAIN_NET
    )
    logger.info("CryptoBot API клиент успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка при инициализации CryptoBot API: {e}")
    # Создаем заглушку чтобы код не падал
    cryptopay = None

# Таблица соответствия уровней подписки и цен
SUBSCRIPTION_PRICES = {
    1: 10,  # Расширенный - 10 USDT
    2: 20,  # Премиум - 20 USDT
    3: 1   # Полный - 50 USDT
}

# Множество для отслеживания обработанных платежей (по update_id)
processed_updates = set()

# Множество для отслеживания обработанных инвойсов (по invoice_id)
processed_invoices = set()

# Блокировка для синхронизации обработки платежей
processing_lock = asyncio.Lock()

async def create_payment_invoice(user_id: int, level: int) -> dict:
    """
    Создает счет на оплату в CryptoBot
    
    :param user_id: ID пользователя
    :param level: Уровень подписки (1, 2 или 3)
    :return: Объект счета с URL для оплаты
    """
    amount = SUBSCRIPTION_PRICES.get(level)
    if not amount:
        logger.error(f"Неверный уровень подписки: {level}")
        raise ValueError(f"Неверный уровень подписки: {level}")
    
    # Проверка инициализации API клиента
    if cryptopay is None:
        logger.error("CryptoBot API клиент не инициализирован")
        raise RuntimeError("CryptoBot API не инициализирован")
    
    try:
        # Логируем параметры запроса
        logger.info(f"Создание счета: user_id={user_id}, level={level}, amount={amount}")
        
        # Создаем счет через CryptoBot API
        invoice = await cryptopay.create_invoice(
            amount=amount,
            description=f"Подписка уровня {level}",
            currency_type="fiat", 
            fiat="USD",
            accepted_assets="USDT",
            payload=f"{user_id}:{level}"
        )
        
        logger.info(f"Счет успешно создан: invoice_id={invoice.invoice_id}")
        
        # Важно! Используем правильный формат deep link для CryptoBot
        # Проверяем наличие атрибута bot_invoice_url или pay_url
        if hasattr(invoice, 'bot_invoice_url') and invoice.bot_invoice_url:
            payment_url = invoice.bot_invoice_url
            logger.info(f"Используем bot_invoice_url: {payment_url}")
        else:
            # Если bot_invoice_url недоступен, формируем ссылку вручную
            payment_url = f"https://t.me/CryptoBot?start=invoice_{invoice.invoice_id}"
            logger.info(f"Сформирована ссылка на оплату вручную: {payment_url}")
        
        # Запускаем процесс проверки оплаты в фоновом режиме
        asyncio.create_task(check_payment(invoice.invoice_id, user_id, level))
        
        return {
            "invoice_id": invoice.invoice_id,
            "payment_url": payment_url,
            "amount": amount,
            "level": level
        }
    except Exception as e:
        # Подробное логирование ошибки
        logger.error(f"Ошибка при создании счета: {e}", exc_info=True)
        raise

async def check_payment(invoice_id: str, user_id: int, level: int):
    """
    Проверяет статус платежа в фоновом режиме
    
    :param invoice_id: ID счета
    :param user_id: ID пользователя
    :param level: Уровень подписки
    """
    logger.info(f"Начата проверка оплаты для invoice_id: {invoice_id}")
    
    if cryptopay is None:
        logger.error("CryptoBot API клиент не инициализирован, проверка оплаты невозможна")
        return
    
    # Проверяем статус платежа каждые 30 секунд в течение 15 минут
    for i in range(30):  # 30 проверок * 30 секунд = 15 минут
        try:
            logger.info(f"Проверка {i+1}/30 для invoice_id: {invoice_id}")
            
            # Проверяем, не обработан ли уже этот счет
            async with processing_lock:
                if invoice_id in processed_invoices:
                    logger.info(f"Счет уже был обработан ранее через вебхук: {invoice_id}")
                    break
            
            # Используем get_invoices вместо get_invoice (правильный метод API)
            invoices = await cryptopay.get_invoices(invoice_ids=[invoice_id])
            
            if not invoices:
                logger.warning(f"Счет {invoice_id} не найден")
                await asyncio.sleep(30)
                continue
                
            # Получаем первый (и единственный) счет из списка
            invoice = invoices[0]
            logger.info(f"Статус счета {invoice_id}: {invoice.status}")
            
            if invoice.status == 'paid':
                logger.info(f"Платеж подтвержден для invoice_id: {invoice_id}")
                
                # Обрабатываем платеж с блокировкой для избежания гонки условий
                async with processing_lock:
                    # Проверяем еще раз внутри блокировки
                    if invoice_id in processed_invoices:
                        logger.info(f"Счет уже был обработан во время ожидания блокировки: {invoice_id}")
                        break
                    
                    # Отмечаем счет как обработанный
                    processed_invoices.add(invoice_id)
                    logger.info(f"Счет {invoice_id} добавлен в обработанные")
                    
                    # Обновляем подписку пользователя
                    await change_user_subscription(user_id, level)
                    
                    # Отправляем уведомление пользователю
                    from aiogram import Bot
                    try:
                        bot = Bot(token=settings.BOT_TOKEN)
                        level_name = settings.SUBSCRIPTION_LEVELS_NAMES.get(level, f"Уровень {level}")
                        
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"✅ <b>Платеж успешно получен!</b>\n\n"
                                f"💳 Подписка '{level_name}' активирована.\n"
                                f"Спасибо за поддержку нашего проекта!",
                            parse_mode="HTML"
                        )
                        
                        await bot.session.close()
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления: {e}")
                    
                    logger.info(f"Подписка обновлена для пользователя {user_id} до уровня {level}")
                    
                # Платеж обработан, выходим из цикла проверок
                break
            
            # Если счет отменен или истек срок
            if invoice.status in ['expired', 'cancelled']:
                logger.info(f"Платеж отменен или истек для invoice_id: {invoice_id}")
                break
                
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса платежа: {e}", exc_info=True)
        
        # Ждем 30 секунд перед следующей проверкой
        await asyncio.sleep(30)

async def register_payment(update_id: int, invoice_id: str, amount: float, user_id: int, level: int):
    """
    Регистрирует платеж и обновляет подписку пользователя
    
    :param update_id: ID обновления от CryptoBot
    :param invoice_id: ID счета
    :param amount: Сумма платежа
    :param user_id: ID пользователя
    :param level: Уровень подписки
    :return: True если платеж успешно зарегистрирован
    """
    logger.info(f"Регистрация платежа: update_id={update_id}, invoice_id={invoice_id}, user_id={user_id}, level={level}")
    
    # Проверяем с использованием блокировки для избежания гонки условий
    async with processing_lock:
        # Проверяем, не обработано ли уже это обновление
        if update_id in processed_updates:
            logger.info(f"Обновление уже было обработано ранее: {update_id}")
            return True
            
        # Проверяем, не обработан ли уже этот счет
        if invoice_id in processed_invoices:
            logger.info(f"Счет уже был обработан ранее: {invoice_id}")
            return True
        
        # Отмечаем обновление и счет как обработанные
        processed_updates.add(update_id)
        processed_invoices.add(invoice_id)
        logger.info(f"Обновление {update_id} и счет {invoice_id} добавлены в обработанные")
    
    try:        
        # Обновляем подписку пользователя
        await change_user_subscription(user_id, level)
        
        # Отправляем уведомление пользователю
        from aiogram import Bot
        try:
            bot = Bot(token=settings.BOT_TOKEN)
            level_name = settings.SUBSCRIPTION_LEVELS_NAMES.get(level, f"Уровень {level}")
            
            await bot.send_message(
                chat_id=user_id,
                text=f"✅ <b>Платеж успешно получен!</b>\n\n"
                     f"💳 Подписка '{level_name}' активирована.\n"
                     f"Спасибо за поддержку нашего проекта!",
                parse_mode="HTML"
            )
            
            await bot.session.close()
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
        
        logger.info(f"Платеж успешно зарегистрирован: update_id={update_id}, invoice_id={invoice_id}, user_id={user_id}, level={level}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации платежа: {e}", exc_info=True)
        return False

# Эти функции нужны для совместимости с bot.py
async def setup_cryptobot_webhook(webhook_url: str) -> bool:
    """
    Настраивает URL для вебхуков CryptoBot
    """
    # Здесь можно добавить код для настройки вебхука в CryptoBot API, если такой метод будет доступен
    # В текущей версии API такого метода нет, поэтому мы просто логируем
    logger.info(f"URL для вебхуков CryptoBot установлен: {webhook_url}/cryptobot-webhook")
    return True

async def remove_cryptobot_webhook() -> bool:
    """
    Удаляет URL для вебхуков CryptoBot
    """
    # Здесь можно добавить код для удаления вебхука в CryptoBot API, если такой метод будет доступен
    logger.info("URL для вебхуков CryptoBot удален")
    return True