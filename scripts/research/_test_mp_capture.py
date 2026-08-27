from mp_capture.parsers import extract_from_body, extract_from_json

sample = {
    "comm_msg_list": [
        {
            "app_msg": {
                "title": "SkillForge test",
                "content_url": "https://mp.weixin.qq.com/s?__biz=MzU=&mid=1&idx=1&sn=abc",
            }
        }
    ]
}
print("json", extract_from_json(__import__("json").dumps(sample)))

xml = (
    "<appmsg><title><![CDATA[OpenObserve v0.92.0]]></title>"
    "<url><![CDATA[https://mp.weixin.qq.com/s/abc]]></url>"
    "<des><![CDATA[MCP support]]></des></appmsg>"
)
print("xml", extract_from_body(xml))
