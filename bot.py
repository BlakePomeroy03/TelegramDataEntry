import os
import asyncio
import gspread_asyncio
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

ALLOWED_USER_IDS = [int(uid.strip()) for uid in os.getenv('ALLOWED_IDS').split(',')]

active_sessions = {}

def get_creds():
    return Credentials.from_service_account_file("credentials.json").with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets"
    ])

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

async def s_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id not in ALLOWED_USER_IDS:
        return
        
    current_time = datetime.now().strftime("%H:%M")
    active_sessions[user_id] = current_time
    
    await update.message.reply_text(f"Clocked in at {current_time}.")

async def format_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Manual: /log Casino, Start, End, EV, AV\nAuto: /log Casino, EV, AV")

async def log_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("You're not on the team list.")
        return
        
    raw_text = update.message.text.replace('/log ', '', 1).strip()
    parts = [p.strip() for p in raw_text.split(',')]
    
    if len(parts) == 3:
        if user_id not in active_sessions:
            await update.message.reply_text("You didn't use /s to clock in. Use the full format.")
            return
            
        casino, ev_str, av_str = parts
        start = active_sessions.pop(user_id)
        end = datetime.now().strftime("%H:%M")
        
    elif len(parts) == 5:
        casino, start, end, ev_str, av_str = parts
        if user_id in active_sessions:
            del active_sessions[user_id]
            
    else:
        await update.message.reply_text("Format looks off. Send /format to see how it works.")
        return
    
    try:
        ev = float(ev_str)
        av = float(av_str)
    except ValueError:
        await update.message.reply_text("Make sure EV and AV are just numbers, no dollar signs.")
        return
        
    row_data = [user_name, casino, start, end, ev, av]
    
    try:
        agc = await agcm.authorize()
        sheet = await agc.open_by_key(SPREADSHEET_ID)
        worksheet = await sheet.get_worksheet(0)
        
        await worksheet.append_row(row_data)
        
        await update.message.reply_text(f"Got it, {user_name}. Session logged.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"Something went wrong with the database: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("s", s_command))
    app.add_handler(CommandHandler("log", log_session))
    app.add_handler(CommandHandler("format", format_command))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == '__main__':
    main()