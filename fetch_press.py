import os
import re
import csv
import urllib.request
from bs4 import BeautifulSoup

# 解析対象のURL（EurekAlert! 日本語版トップ）
TARGET_URL = "https://www.eurekalert.org/language/japanese/home"
CSV_FILE = "releases.csv"

def fetch_html():
    """WebページからHTMLを取得する"""
    try:
        # 403 Forbiddenなどのアクセス拒否を防ぐため、ブラウザのふりをするUser-Agentを設定
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
    """HTMLを解析してニュースリリースの情報を抽出する"""
    items = []
    if not html_data:
        return items
    
    soup = BeautifulSoup(html_data, 'html.parser')
    
    # ニュースの一覧エリア（通常、記事リンクを含むブロック）を探す
    # 2026年現在のEurekAlert!の標準的な構造（h2タグ内のリンクなど）に適合させています
    articles = soup.find_all('h2')
    
    for h2 in articles:
        link_tag = h2.find('a')
        if not link_tag:
            continue
            
        title = link_tag.get_text(strip=True)
        relative_url = link_tag.get('href', '')
        
        # 相対URLを絶対URLに変換
        if relative_url.startswith('/'):
            url = f"https://www.eurekalert.org{relative_url}"
        else:
            url = relative_url
            
        # 日付と概要、DOIの探索（h2の直前の要素や周辺の構造から取得を試みる）
        # ※HTMLから直接DOIを抜くため、今回は周辺テキストから正規表現で抽出
        parent_or_sibling = h2.find_parent()
        parent_text = parent_or_sibling.get_text() if parent_or_sibling else ""
        
        # 本文からDOIを特定するルール
        doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', parent_text)
        doi = doi_match.group(0) if doi_match else "なし"
        
        # 日付の抽出（例: 18-Sep-2026 などのパターンを検索）
        date_match = re.search(r'\d{1,2}-[A-Za-z]{3}-\d{4}', parent_text)
        date = date_match.group(0) if date_match else "不明"
        
        items.append({
            "date": date,
            "title": title,
            "doi": doi,
            "url": url
        })
        
    return items

def update_csv(new_items):
    """既存のCSVを確認し、新しいデータのみを追記する"""
    existing_urls = set()
    file_exists = os.path.exists(CSV_FILE)
    
    # すでに保存されているURLを読み込んで重複を防ぐ
    if file_exists:
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row.get('url'))
                
    # 新着データだけを絞り込む（古い順に書き込めるよう逆順にする）
    items_to_add = [item for item in reversed(new_items) if item['url'] not in existing_urls]
    
    if not items_to_add:
        print("新しいプレスリリースはありませんでした。")
        return False
        
    # CSVに追記
    with open(CSV_FILE, mode='a', encoding='utf-8', newline='') as f:
        fieldnames = ['date', 'title', 'doi', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader() # ファイルが新規作成の場合のみ見出しを書き込む
            
        for item in items_to_add:
            writer.writerow(item)
            print(f"追加: {item['title']}")
            
    return True

if __name__ == "__main__":
    html_content = fetch_html()
    parsed_items = parse_html(html_content)
    update_csv(parsed_items)
