import mwparserfromhell
from .base import BaseCleaner
import json

class MissionCleaner(BaseCleaner):
    def __init__(self):
        super().__init__("任务")

    def clean(self, index: int, title: str, raw_text: str):
        wikicode = mwparserfromhell.parse(raw_text)
        mission_template = None
        # 找到任务模板
        for t in wikicode.filter_templates():
            if str(t.name).strip() == "任务":
                mission_template = t
                break
        # 需要的元数据字段
        meta_keys = [
            ("任务名称", "任务名称"),
            ("任务地区", "任务地区"),
            ("任务类型", "任务类型"),
            ("所属版本", "所属版本"),
            ("任务描述", "任务描述"),
            ("出场人物", "出场人物"),
            ("系列任务", "系列任务"),
            ("前置任务", "前置任务"),
            ("后续任务", "后续任务"),
            ("任务流程", "任务流程")
        ]
        meta = {"category": self.category}
        if mission_template:
            for key, meta_key in meta_keys:
                if mission_template.has(key):
                    value = mission_template.get(key).value.strip()
                    if key == "任务流程":
                        lines = [line.strip() for line in value.split("\n") if line.strip().startswith("*")]
                        meta[meta_key] = json.dumps([line.lstrip("*").strip() for line in lines], ensure_ascii=False)
                    else:
                        meta[meta_key] = value
                else:
                    meta[meta_key] = ""
            if mission_template.has("任务类型"):
                meta["类型"] = mission_template.get("任务类型").value.strip()
            else:
                meta["类型"] = ""
        else:
            meta["任务名称"] = title
            for _, meta_key in meta_keys:
                if meta_key != "任务名称":
                    meta[meta_key] = ""
            meta["类型"] = ""
        # 用mwparserfromhell删除所有{{提示...}}和{{任务...}}模板
        nodes = wikicode.nodes[:]
        to_remove = []
        for node in nodes:
            if isinstance(node, mwparserfromhell.nodes.Template):
                name = str(node.name).strip()
                if name == "提示" or name == "任务":
                    to_remove.append(node)
        for node in to_remove:
            wikicode.remove(node)
        content = str(wikicode).strip()
        return {
            "index": index,
            "meta": meta,
            "content": content
        }
