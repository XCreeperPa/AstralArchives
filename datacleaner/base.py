# 数据清洗基础模型
import mwparserfromhell
from abc import ABC, abstractmethod

class BaseCleaner(ABC):
    def __init__(self, category: str):
        self.category = category

    @abstractmethod
    def clean(self, index: int, title: str, raw_text: str):
        """
        清洗入口，返回dict: {index, meta, content}
        其中 meta 必须包含 "category" 和 "title" 字段
        """
        pass