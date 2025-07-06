# 光锥清洗模型
import mwparserfromhell
from .base import BaseCleaner

class LightconeCleaner(BaseCleaner):
    def __init__(self):
        super().__init__("光锥")

    def clean(self, index: int, title: str, raw_text: str):
        meta = {"category": self.category, "title": title}
        # 解析模板
        wikicode = mwparserfromhell.parse(raw_text)
        lightcone_template = None
        for t in wikicode.filter_templates():
            if "光锥图鉴" in t.name:
                lightcone_template = t
                break
        if lightcone_template:
            meta["名称"] = lightcone_template.get("名称").value.strip() if lightcone_template.has("名称") else title
            meta["命途"] = lightcone_template.get("命途").value.strip() if lightcone_template.has("命途") else ""
            meta["稀有度"] = lightcone_template.get("稀有度").value.strip() if lightcone_template.has("稀有度") else ""
            meta["相关角色"] = lightcone_template.get("相关角色").value.strip() if lightcone_template.has("相关角色") else ""
        else:
            meta["名称"] = title
            meta["命途"] = meta["稀有度"] = meta["相关角色"] = ""
        # 光锥故事
        story = ""
        if lightcone_template and lightcone_template.has("光锥故事"):
            story = lightcone_template.get("光锥故事").value.strip()
        # 内容：只保留名称、命途、稀有度、相关角色、光锥故事字段的wiki源代码
        content_parts = []
        if lightcone_template:
            for key in ["名称", "命途", "稀有度", "相关角色", "光锥故事"]:
                if lightcone_template.has(key):
                    content_parts.append(f"|{key}={lightcone_template.get(key).value.strip()}")
        content = "{{光锥图鉴\n" + "\n".join(content_parts) + "\n}}"
        return {
            "index": index,
            "meta": meta,
            "content": content
        }
