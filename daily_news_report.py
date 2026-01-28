import os
import requests
import feedparser as fp

# ------ CONFIGS ------
GEMINI_KEY = os.environ('GEMINI_KEY')
NEWS_DISCORD_URL = os.environ('NEWS_DISCORD_URL')               #general channel webhook
NEWS_SUB_DISCORD_URL = os.environ('NEWS_SUB_DISCORD_URL')       #daily-news channel webhook

news_rss = {
    'Thai News': [
        'https://www.bangkokpost.com/rss/data/topstories.xml', 
        'https://thestandard.co/feed/'],
    'Global News': [
        'http://feeds.bbci.co.uk/news/world/rss.xml', 
        'https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml'],
    'Tech News': [
        'https://techcrunch.com/feed/', 
        'https://www.theverge.com/rss/index.xml'],
    'Finance News': [
        'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664', 
        'https://finance.yahoo.com/news/rssindex']
}

news_data = {
    'Thai News': [], 'Global News': [],
    'Tech News': [], 'Finance News': []
}

def fetch_rss_feed(rss):
    try:
        feed = fp.parse(rss)
        if not feed.entries:
            print(f'Fetching Failed for {rss}')
        
        # Get only top 5 news in the feed
        data = []
        for entry in feed.entries[:5]:
            data.append({
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': (entry.get('summary') or entry.get('description') or 'No summary')
            })

        return data
        
    except Exception as e:
        print(f'Error:{e}')
        return []
    
def send_raw_feed(rss):
    print()

def news_summary():
    print()

if __name__ == '__main__':
    for key, value in news_rss.items():
        for rss in value:
            news_data[key].extend(fetch_rss_feed(rss))