import arxiv
import logging

logger = logging.getLogger(__name__)

class ArxivSearch:

    @staticmethod
    def search(query: str, limit: int = 3):
        """
        Returns a list of top arXiv paper summaries for the query.
        """
        try:
            results = arxiv.Search(
                query=query,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance
            )

            papers = []
            for result in results.results():
                summary = (
                    f"Title: {result.title}\n"
                    f"Authors: {', '.join(a.name for a in result.authors)}\n"
                    f"Published: {result.published.strftime('%Y-%m-%d')}\n"
                    f"URL: {result.entry_id}\n"
                    f"Abstract: {result.summary}"
                )
                papers.append(summary)

            return papers

        except Exception as e:
            logger.warning(f"arXiv search failed: {e}")
            return []
