import telebot
import gspread
from google.oauth2.service_account import Credentials
import datetime
import schedule
import threading
import time
import os

# Ключи из переменных окружения (БЕЗОПАСНО)
BOT_TOKEN = os.getenv('BOT_TOKEN')
SHEET_ID = os.getenv('SHEET_ID')
CHAT_ID = int(os.getenv('CHAT_ID'))

bot = telebot.TeleBot(BOT_TOKEN)

SOURCES = {
    'avito_ads': 'Avito Ads',
    'avito ads': 'Avito Ads',
    'avito': 'Avito',
    'yandex': 'Yandex.Direct',
    'vk': 'VK Ads',
}

try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    gc = gspread.service_account(filename='credentials.json')
    wb = gc.open_by_key(SHEET_ID)
    sheet_leads = wb.worksheet('leads')
    sheet_budget = wb.worksheet('budget')
    print("OK Google Sheets")
except Exception as e:
    print(f"Error: {e}")
    sheet_leads = None
    sheet_budget = None

def get_source_from_text(text):
    text_lower = text.lower()
    for keyword, source in SOURCES.items():
        if keyword in text_lower:
            return source
    return 'Avito'

def get_budget_for_period(source, start_date, end_date):
    if not sheet_budget:
        return 0
    try:
        all_rows = sheet_budget.get_all_values()
        total = 0
        for row in all_rows[1:]:
            if len(row) >= 3:
                date_str = row[0]
                source_name = row[1]
                try:
                    budget = float(row[2]) if row[2] else 0
                except:
                    budget = 0
                try:
                    row_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    if start_date <= row_date <= end_date and source_name == source:
                        total += budget
                except:
                    pass
        return total
    except:
        return 0

def get_leads_for_period(source, start_date, end_date):
    if not sheet_leads:
        return 0
    try:
        all_rows = sheet_leads.get_all_values()
        total = 0
        for row in all_rows[1:]:
            if len(row) >= 3:
                date_str = row[0]
                source_name = row[1]
                try:
                    leads = int(row[2]) if row[2] else 0
                except:
                    leads = 0
                try:
                    row_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    if start_date <= row_date <= end_date and source_name == source:
                        total += leads
                except:
                    pass
        return total
    except:
        return 0

def build_report(start_date, end_date):
    report = f"Stats {start_date} to {end_date}\n\n"
    total_leads = 0
    total_budget = 0
    sources_list = ['Avito', 'Avito Ads', 'Yandex.Direct', 'VK Ads']
    for source in sources_list:
        leads = get_leads_for_period(source, start_date, end_date)
        budget = get_budget_for_period(source, start_date, end_date)
        cpa = budget / leads if leads > 0 else 0
        total_leads += leads
        total_budget += budget
        if leads > 0 or budget > 0:
            report += f"{source}: {leads} leads, {budget:,} rub, CPA {cpa:.0f}\n"
    total_cpa = total_budget / total_leads if total_leads > 0 else 0
    report += f"\nTOTAL: {total_leads} leads, {total_budget:,} rub, CPA {total_cpa:.0f}"
    return report

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message.chat.id, "Bot running!")

@bot.message_handler(commands=['stats_week'])
def stats_week(message):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=7)
    bot.reply_to(message.chat.id, build_report(start_date, end_date))

@bot.message_handler(commands=['stats'])
def stats_custom(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message.chat.id, "Use: /stats 2025-11-01 2025-11-30")
            return
        start_date = datetime.datetime.strptime(args[1], '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(args[2], '%Y-%m-%d').date()
        bot.reply_to(message.chat.id, build_report(start_date, end_date))
    except:
        bot.reply_to(message.chat.id, "Error!")

@bot.message_handler(func=lambda m: any(word in m.text.lower() for word in ['lead', 'cottage', 'house']))
def catch_lead(message):
    source = get_source_from_text(message.text)
    today = datetime.date.today()
    if sheet_leads:
        try:
            sheet_leads.append_row([today.strftime('%Y-%m-%d'), source, 1])
        except:
            pass
    bot.reply_to(message.chat.id, f"Lead recorded: {source}")

print("Bot started")
bot.polling(none_stop=True)
