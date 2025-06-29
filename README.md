# 🌐 Link Grabber Bot 🤖
_A Telegram bot to scrape and filter links from URLs or text files with powerful keyword filtering_

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python) 
![Platform](https://img.shields.io/badge/Platform-Telegram-blue?logo=telegram) 
![Author](https://img.shields.io/badge/Author-AvroHere-green?logo=github)

2. 🧩 **Features**
- 🔗 **URL Scraping**: Extract all links from any webpage or multiple URLs
- 📂 **File Processing**: Accepts .txt files with multiple URLs (one per line)
- 🔍 **Smart Filtering**: `/include` and `/exclude` keywords to refine results
- 🧑‍💻 **User Sessions**: Maintains separate sessions with filters for each user
- ⏱ **Progress Tracking**: Real-time updates during scraping operations
- 📥 **Easy Export**: Get filtered links as downloadable .txt files
- 🚀 **Concurrent Processing**: Fast scraping with thread pool execution
- ⚙️ **Session Management**: Automatic cleanup of inactive sessions


✨ Features
🌐 URL Scraping

Scrape links from direct URLs or .txt file uploads

Supports http:// and https:// validation

🔍 Smart Filtering

/include keyword1,keyword2 → Whitelist links by keywords

/exclude keyword3,keyword4 → Blacklist links by keywords

Case-insensitive matching

📂 Session Management

Isolated per-user sessions

Auto-reset after 1 hour of inactivity

/reset → Clear all filters & data

📊 Progress Tracking

Real-time updates during scraping

Concurrent processing (8 threads)

📤 Downloadable Results

Filtered links delivered as .txt files

Clean filename with link count (e.g., filtered_links_42.txt)

🛟 User-Friendly UX

/help → Detailed guide with examples

/status → Check active filters & link counts

Error handling with plain-English replies

⚡ Tech Stack

Python + python-telegram-bot

BeautifulSoup for scraping

ThreadPoolExecutor for concurrency



3. 💾 **Installation**
# Clone the repository
git clone https://github.com/AvroHere/link_grabber_tg
cd link-grabber-bot

# Install dependencies
pip install -r requirements.txt

# Run the bot (replace with your actual token)
python main.py

4. 🧠 **Usage**
   1. 🚀 **Start** the bot with `/start` command
2. ⚙️ Set filters (optional):
   - `/include python,telegram` - Only keep links containing these words
   - `/exclude ads,tracking` - Remove links containing these words
3. 🔗 Send a URL or upload a `.txt` file with multiple URLs
4. 📥 Receive filtered links as a downloadable text file
5. 🔄 Use `/reset` to clear filters or `/status` to check progress

5. 📁 **Folder Structure
```
project/
├── LICENSE.txt       # MIT License file
├── README.md         # Project documentation
├── main.py           # Main bot application
├── requirements.txt  # Python dependencies
└── .gitignore        # Standard git ignore file
```

6. 🛠 **Built With**
- External Libraries:
  - `python-telegram-bot` - Telegram Bot API wrapper
  - `beautifulsoup4` - HTML parsing and web scraping
  - `requests` - HTTP requests handling
- Standard Libraries:
  - `asyncio` - Asynchronous I/O operations
  - `logging` - Application logging
  - `re` - Regular expressions
  - `os` - Operating system interfaces
 
7. 🚧 **Roadmap**
- [ ] Add depth-limited recursive scraping
- [ ] Support for additional file formats (CSV, JSON)
- [ ] Rate limiting and polite scraping delays
- [ ] User whitelist/blacklist functionality
- [ ] Scheduled scraping tasks
- [ ] Docker container support

8. ❓ **FAQ
**Q: Why am I not getting any links?**  
A: Check your filters with `/status` - they might be too restrictive. Try `/reset` to clear all filters.

**Q: Can I scrape private websites?**  
A: The bot only scrapes publicly accessible content like any web browser would.


9. 📄 **License**
MIT License

Copyright (c) 2025 AvroHere

Permission is hereby granted... [standard MIT text]

10. 👨‍💻 **Author**
**Avro** - Python Developer & Automation Enthusiast  
🔗 GitHub: [https://github.com/AvroHere](https://github.com/AvroHere)  

💡 *"Automation is not about replacing humans, it's about amplifying human potential."*  

⭐ **If you find this project useful, please consider starring it on GitHub!**

