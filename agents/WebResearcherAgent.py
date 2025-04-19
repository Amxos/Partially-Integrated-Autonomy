# --- Specialized Agent: WebResearcher ---
def scrape_books_toscrape(url: str) -> Optional[List[Dict[str, str]]]:
    """
    Scrapes book data (title and price) from a given books.toscrape.com URL.

    Args:
        url: The URL of the page to scrape.

    Returns:
        A list of dictionaries, where each dictionary represents a book
        and contains its title and price.  Returns None on error.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        soup = BeautifulSoup(response.text, 'html.parser')  # Use 'html.parser'

        books = []
        for article in soup.find_all('article', class_='product_pod'):
            title = article.h3.a['title']  # Get the title from the <a> tag within the <h3>
            price = article.find('p', class_='price_color').text  # Get the price text

            books.append({'title': title, 'price': price})

        return books

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return None

class WebResearcher(BaseAgent):
    def __init__(self, skills, access_level=1):
        super().__init__("Web Researcher", skills, access_level)
        self.capacity = 5  # Example capacity

    def _execute_task(self, task):
        """Executes web scraping tasks, utilizing memory."""

        if task.type != "web_scraping":
            raise TaskExecutionError("WebResearcher can only handle web_scraping tasks.")

        url = task.details.get("url")
        target = task.details.get("target")  # Keep target for future use

        if not url:
            raise TaskExecutionError("URL is required for web_scraping.")

        # --- Memory Usage: Check for Recent Scrapes ---
        recent_scrape_query = f"Scraped data from {url}"
        recent_scrapes = self.query_memory(recent_scrape_query, n_results=3)

        for scrape in recent_scrapes:
            # Check if the scrape is recent enough (e.g., within the last 2 hours)
            try:
                scrape_data = json.loads(scrape)  # Assuming stored as JSON
                scrape_timestamp = datetime.fromisoformat(scrape_data.get("timestamp"))
                if datetime.now() - scrape_timestamp < timedelta(hours=2):
                    # Use cached data
                    logger.info(f"Agent {self.id}: Using cached data for {url} from {scrape_timestamp}")
                    return scrape_data.get("data")  # Return the cached data
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(f"Agent {self.id}: Invalid cached data format for {url}.")
                continue #go to the next item


        # ---  Web Scraping with requests and BeautifulSoup4 ---
        logger.info(f"Agent {self.id}: Scraping {url}...")
        scraped_data = None
        if "books.toscrape.com" in url:
            scraped_data = scrape_books_toscrape(url)  # Use our new function
        # Add more 'elif' blocks for other websites you want to scrape
        else:
            logger.warning(f"Agent {self.id}: No scraping function for {url}")


        # --- Memory Usage: Store Parsed Data ---
        if scraped_data:
            memory_entry = {
                "url": url,
                "target": target,  # Include target in memory entry
                "timestamp": datetime.now().isoformat(),
                "data": scraped_data,
            }
            self.add_to_memory(json.dumps(memory_entry))  # Store as JSON string
            logger.info(f"Agent {self.id}: Stored scraped data for {url} in memory.")
            return scraped_data

        return None # Return scraped_data, or None if the scrape "fails".
# --- Example Usage (if __name__ == '__main__':) ---