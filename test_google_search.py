from ddgs import DDGS

query = "Detection Transformer object detection research paper"

print("\nTop Search Results:\n")

with DDGS() as ddgs:
    results = ddgs.text(query, max_results=5)

    for r in results:
        print(r["title"])
        print(r["href"])
        print("-" * 50)