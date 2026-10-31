# Deal Alert Telegram Bot
1. `pip install -r requirements.txt` then `playwright install chromium`
2. Edit `config.py`: BOT_TOKEN (or env var), CHANNELS (numeric IDs), ADDRESS.
3. Test a source first: `python debug_fetch.py flipkart`
4. Run: `python main.py`, then send /start in each channel.
