from teacher.services.internet_search import InternetSearchService

text = """
Object detection using transformers eliminates
non maximum suppression and improves global reasoning.
"""

sources = InternetSearchService.search_sources(text)

print(sources)