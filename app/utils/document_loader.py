import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentLoader:
    def __init__(self, file_data: bytes, file_name: str):
        self.file_data = file_data
        self.file_name = file_name
        self.text = ""

    def read(self):
        # Determine the file type and process accordingly
        if self.file_name.endswith('.pdf'):
            self.text = self._read_pdf()
        elif self.file_name.endswith('.txt'):
            self.text = self._read_text()
        else:
            raise ValueError("Unsupported file type")

        return self.text

    def _read_pdf(self):
        text = ""
        try:
            # Load PDF from bytes
            doc = fitz.open("pdf", self.file_data)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            raise RuntimeError(f"Failed to process PDF: {e}")
        return text

    def _read_text(self):
        try:
            # Decode binary data assuming UTF-8 encoding
            text = self.file_data.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to process text file: {e}")
        return text

    def split(self, text_length: int, text_overlap: int):
        if not self.text:
            raise ValueError(
                "No text available. Ensure 'read' is called first."
            )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=text_length,
            chunk_overlap=text_overlap,
        )
        documents = text_splitter.create_documents([self.text])
        texts = [doc.page_content for doc in documents]
        print("Texts: \n", texts)
        return texts
