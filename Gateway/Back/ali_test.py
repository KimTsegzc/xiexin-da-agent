from openai import OpenAI

from .settings import get_settings

try:
    settings = get_settings()
    if not settings.api_key:
        raise RuntimeError("缺少 API Key，请在项目根目录 .env 中配置 ALIYUN_BAILIAN_API_KEY 或 DASHSCOPE_API_KEY")

    client = OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
    )

    completion = client.chat.completions.create(
        model=settings.model,  # 模型列表: https://help.aliyun.com/model-studio/getting-started/models
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': '你是谁？'}
        ]
    )
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"错误信息：{e}")
    print("请参考文档：https://help.aliyun.com/model-studio/developer-reference/error-code")