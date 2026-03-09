# =========================================================
# INTERNET SEARCH SERVICE – EduDOC
# Finds possible plagiarism sources from Internet
# =========================================================

from ddgs import DDGS


class InternetSearchService:

    @staticmethod
    def search_sources(text, max_results=5):
        """
        Search internet for matching sources.
        Returns list of {title, url}
        """

        # Use first 40 words as search query
        query = " ".join(text.split()[:40])

        results_list = []

        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)

                for r in results:
                    results_list.append({
                        "title": r["title"],
                        "url": r["href"]
                    })

        except Exception as e:
            print("Internet search failed:", e)

        return results_list