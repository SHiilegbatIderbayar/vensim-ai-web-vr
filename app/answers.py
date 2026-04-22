from __future__ import annotations
from app.openai_utils import response_text
from app.config import USE_WEB_SEARCH_FOR_REAL_WORLD


def explain_simulation(question: str, facts_text: str, language: str = "mn") -> str:
    system = "Та систем динамик симуляцийн шинжээч. Зөвхөн өгөгдсөн баримтад тулгуурлан Монгол хэлээр тайлбарла."
    user = f"""
Дараах simulation баримтууд дээр үндэслэн хариул.
Шинэ тоо бүү зохио.

Question:
{question}

Facts:
{facts_text}

Format:
1. Товч хариулт
2. Гол өөрчлөлтүүд
3. Тайлбар
4. Боломжит бодлогын санал
"""
    return response_text([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])


def explain_from_model_context(question: str, context_text: str, language: str = "mn") -> str:
    system = "Та систем динамик загвар тайлбарлагч. Зөвхөн өгөгдсөн model context болон baseline summary-д тулгуурлан хариул."
    user = f"""
Question:
{question}

Model context:
{context_text}

Requirements:
- Монгол хэлээр хариул.
- Хэрэв equation/томьёо байгаа бол тайлбарла.
- Хэрэв утга/дүн асуусан бол baseline summary-гээс тайлбарла.
- Хэрэв нөлөө асуусан бол causal logic-оор тайлбарла.
- Context-д байхгүй тоо бүү зохио.
"""
    return response_text([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])


def explain_methodology(question: str, language: str = "mn") -> str:
    system = "Та аргачлал, нэр томьёо, үг хэллэгийг ойлгомжтой тайлбарладаг багш."
    user = f"""
Question:
{question}

Requirements:
- Монгол хэлээр тайлбарла.
- Эхлээд энгийн тодорхойлолт өг.
- Дараа нь юунд хэрэглэдэгийг тайлбарла.
- Боломжтой бол богино жишээ өг.
"""
    return response_text([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])


def answer_real_world(question: str, language: str = "mn") -> str:
    system = "Та бодит дэлхийн сүүлийн үеийн мэдээллийг вэбээс шалгаж, Монгол хэлээр эх сурвалжтай тайлбарладаг судлаач."
    user = f"""
Question:
{question}

Requirements:
- Web search ашиглаж сүүлийн үеийн мэдээлэл шалга.
- Монгол хэлээр хариул.
- Гол тоо баримтыг тайлбарла.
- Эх сурвалжийн ишлэлийг хариултад үлдээ.
"""
    tools = [{"type": "web_search"}] if USE_WEB_SEARCH_FOR_REAL_WORLD else []
    return response_text([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], tools=tools)


def explain_goal_seek(question: str, facts_text: str) -> str:
    system = "Та simulation goal-seek шинжилгээ тайлбарлагч."
    user = f"""
Question:
{question}

Facts:
{facts_text}

Монгол хэлээр дараах бүтэцтэй хариул:
1. Зорилтот тайлбар
2. Ойролцоогоор шаардлагатай parameter утга
3. Болгоомжлох зүйлс
"""
    return response_text([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])
