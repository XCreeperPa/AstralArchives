# 数据清洗基础模型
import mwparserfromhell

class BaseCleaner:
    def __init__(self, category: str):
        self.category = category

    def clean(self, index: int, title: str, raw_text: str):
        """
        清洗入口，返回dict: {index, meta, content}
        """
        return {
            "index": index,
            "meta": {"category": self.category, "title": title},
            "content": "test"
        }
