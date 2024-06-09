# crawling.py
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio
from pydantic import BaseModel
import fitz  # PyMuPDF
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    HTMLHeaderTextSplitter,
)


class CrawlInfo(BaseModel):
    url: str
    error: str = None
    content: str
    depth: int


async def fetch_url(client, url, current_depth, retries=1, timeout=10.0):
    for attempt in range(retries):
        try:
            response = await client.get(url, timeout=timeout)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                print(f"Fetched PDF {url} at depth {current_depth}")
                pdf_content = await fetch_pdf_content(response.content)
                return pdf_content, None  # Return content with no error
            else:
                print(f"Fetched HTML {url} at depth {current_depth}")
                return response.text, None  # Return content with no error
        except (
            httpx.RequestError,
            httpx.HTTPStatusError,
            httpx.TimeoutException,
        ) as e:
            print(f"Error fetching {url}: {e}")
            return None, str(e)  # Return no content with error message

    print(f"Failed to fetch {url} after {retries} attempts.")
    return None, "Failed after retries"


async def fetch_pdf_content(pdf_bytes):
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in document:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None


async def process_url(
    client, url, current_depth, root_url, visited, max_depth, success_callback
):
    if url in visited or (max_depth is not None and current_depth > max_depth):
        return None, None, None

    visited.add(url)
    content, error = await fetch_url(client, url, current_depth)
    if content is None and error is not None:
        crawl_info = CrawlInfo(
            url=url, content="", error=error, depth=current_depth
        )
        return crawl_info, root_url, None

    crawl_info = CrawlInfo(url=url, content=content, depth=current_depth)
    if success_callback:
        await success_callback(crawl_info)  # Call the success callback

    if not content.startswith(
        "%PDF"
    ):  # PDF content will not contain HTML links
        soup = BeautifulSoup(content, "lxml")
        links = [
            urljoin(url, a_tag["href"])
            for a_tag in soup.find_all("a", href=True)
        ]
        valid_links = [
            link
            for link in links
            if urlparse(link).netloc == urlparse(root_url).netloc
        ]
        print(f"\nFound {len(valid_links)} valid links on {url}")
        return crawl_info, root_url, valid_links
    else:
        return crawl_info, root_url, []


async def crawl_websites(root_urls, max_depth=None, success_callback=None):
    visited = set()
    queue = [(url, url, 0) for url in root_urls]  # (url, root_url, depth)
    all_data = []

    async with httpx.AsyncClient() as client:
        while queue:
            print("\n\nQueue:\n", queue)
            tasks = [
                process_url(
                    client,
                    url,
                    depth,
                    root_url,
                    visited,
                    max_depth,
                    success_callback,
                )
                for url, root_url, depth in queue
            ]
            results = await asyncio.gather(*tasks)

            new_queue = []
            for data, root_url, links in results:
                if data is not None:
                    all_data.append(data)
                    if links is not None:
                        new_queue.extend(
                            (link, root_url, data.depth + 1) for link in links
                        )

            queue = new_queue

    return all_data


# Placeholder function for preprocessing content
def content_preprocess(crawl_info: CrawlInfo):
    chunk_size = 1000
    chunk_overlap = 200
    documents = []
    if crawl_info.url.endswith(".pdf"):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        documents = text_splitter.create_documents(crawl_info.content)

    else:  # if is HTML content
        headers_to_split_on = [("h1", "Header 1"), ("h2", "Header 2")]
        splitter = HTMLHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        header_split_docs = splitter.split_text(crawl_info.content)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        documents = text_splitter.split_documents(header_split_docs)

    crawl_info_docs = [
        CrawlInfo(
            url=crawl_info.url,
            content=doc.page_content,
            depth=crawl_info.depth,
        )
        for doc in documents
    ]

    return crawl_info_docs
