import logging
import re
import os
import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from typing import List, Set

import requests
from bs4 import BeautifulSoup
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Configuration
BOT_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your actual bot token
MAX_WORKERS = 8
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class UserSession:
    """Manages per-user state including filters and collected links."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.include_keywords: List[str] = []
        self.exclude_keywords: List[str] = []
        self.collected_links: Set[str] = set()
        self.last_activity_time = asyncio.get_event_loop().time()
        self.processing_lock = asyncio.Lock()  # To prevent concurrent scraping for a user

    def update_activity_time(self) -> None:
        """Update the last activity time for session management."""
        self.last_activity_time = asyncio.get_event_loop().time()

    def set_include_keywords(self, keywords: str) -> None:
        """Set keywords to include in filtered links."""
        self.include_keywords = [k.strip().lower() for k in keywords.split(",") if k.strip()]

    def set_exclude_keywords(self, keywords: str) -> None:
        """Set keywords to exclude from filtered links."""
        self.exclude_keywords = [k.strip().lower() for k in keywords.split(",") if k.strip()]

    def reset(self) -> None:
        """Reset all filters and collected links."""
        self.include_keywords = []
        self.exclude_keywords = []
        self.collected_links = set()

    def add_link(self, link: str) -> None:
        """Add a new link to the collection."""
        self.collected_links.add(link)

    def get_filtered_links(self) -> List[str]:
        """Get filtered links based on include/exclude keywords."""
        filtered_links = set()
        for link in self.collected_links:
            link_lower = link.lower()
            # Apply include filter
            if self.include_keywords and not any(
                keyword in link_lower for keyword in self.include_keywords
            ):
                continue
            # Apply exclude filter
            if self.exclude_keywords and any(
                keyword in link_lower for keyword in self.exclude_keywords
            ):
                continue
            filtered_links.add(link)
        return sorted(list(filtered_links))


# Dictionary to store user sessions
user_sessions = {}
# Thread pool for concurrent scraping
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


async def get_user_session(user_id: int) -> UserSession:
    """Retrieve or create a user session."""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
        logger.info(f"Created new session for user {user_id}")
    session = user_sessions[user_id]
    session.update_activity_time()
    return session


async def cleanup_sessions() -> None:
    """Periodically clean up inactive sessions."""
    while True:
        current_time = asyncio.get_event_loop().time()
        inactive_users = [
            user_id
            for user_id, session in user_sessions.items()
            if current_time - session.last_activity_time > SESSION_TIMEOUT_SECONDS
        ]
        for user_id in inactive_users:
            del user_sessions[user_id]
            logger.info(f"Cleaned up inactive session for user {user_id}")
        await asyncio.sleep(SESSION_TIMEOUT_SECONDS // 2)  # Check every half session timeout


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and instructions."""
    user = update.effective_user
    session = await get_user_session(user.id)  # Ensure session is initialized/updated
    
    welcome_msg = """
🌐 *Link Grabber Bot* 🌐
_Scrape and filter links from URLs or files!_

📥 *How to use:*
1. Send a URL directly, or upload a `.txt` file with URLs
2. Set filters (optional):
   - `/include keyword1,keyword2`
   - `/exclude keyword3,keyword4`
3. I'll scrape and send filtered links in a file!

🛠 *Commands:*
- `/help` – Show detailed guide
- `/status` – Check current filters
- `/reset` – Clear all filters
"""
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a detailed help message."""
    help_msg = """
📖 *Help Guide* 📖

🔗 *URL Processing:*
- Send me any valid URL starting with http:// or https://
- Or upload a .txt file with multiple URLs (one per line)

⚙️ *Filter Commands:*
- `/include keyword1,keyword2` - Only keep links containing these words
- `/exclude keyword3,keyword4` - Remove links containing these words
- `/reset` - Clear all filters and collected links
- `/status` - Show current filters and link count

📊 *Example Workflow:*
1. `/include python,programming`
2. `/exclude ads,tracking`
3. Send a URL or upload a file
4. Receive filtered links in a downloadable file

