import os
import re
import csv
import urllib.request
import xml.etree.ElementTree as ET

# EurekAlert! 日本版のRSS
RSS_URL = "https://eurekalert.org"
CSV_FILE = "releases.csv"

def fetch_rss():
    try:
        response = urllib.request.urlopen(RSS_URL)
        return response.read()
    except Exception as e:
        print(f"RSSの取得に失敗しました: {e}")
        return None

def parse_rss(xml_data):
    items = []
    if not xml_data:
        return items
    
    root = ET.fromstring(xml_data)
    # RSSのitem要素をすべて取得
    for item in root.findall('.//item'):
        title = item.find('title').text if item.find('title') is not None else ""
        link = item.find('link').text if item.find('link') is not None else ""
        description = item.find('description').text if item.find('description') is not None else ""
        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
        
        # 本文からDOIを特定するルール（正規表現）
        doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', description)
        doi = doi_match.group(0) if doi_match else "なし"
        
        items.append({
            "date": pub_date,
            "title": title,
            "doi": doi,
            "url": link
        })
    return items

def update_csv(new_items):
    # すでに保存されているURL（またはタイトル）を記録して重複を防ぐ
    existing_urls = set()
    file_exists = os.path.exists(CSV_FILE)
    
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
            writer.writeheader() # ファイルがなければ見出しを書く
            
        for item in items_to_add:
            writer.writerow(item)
            print(f"追加: {item['title']}")
            
    return True

if __name__ == "__main__":
    xml_content = fetch_rss()
    parsed_items = parse_rss(xml_content)
    update_csv(parsed_items)
