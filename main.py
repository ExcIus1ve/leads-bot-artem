import telebot
import gspread
import json
import os
import datetime
import schedule
import threading
import time
from datetime import timedelta

# Ключи из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
SHEET_ID = os.getenv('SHEET_ID')
CHAT_ID = int(os.getenv('CHAT_ID', '0'))
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')

bot = telebot.TeleBot(BOT_TOKEN)

# Источники
SOURCES = ['Avito Ads', 'Яндекс.Директ', 'VK Реклама']

# Инициализация Google Sheets
try:
    if GOOGLE_CREDENTIALS_JSON:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        gc = gspread.service_account_from_dict(creds_dict)
    else:
        gc = gspread.service_account(filename='credentials.json')
    
    workbook = gc.open_by_key(SHEET_ID)
    leads_sheet = workbook.worksheet('leads')
    budget_sheet = workbook.worksheet('budget')
    print("✅ Google Sheets подключен")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    leads_sheet = None
    budget_sheet = None

def build_report(start_date, end_date):
    """Собирает отчёт за период"""
    if not leads_sheet or not budget_sheet:
        return "❌ Google Sheets не подключен"
    
    try:
        leads_rows = leads_sheet.get_all_records()
        budget_rows = budget_sheet.get_all_records()
        
        stats = {source: {'leads': 0, 'budget': 0} for source in SOURCES}
        
        for row in leads_rows:
            try:
                row_date = datetime.datetime.strptime(row['Дата'], '%Y-%m-%d').date()
                if start_date <= row_date <= end_date:
                    source = row['Источник']
                    if source in stats:
                        stats[source]['leads'] += int(row.get('Лидов', 0) or 0)
            except:
                continue
        
        for row in budget_rows:
            try:
                row_date = datetime.datetime.strptime(row['Дата'], '%Y-%m-%d').date()
                if start_date <= row_date <= end_date:
                    source = row['Источник']
                    if source in stats:
                        stats[source]['budget'] += float(row.get('Бюджет ₽', 0) or 0)
            except:
                continue
        
        report = f"📊 Отчёт за период {start_date} — {end_date}\n\n"
        total_leads = 0
        total_budget = 0
        
        for source in SOURCES:
            leads = stats[source]['leads']
            budget = stats[source]['budget']
            cpa = budget / leads if leads > 0 else 0
            total_leads += leads
            total_budget += budget
            report += f"<b>{source}</b>\nЛидов: {leads}\nСтоимость лида: {cpa:.0f} ₽\n\n"
        
        total_cpa = total_budget / total_leads if total_leads > 0 else 0
        report += f"<b>Общая статистика</b>\nЛидов: {total_leads}\nСтоимость лида: {total_cpa:.0f} ₽\nПотрачено: {total_budget:,.0f} ₽"
        return report
    except Exception as e:
        return f"❌ Ошибка: {e}"

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    args = message.text.split()
    if len(args) == 3:
        try:
            start_date = datetime.datetime.strptime(args[1], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(args[2], '%Y-%m-%d').date()
            report = build_report(start_date, end_date)
            bot.send_message(message.chat.id, report, parse_mode='HTML')
        except:
            bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: /stats 2025-11-01 2025-11-30")
    else:
        bot.send_message(message.chat.id, "📊 Формат: /stats 2025-11-01 2025-11-30")

@bot.message_handler(commands=['stats_week'])
def handle_stats_week(message):
    today = datetime.date.today()
    start_date = today - timedelta(days=7)
    report = build_report(start_date, today)
    bot.send_message(message.chat.id, report, parse_mode='HTML')

@bot.message_handler(commands=['stats_month'])
def handle_stats_month(message):
    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    report = build_report(first_day_prev_month, last_day_prev_month)
    bot.send_message(message.chat.id, report, parse_mode='HTML')

@bot.message_handler(func=lambda m: any(word in m.text.lower() for word in ['заявка', 'коттедж', 'дом', 'построить', 'смета', 'проект']))
def catch_lead(message):
    if not leads_sheet:
        bot.reply_to(message, "❌ Google Sheets не подключен")
        return
    
    source = 'Avito Ads'
    if 'yandex' in message.text.lower() or 'директ' in message.text.lower():
        source = 'Яндекс.Директ'
    elif 'vk' in message.text.lower() or 'вк' in message.text.lower():
        source = 'VK Реклама'
    
    try:
        today = datetime.date.today().isoformat()
        leads_sheet.append_row([today, source, 1])
        bot.reply_to(message, f"✅ Лид зафиксирован из {source}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def send_weekly_report():
    """Еженедельный отчёт"""
    today = datetime.date.today()
    start_date = today - timedelta(days=7)
    report = build_report(start_date, today)
    try:
        bot.send_message(CHAT_ID, report, parse_mode='HTML')
        print(f"✅ Еженедельный отчёт отправлен {today}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def send_monthly_report():
    """Ежемесячный отчёт"""
    today = datetime.date.today()
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    report = build_report(first_day_prev_month, last_day_prev_month)
    try:
        bot.send_message(CHAT_ID, report, parse_mode='HTML')
        print(f"✅ Ежемесячный отчёт отправлен {today}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def schedule_jobs():
    """Планировщик"""
    schedule.every().monday.at("10:00").do(send_weekly_report)
    schedule.every().day.at("10:00").do(lambda: send_monthly_report() if datetime.date.today().day == 1 else None)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    scheduler_thread = threading.Thread(target=schedule_jobs, daemon=True)
    scheduler_thread.start()
    
    print("🚀 Бот запущен!")
    print("💬 Команды:")
    print(" /stats 2025-11-01 2025-11-30")
    print(" /stats_week")
    print(" /stats_month")
    
    bot.polling(none_stop=True)