💡 *Tips:*
- Filters are case-insensitive
- You can chain multiple filters
- Use comma to separate multiple keywords
"""
    await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)


async def include_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set include keywords for the user session."""
    session = await get_user_session(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide keywords to include (comma-separated).\n"
            "Example: `/include python,telegram,bot`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    keywords = " ".join(context.args)
    session.set_include_keywords(keywords)
    
    response = (
        "✅ *Include filters updated:*\n" +
        ("`" + "`, `".join(session.include_keywords) + "`" if session.include_keywords else "*None*")
    )
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


async def exclude_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set exclude keywords for the user session."""
    session = await get_user_session(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide keywords to exclude (comma-separated).\n"
            "Example: `/exclude spam,ads,junk`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    keywords = " ".join(context.args)
    session.set_exclude_keywords(keywords)
    
    response = (
        "✅ *Exclude filters updated:*\n" +
        ("`" + "`, `".join(session.exclude_keywords) + "`" if session.exclude_keywords else "*None*")
    )
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset all filters and collected links for the user session."""
    session = await get_user_session(update.effective_user.id)
    session.reset()
    
    await update.message.reply_text(
        "♻️ *All filters and collected links have been reset.*\n"
        "Your session is now clean!",
        parse_mode=ParseMode.MARKDOWN
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current filters and collected link count."""
    session = await get_user_session(update.effective_user.id)
    
    include_str = "`, `".join(session.include_keywords) if session.include_keywords else "None"
    exclude_str = "`, `".join(session.exclude_keywords) if session.exclude_keywords else "None"
    link_count = len(session.collected_links)
    filtered_count = len(session.get_filtered_links())

    message = (
        "📊 *Current Status*\n\n"
        f"• *Include Filters:* `{include_str}`\n"
        f"• *Exclude Filters:* `{exclude_str}`\n"
        f"• *Collected Links:* `{link_count}`\n"
        f"• *Filtered Links:* `{filtered_count}`\n\n"
        "Send me URLs or a `.txt` file to scrape more links!"
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def validate_url(url: str) -> bool:
    """Validate if a URL has http/https scheme and a netloc."""
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except ValueError:
        return False


def scrape_links_sync(url: str, base_url: str) -> List[str]:
    """Synchronously scrape links from a given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"]
            full_url = urljoin(base_url, href)
            if validate_url(full_url):
                links.append(full_url)
        return links
    except requests.exceptions.RequestException as e:
        logger.error(f"Error scraping {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error during scraping {url}: {e}")
        return []


async def process_urls(
    update: Update, context: ContextTypes.DEFAULT_TYPE, urls: List[str]
) -> None:
    """Process a list of URLs concurrently with progress updates."""
    user_id = update.effective_user.id
    session = await get_user_session(user_id)

    async with session.processing_lock:
        total_urls = len(urls)
        if total_urls == 0:
            await update.message.reply_text("❌ No valid URLs provided to scrape.")
            return

        progress_message = await update.message.reply_text(
            f"🔍 Scraping {total_urls} URLs. Please wait..."
        )

        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, scrape_links_sync, url, url) for url in urls
        ]

        processed = 0
        update_interval = max(1, total_urls // 5)  # Update every 20% progress

        for future in asyncio.as_completed(futures):
            try:
                scraped_links = await future
                for link in scraped_links:
                    session.add_link(link)
                processed += 1
                
                if processed % update_interval == 0 or processed == total_urls:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=progress_message.message_id,
                        text=(
                            f"⏳ Progress: {processed}/{total_urls} URLs\n"
                            f"📥 Collected: {len(session.collected_links)} links"
                        ),
                    )
            except Exception as e:
                logger.error(f"Error processing URL: {e}")
                processed += 1  # Count failed attempts too

        filtered_links = session.get_filtered_links()
        
        if not filtered_links:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text="❌ No links found matching your filters.",
            )
            return

        # Save filtered links to a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', encoding='utf-8', delete=False) as temp_file:
            temp_file.write("\n".join(filtered_links))
            temp_file_path = temp_file.name

        try:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(temp_file_path, "rb"),
                caption=f"✅ Found {len(filtered_links)} filtered links",
                filename=f"filtered_links_{len(filtered_links)}.txt"
            )
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id
            )
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text="❌ Error preparing your download. Please try again.",
            )
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages and document uploads."""
    session = await get_user_session(update.effective_user.id)

    if update.message.text:
        url_text = update.message.text.strip()
        if validate_url(url_text):
            await update.message.reply_text("🔗 URL received. Starting scrape...")
            await process_urls(update, context, [url_text])
        else:
            await update.message.reply_text(
                "⚠️ Invalid URL. Please send a URL starting with http:// or https://"
            )
    elif update.message.document:
        document = update.message.document
        if document.file_name.lower().endswith(".txt"):
            await update.message.reply_text("📄 TXT file received. Processing...")
            
            # Create a temporary file to store the downloaded content
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                file = await context.bot.get_file(document.file_id)
                await file.download_to_drive(temp_file_path)
                
                urls = []
                with open(temp_file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        url = line.strip()
                        if validate_url(url):
                            urls.append(url)
                        else:
                            logger.warning(f"Invalid URL in file: {url}")
                
                if urls:
                    await process_urls(update, context, urls)
                else:
                    await update.message.reply_text("❌ No valid URLs found in the file.")
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                await update.message.reply_text("❌ Error processing your file. Please try again.")
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        else:
            await update.message.reply_text("⚠️ I only accept .txt files with URLs.")
    else:
        await update.message.reply_text("⚠️ Please send a URL or .txt file with URLs.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and send user-friendly messages."""
    logger.error(f"Error: {context.error}", exc_info=True)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again or contact support."
        )


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Schedule session cleanup
    asyncio.get_event_loop().create_task(cleanup_sessions())

    # Command handlers
    cmd_handlers = [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("include", include_command),
        CommandHandler("exclude", exclude_command),
        CommandHandler("reset", reset_command),
        CommandHandler("status", status_command),
    ]
    
    for handler in cmd_handlers:
        application.add_handler(handler)

    # Message handler
    application.add_handler(
        MessageHandler(filters.TEXT | filters.Document.TEXT, handle_message)
    )

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
