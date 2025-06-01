import mwparserfromhell
from .base import BaseCleaner

class CharacterCleaner(BaseCleaner):
    def __init__(self):
        super().__init__("角色")

    def clean(self, index: int, title: str, raw_text: str):
        wikicode = mwparserfromhell.parse(raw_text)
        char_template = None
        for t in wikicode.filter_templates():
            if "角色图鉴" in t.name:
                char_template = t
                break
        # 需要的元数据字段
        meta_keys = [
            "名称", "外文名", "称号", "全名", "性别", "稀有度", "限定", "阵营", "命途", "实装日期", "实装版本", "昵称/外号", "派系", "体型", "种族"
        ]
        meta = {"category": self.category}
        if char_template:
            for key in meta_keys:
                meta[key] = char_template.get(key).value.strip() if char_template.has(key) else ""
        else:
            meta["名称"] = title
            for key in meta_keys:
                if key != "名称":
                    meta[key] = ""
        # 内容字段
        content_keys = meta_keys + [
            "卷首语", "角色详细", "角色故事1", "角色故事2", "角色故事3", "角色故事4"
        ]
        content_parts = []
        if char_template:
            for key in content_keys:
                if char_template.has(key):
                    content_parts.append(f"|{key}={char_template.get(key).value.strip()}")
        content = "{{角色图鉴\n" + "\n".join(content_parts) + "\n}}"
        return {
            "index": index,
            "meta": meta,
            "content": content
        }
