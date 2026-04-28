"""News source — dated headlines from Google News RSS."""


def search(query, cutoff):
    """Google News RSS — timestamped headlines."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        results = []
        for item in root.iter("item"):
            title = item.findtext("title", "")
            pub_date = item.findtext("pubDate", "")
            if pub_date:
                try:
                    dt = datetime.strptime(pub_date[:25], "%a, %d %b %Y %H:%M:%S")
                    date_str = dt.strftime("%Y-%m-%d")
                    if date_str >= cutoff:
                        continue
                except ValueError:
                    date_str = ""
            else:
                date_str = ""
            if title:
                results.append({
                    "title": title,
                    "content": f"{title} ({date_str})",
                    "source": "Google News",
                    "date": date_str,
                })
            if len(results) >= 5:
                break
        return results
    except Exception:
        return []
