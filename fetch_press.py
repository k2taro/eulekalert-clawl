import os
import re
import csv
import urllib.request
from bs4 import BeautifulSoup

TARGET_URL = "https://www.eurekalert.org/language/japanese/home"
CSV_FILE = "releases.csv"

def fetch_html():
    try:
        req = urllib.request.Request(
            TARGET_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            return response.read()
    except Exception as e:
        print(f"HTMLの取得に失敗しました: {e}")
        return None

def parse_html(html_data):
    items = []
    if not html_data:
        return items
    
    soup = BeautifulSoup(html_data, 'html.parser')
    
    # 改善点：ニュースリリースを内正する個々のコンテナ（ブロック）を特定してループを回すと安全です
    # ここでは一般的な記事配下の構造、または各h2要素を起点とします
    articles = soup.find_all('h2')
    
    for h2 in articles:
        # h2自体がaタグ、またはh2の中にaタグがある両方のパターンに対応
        link_tag = h2 if h2.name == 'a' else h2.find('a')
        if not link_tag:
            # 周辺（直近の親要素など）にリンクがないか再探索
            link_tag = h2.find_parent('a') or h2.find_next('a')
            
        if not link_tag:
            continue
            
        title = h2.get_text(strip=True)
        relative_url = link_tag.get('href', '')
        
        if relative_url.startswith('/'):
            url = f"https://www.eurekalert.org{relative_url}"
        else:
            url = relative_url
            
        # 記事ブロックごとのテキストに限定して検索（誤検知防止）
        container = h2.find_parent(class_=re.compile(r'(hentry|article|release|item)')) or h2.find_parent()
        container_text = container.get_text() if container else ""
        
        # DOIの抽出
        doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', container_text)
        doi = doi_match.group(0) if doi_match else "なし"
        
        # 日付の抽出（h2の前の要素、またはコンテナ内から探す）
        date_match = re.search(r'\d{1,2}-[A-Za-z]{3}-\d{4}', container_text)
        date = date_match.group(0) if date_match else "不明"
        
        # タイトルやURLが空でない場合のみ追加
        if title and url:
            items.append({
                "date": date,
                "title": title,
                "doi": doi,
                "url": url
            })
        
    return items

def update_csv(new_items):
    existing_urls = set()
    file_exists = os.path.exists(CSV_FILE)
    
    if file_exists:
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row.get('url'))
                
    items_to_add = [item for item in reversed(new_items) if item['url'] not in existing_urls]
    
    if not items_to_add:
        print("新しいプレスリリースはありませんでした。")
        return False
        
    with open(CSV_FILE, mode='a', encoding='utf-8', newline='') as f:
        fieldnames = ['date', 'title', 'doi', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        for item in items_to_add:
            writer.writerow(item)
            print(f"追加: {item['title']}")
            
    return True

if __name__ == "__main__":
    html_content = fetch_html()
    parsed_items = parse_html(html_content)
    update_csv(parsed_items)
